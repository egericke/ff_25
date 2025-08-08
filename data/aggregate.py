import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import os
import sys

def aggregate_data(year):
    """
    Main function to orchestrate the data aggregation, cleaning, and feature engineering.
    """
    # --- 1. Load and Clean Data ---
    projections = load_projections(year)
    adp = load_adp(year)

    # Merge dataframes
    df = pd.merge(projections, adp, on='Player', how='left')

    # --- 2. Feature Engineering: VORP, Tiers, Volatility ---

    # Calculate VORP (Value Over Replacement Player)
    df = calculate_vorp(df)

    # Calculate Volatility based on rank disagreement
    rank_cols = [col for col in df.columns if 'Rank' in col]
    df['Volatility'] = df[rank_cols].std(axis=1)
    # Normalize volatility to a 1-10 scale for easier interpretation
    df['Volatility'] = 1 + 9 * (df['Volatility'] - df['Volatility'].min()) / (df['Volatility'].max() - df['Volatility'].min())
    df['Volatility'] = df['Volatility'].fillna(5) # Fill NaN with average volatility

    # Calculate Tiers using K-Means Clustering
    df = calculate_tiers(df)

    # --- 3. Final Cleaning and Export ---
    # Select and rename columns for the final output
    df_final = df[[
        'Player', 'Team', 'Pos', 'VORP', 'Tier', 'Volatility', 'ADP', 'CBS_Rank',
        'ESPN_Rank', 'FantasyPros_Rank', 'Pass_Yds', 'Pass_TD', 'Int', 'Rush_Yds',
        'Rush_TD', 'Rec', 'Rec_Yds', 'Rec_TD'
    ]].copy()

    # Sort by VORP for a more meaningful default order
    df_final = df_final.sort_values(by='VORP', ascending=False).reset_index(drop=True)
    df_final['Rank'] = df_final.index + 1 # Add a new overall rank based on VORP

    # Convert to JSON
    output_path = f'processed/Projections-{year}.json'
    df_final.to_json(output_path, orient='records', indent=2)
    print(f"Successfully created aggregated projections at: {output_path}")

def load_projections(year):
    """Loads and merges projection data from multiple sources."""
    projection_files = [f for f in os.listdir(f'raw/projections') if f.endswith(f'-{year}.csv')]
    df_list = []
    for file in projection_files:
        source = file.split('-')[0]
        df_source = pd.read_csv(f'raw/projections/{file}')
        # Basic cleaning and standardizing
        df_source['Player'] = df_source['Player'].apply(standardize_player_name)
        # Rename columns to be source-specific
        df_source = df_source.rename(columns={
            'Rank': f'{source}_Rank',
            'Overall': f'{source}_Rank'
        })
        df_list.append(df_source)

    # Merge all projections, averaging the stats
    df_merged = df_list[0]
    for df_next in df_list[1:]:
        df_merged = pd.merge(df_merged, df_next, on='Player', how='outer', suffixes=(f'_{len(df_list)}', ''))

    # Group by player and average all numeric stats
    numeric_cols = df_merged.select_dtypes(include=np.number).columns
    df_agg = df_merged.groupby('Player').mean()[numeric_cols].reset_index()

    # Consolidate non-numeric data
    meta_cols = df_merged.select_dtypes(exclude=np.number).drop_duplicates(subset=['Player'])
    df_final = pd.merge(df_agg, meta_cols, on='Player', how='left')

    # Calculate consensus projected points
    df_final['Projected_Points'] = (
        df_final.get('Pass_Yds', 0) / 25 +
        df_final.get('Pass_TD', 0) * 4 -
        df_final.get('Int', 0) * 2 +
        df_final.get('Rush_Yds', 0) / 10 +
        df_final.get('Rush_TD', 0) * 6 +
        df_final.get('Rec', 0) * 0.5 + # 0.5 PPR
        df_final.get('Rec_Yds', 0) / 10 +
        df_final.get('Rec_TD', 0) * 6
    ).round(2)

    return df_final

def load_adp(year):
    """Loads and cleans ADP data."""
    adp_path = f'raw/adp/FantasyPros-{year}.csv'
    df_adp = pd.read_csv(adp_path)
    df_adp['Player'] = df_adp['Player'].apply(standardize_player_name)
    return df_adp[['Player', 'ADP']]

def standardize_player_name(name):
    """Removes suffixes like 'Jr.', 'Sr.', 'II', etc."""
    return ' '.join(name.replace('.', '').split()[:2]) # Keep first two parts of name

def calculate_vorp(df):
    """Calculates Value Over Replacement Player."""
    df_sorted = df.sort_values(by='Projected_Points', ascending=False)
    positions = df_sorted['Pos'].unique()
    vorp_baselines = {}

    # Define replacement levels (e.g., QB20, RB40, etc.)
    replacement_levels = {'QB': 20, 'RB': 40, 'WR': 40, 'TE': 15}

    for pos in positions:
        if pos in replacement_levels:
            pos_df = df_sorted[df_sorted['Pos'] == pos]
            replacement_player_index = replacement_levels[pos]
            if len(pos_df) > replacement_player_index:
                baseline_score = pos_df.iloc[replacement_player_index]['Projected_Points']
                vorp_baselines[pos] = baseline_score
            else:
                vorp_baselines[pos] = 0 # Fallback if not enough players

    df['VORP'] = df.apply(
        lambda row: round(row['Projected_Points'] - vorp_baselines.get(row['Pos'], 0), 2),
        axis=1
    )
    return df

def calculate_tiers(df):
    """Calculates positional tiers using K-Means clustering."""
    df['Tier'] = 0
    positions = df['Pos'].unique()

    # Define number of tiers per position
    tier_counts = {'QB': 8, 'RB': 10, 'WR': 10, 'TE': 7}

    for pos in positions:
        if pos in tier_counts:
            pos_df = df[df['Pos'] == pos].copy()
            if len(pos_df) < tier_counts[pos]: continue

            # Features for clustering: VORP and ADP
            features = pos_df[['VORP', 'ADP']].fillna(pos_df[['VORP', 'ADP']].mean())
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)

            kmeans = KMeans(n_clusters=tier_counts[pos], random_state=42, n_init=10)
            pos_df['cluster'] = kmeans.fit_predict(features_scaled)

            # Order clusters by VORP to create tiers
            cluster_order = pos_df.groupby('cluster')['VORP'].mean().sort_values(ascending=False).index
            tier_map = {cluster_id: i + 1 for i, cluster_id in enumerate(cluster_order)}
            pos_df['Tier'] = pos_df['cluster'].map(tier_map)

            # Update the main dataframe
            df.update(pos_df['Tier'])

    return df

if __name__ == '__main__':
    if len(sys.argv) > 1:
        year = sys.argv[1]
        aggregate_data(year)
    else:
        print("Error: Please provide a year. Usage: python aggregate.py 2025")
