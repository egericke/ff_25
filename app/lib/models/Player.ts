/**
 * Defines the types of roster positions available in the league.
 */
export type Position =
  | 'QB'
  | 'RB'
  | 'WR'
  | 'FLEX'
  | 'SUPERFLEX'
  | 'TE'
  | 'DST'
  | 'K'
  | 'BENCH'
  | '?'; // Represents an empty or unknown position

/**
 * Maps wildcard positions (like FLEX) to the standard positions they can hold.
 * This is used to determine which players can fill which roster spots.
 */
export const wildCardPositions: { [key: string]: Set<string> } = {
  QB: new Set([]),
  RB: new Set([]),
  WR: new Set([]),
  FLEX: new Set(['WR', 'RB', 'TE']),
  SUPERFLEX: new Set(['QB', 'WR', 'RB', 'TE']),
  TE: new Set([]),
  DST: new Set([]),
  K: new Set([]),
  BENCH: new Set([]),
  '?': new Set([]),
};

/**
 * The primary interface for a single player.
 * This combines the raw stats from the data pipeline (like passing yards)
 * with the new advanced metrics (like VORP) calculated by our script.
 */
export interface Player {
  // Core Identifying Info
  Rank: number;       // Overall rank, now based on VORP
  Player: string;
  Pos: 'QB' | 'RB' | 'WR' | 'TE' | 'DST' | 'K';
  Team: string;
  bye?: number;

  // Advanced Analytical Metrics
  VORP: number;       // Value Over Replacement Player - The most important value!
  Tier: number;       // Positional Tier, for spotting talent drop-offs
  Volatility: number; // Risk/disagreement metric (1-10 scale)
  ADP: number;        // Average Draft Position

  // Raw Stat Projections
  Pass_Yds: number;
  Pass_TD: number;
  Int: number;
  Rush_Yds: number;
  Rush_TD: number;
  Rec: number;
  Rec_Yds: number;
  Rec_TD: number;

  // Optional client-side fields
  href?: string;       // Link to player profile
  tableName?: string;  // Shortened name for display, e.g., "P. Mahomes"
}
