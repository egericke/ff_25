import { Input, InputRef, Tooltip } from 'antd';
import * as React from 'react';
import { Player } from '../lib/models/Player'; // Use the new unified Player model
import PlayerTableRow from './PlayerTableRow';

/** All possible positions. ? Means any position, don't filter */
const filterPositions: Player['Pos'][] = ['QB', 'RB', 'WR', 'TE', 'DST', 'K'];

interface IPlayerTableProps {
  byeWeeks: { [key: number]: boolean };
  currentPick: number;
  draftSoon: boolean[];
  filteredPlayers: boolean[];
  mobile: boolean;
  nameFilter: string;
  onPickPlayer: (player: Player) => void;
  players: Player[]; // Use the new Player type
  positionsToShow: Player['Pos'][];
  rbHandcuffs: Set<Player>;
  recommended: Set<Player>; // names that are recommended
  resetPositionFilter: () => void; // reset positions
  onRemovePlayer: (player: Player) => void;
  setNameFilter: (e: React.ChangeEvent<HTMLInputElement>) => void;
  togglePositionFilter: (pos: Player['Pos'] | '?') => void; // Allow '?' for All
  skip: () => void;
  undo: () => void;
  valuedPositions: { [key: string]: boolean };
}

export default ({
  byeWeeks,
  draftSoon,
  filteredPlayers,
  nameFilter,
  mobile,
  onPickPlayer,
  players,
  positionsToShow,
  rbHandcuffs,
  recommended,
  onRemovePlayer,
  resetPositionFilter,
  setNameFilter,
  togglePositionFilter,
  skip,
  valuedPositions,
  undo,
}: IPlayerTableProps) => {
  const inputRef = React.createRef<InputRef>();

  return (
    <div className="PlayerTable Section">
      <div id="table-top-header" className="Stick-Section">
        <header>
          {!mobile && <h3>Players</h3>}

          {/* Name filter input element */}
          {!mobile && (
            <Input.Search
              autoFocus
              className="Player-Search"
              placeholder="Name"
              onChange={setNameFilter}
              value={nameFilter}
              ref={inputRef}
            />
          )}

          {/* Buttons for filtering on position */}
          <div className="PlayerTable-Position-Buttons">
            {/* "All" button first */}
            <button
              key="all"
              className={positionsToShow.length === 0 ? 'Active' : ''}
              onClick={() => togglePositionFilter('?')}>
              All
            </button>
            {/* Then specific positions */}
            {filterPositions.map((p) => (
              <button
                key={p}
                className={positionsToShow.indexOf(p) > -1 ? 'Active' : ''}
                onClick={() => togglePositionFilter(p)}>
                {p}
              </button>
            ))}
          </div>

          {!mobile && (
            <div className="Player-Table-Control-Buttons">
              <button className="Grayed skip-button" onClick={skip}>
                Skip
              </button>
              <button className="Grayed undo-button" onClick={undo}>
                Undo
              </button>
            </div>
          )}
        </header>

        {/* Legend for dots on the row */}
        <div className="Legend-Row">
          {!mobile && (
            <>
              <div className="dot green-dot" />
              <p className="small">Recommended</p>
              <div className="dot blue-dot" />
              <p className="small">RB handcuff</p>
              <div className="dot orange-dot" />
              <p className="small">Will be drafted soon</p>
              <div className="dot red-dot" />
              <p className="small">BYE week overlap</p>
            </>
          )}
        </div>
        
        {/* UPDATED TABLE HEADERS */}
        <div id="table-head">
            <p className="col col-name">Name</p>
            <p className="col col-pos">Pos</p>
            <p className="col col-team">Team</p>
            <p className="col" data-tip="Value over replacement">
                <Tooltip title="Value Over Replacement Player">
                    <span>VORP</span>
                </Tooltip>
            </p>
            <p className="col" data-tip="Positional Tier">
                <Tooltip title="Positional Tier">
                    <span>Tier</span>
                </Tooltip>
            </p>
            <p className="col" data-tip="Expert Disagreement / Risk">
                <Tooltip title="Expert Disagreement / Risk">
                    <span>Risk</span>
                </Tooltip>
            </p>
            {!mobile && (
                <>
                    <p className="col col-adp">
                        <Tooltip title="Average draft position">
                            <span>ADP</span>
                        </Tooltip>
                    </p>
                    <p className="col col-remove" style={{ paddingRight: 12 }}>
                        Remove
                    </p>
                </>
            )}
        </div>
      </div>

      <div id="table">
        <div id="table-body">
          {players
            .filter((_, i) => !filteredPlayers[i])
            .map((player: Player, i) => (
              <PlayerTableRow
                key={player.Rank} // Use a unique key like Rank
                mobile={mobile}
                onPickPlayer={(p: Player) => {
                  onPickPlayer(p);
                  resetPositionFilter();
                  inputRef.current?.focus();
                }}
                draftSoon={draftSoon[i]}
                byeWeekConflict={player.bye ? byeWeeks[player.bye] : false}
                inValuablePosition={valuedPositions[player.Pos]}
                player={player}
                rbHandcuff={rbHandcuffs.has(player)}
                recommended={recommended.has(player)}
                onRemovePlayer={(p: Player) => {
                  onRemovePlayer(p);
                  resetPositionFilter();
                  inputRef.current?.focus();
                }}
              />
            ))}
        </div>
      </div>
    </div>
  );
};
