import { DeleteOutlined } from '@ant-design/icons';
import { Button } from 'antd';
import * as React from 'react';
import { Player } from '../lib/models/Player'; // IMPORTANT: Use the new unified Player model

// Helper functions for styling the new data, placed outside the class
const getVorpColor = (vorp: number) => {
  if (vorp > 60) return '#2ca02c'; // Strong green
  if (vorp > 30) return '#98df8a'; // Light green
  if (vorp > 0) return '#6f6f6f';  // Neutral gray
  return '#d62728'; // Red
};

const getTierColor = (tier: number) => {
  const colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'];
  return tier ? colors[(tier - 1) % colors.length] : '#ccc'; // Handle null/0 tiers gracefully
};

const getVolatilityColor = (volatility: number) => {
  if (volatility > 7) return '#d62728'; // High risk (Red)
  if (volatility > 4) return '#ff7f0e'; // Medium risk (Orange)
  return '#2ca02c'; // Low risk (Green)
};


// The props interface is updated to use the new Player model
interface IPlayerRowProps {
  byeWeekConflict: boolean;
  draftSoon: boolean;
  inValuablePosition: boolean;
  mobile: boolean;
  onPickPlayer: (player: Player) => void;
  player: Player; // Use the new Player type
  rbHandcuff: boolean;
  recommended: boolean;
  onRemovePlayer: (player: Player) => void;
}

/**
 * A single player row in the PlayerTable.
 * Shows name, team, and the new VORP, Tier, and Risk metrics.
 */
export default class PlayerTableRow extends React.Component<IPlayerRowProps> {
  public render() {
    const {
      byeWeekConflict,
      draftSoon,
      inValuablePosition,
      mobile,
      onPickPlayer,
      player,
      rbHandcuff,
      recommended,
      onRemovePlayer,
    } = this.props;

    // The main JSX structure is preserved, but the data columns are updated
    return (
      <div onClick={() => onPickPlayer(player)} className={inValuablePosition || mobile ? 'row' : 'row row-inactive'}>
        <div className="col col-name">
          <p>{player.tableName || player.Player}</p>
          {/* Informational dots are preserved */}
          {recommended && !mobile && <div className="dot green-dot" title="Recommended"/>}
          {rbHandcuff && !mobile && <div className="dot blue-dot" title="Handcuff"/>}
          {draftSoon ? <div className="dot orange-dot" title="Draft Soon"/> : null}
          {byeWeekConflict && !mobile && <div className="dot red-dot" title="BYE Conflict"/>}
        </div>
        <p className="col col-pos">{player.Pos}</p>
        <p className="col col-team">{player.Team}</p>

        {/* --- NEW/UPDATED COLUMNS --- */}
        <p className="col col-vor" style={{ fontWeight: 'bold', color: getVorpColor(player.VORP) }}>
            {player.VORP.toFixed(1)}
        </p>
        <p className="col" style={{ color: 'white', textAlign: 'center' }}>
            <span style={{backgroundColor: getTierColor(player.Tier), padding: '2px 8px', borderRadius: '4px'}}>
                {player.Tier || 'N/A'}
            </span>
        </p>
        <p className="col" style={{ color: getVolatilityColor(player.Volatility), fontWeight: 'bold' }}>
            {player.Volatility.toFixed(1)}
        </p>
        {/* --- END NEW/UPDATED COLUMNS --- */}
        
        {!mobile && (
          <>
            <p className="col col-adp">{player.ADP ? player.ADP.toFixed(1) : ''}</p>
            <div className="col col-remove">
              <Button
                icon={<DeleteOutlined />}
                size="small"
                type="text"
                className="remove-player-button"
                style={{ marginRight: 10 }}
                onClick={(e) => {
                  e.stopPropagation(); // Prevent the row's onClick from firing
                  onRemovePlayer(player);
                }}
              />
            </div>
          </>
        )}
      </div>
    );
  }
}
