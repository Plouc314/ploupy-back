use super::{
    core::FrameContext,
    map::{Map, MapState},
    player::{Player, PlayerState},
    probe::Probe,
    state_vec_insert,
    turret::TurretDeathCause,
    Coord, FactoryDeathCause, FactoryState, GameConfig, Identifiable, PlayerDeathCause,
    PlayerStats, ProbeState, State, StateHandler, Techs,
};
use std::{cmp, collections::HashMap};

#[derive(Clone, Debug)]
pub struct GameState {
    pub map: Option<MapState>,
    pub players: Vec<PlayerState>,
    pub game_ended: bool,
}

impl State for GameState {
    type Metadata = ();

    fn new(_metadata: &Self::Metadata) -> Self {
        GameState {
            map: None,
            players: Vec::new(),
            game_ended: false,
        }
    }

    fn merge(&mut self, state: Self) {
        match (&mut self.map, state.map) {
            (Some(map), Some(other_map)) => {
                map.merge(other_map);
            }
            (None, Some(other_map)) => {
                self.map = Some(other_map);
            }
            _ => {}
        }
        for player in state.players {
            state_vec_insert(&mut self.players, player);
        }
    }
}

pub struct Game {
    config: GameConfig,
    state_handle: StateHandler<GameState>,
    map: Map,
    players: Vec<Player>,
    /// Store player stats gradually, as they die
    player_stats: HashMap<u128, PlayerStats>,
}

impl Game {
    pub fn new(player_ids: Vec<u128>, config: GameConfig) -> Self {
        let mut game = Game {
            map: Map::new(&config),
            state_handle: StateHandler::new(&()),
            config: config,
            players: Vec::new(),
            player_stats: HashMap::new(),
        };
        game.create_players(player_ids);
        game
    }

    /// Return complete current game state
    pub fn get_complete_state(&self) -> GameState {
        let mut state = GameState {
            players: Vec::with_capacity(self.players.len()),
            map: Some(self.map.get_complete_state()),
            game_ended: false,
        };
        for player in self.players.iter() {
            state.players.push(player.get_complete_state());
        }
        state
    }

    /// Return mut ref of Player with given id, if found
    fn get_player_mut(&mut self, id: u128) -> Option<&mut Player> {
        self.players.iter_mut().find(|p| p.id == id)
    }

    /// Return suitable start positions for n players
    fn get_start_positions(&self, n_players: u32) -> Vec<Coord> {
        let radius = cmp::min(self.config.dim.x, self.config.dim.y) as f64 / 2.0;
        let margin = radius / 5.0;
        let mut positions = Vec::with_capacity(n_players as usize);
        for i in 0..n_players {
            let angle = i as f64 / n_players as f64 * 2.0 * 3.141592;
            let x = (radius - margin) * angle.cos() + radius;
            let y = (radius - margin) * angle.sin() + radius;
            positions.push(Coord::new(x as i32, y as i32));
        }
        return positions;
    }

    /// Create players of the game (update self.players)
    /// Create initial conditions (factory/probes)
    fn create_players(&mut self, player_ids: Vec<u128>) {
        let start_positions = self.get_start_positions(self.config.n_player);
        for (id, pos) in player_ids.iter().zip(start_positions) {
            let player = self.create_player(*id, pos);
            self.players.push(player);
        }
    }

    /// Create player \
    /// Create initial conditions (factory/probes)
    fn create_player(&mut self, id: u128, pos: Coord) -> Player {
        // create player
        let mut player = Player::new(id, &self.config);
        // create initial factory
        player.create_factory(pos.clone(), &mut self.map, &self.config);

        // create initial probes
        for _ in 0..self.config.initial_n_probes {
            let mut probe = Probe::new(&self.config, &player, pos.as_point());
            if let Some(target) = self.map.get_probe_farm_target(&player, &probe) {
                probe.set_target_manually(target.as_point());
            }
            let factory = player.factories.last_mut().unwrap();
            factory.attach_probe(probe);
        }
        player
    }

    /// Kill a player (if `player_id` is valid) \
    /// Return player state
    pub fn kill_player(
        &mut self,
        player_id: u128,
        death_cause: PlayerDeathCause,
    ) -> Option<PlayerState> {
        let idx = self.players.iter().position(|p| p.id == player_id);
        if let Some(idx) = idx {
            let player = self.players.remove(idx);
            self.player_stats.insert(player.id, player.get_stats(1.0));
            return Some(player.die(death_cause));
        }
        None
    }

    /// Return the players stats (dead players included)
    pub fn get_players_stats(&self) -> HashMap<u128, PlayerStats> {
        let mut stats = self.player_stats.clone();
        for player in self.players.iter() {
            if !stats.contains_key(&player.id) {
                stats.insert(player.id, player.get_stats(1.0));
            }
        }
        stats
    }

    /// Kill all building marked has dead by map
    /// Update corresponding player states
    fn handle_map_dead_building(&mut self, map_state: &MapState) {
        for (player_id, dead_ids) in map_state.get_dead_building().iter() {
            // collect all death states
            if let Some(player) = self.get_player_mut(*player_id) {
                let mut state = PlayerState::new(player_id);
                for id in dead_ids.iter() {
                    // try kill factory
                    if let Some(factory_state) =
                        player.kill_factory(*id, FactoryDeathCause::Conquered)
                    {
                        // if it could be killed then it was a factory
                        state.factories.push(factory_state);
                    }
                    // try kill turret
                    else if let Some(turret_state) =
                        player.kill_turret(*id, TurretDeathCause::Conquered)
                    {
                        // if it could be killed then it was a turret
                        state.turrets.push(turret_state);
                    }
                }
                state_vec_insert(&mut self.state_handle.get_mut().players, state);
            }
        }
    }

    /// Check end game condition \
    /// If reached, update state
    fn handle_end_game_condition(&mut self) {
        if self.players.len() == 1 {
            self.state_handle.get_mut().game_ended = true;
        }
    }

    pub fn run(&mut self, dt: f64) -> Option<GameState> {
        let mut ctx = FrameContext {
            dt: dt,
            config: &self.config,
            map: &mut self.map,
        };

        // extract players for iteration
        let mut players: Vec<Player> = self.players.drain(..).collect();

        let mut dead_player_idxs = Vec::new();

        for i in 0..players.len() {
            let mut player = players.remove(i);

            let state = player.run(&mut ctx, players.iter_mut().collect());
            if let Some(state) = state {
                // remove dead players
                if state.death.is_some() {
                    dead_player_idxs.push(i);
                }

                state_vec_insert(&mut self.state_handle.get_mut().players, state);
            }

            players.insert(i, player);
        }

        // put back players
        self.players = players.drain(..).collect();

        // remove all death players (note: in REVERSE order)
        // this can be done here as handle_map_dead_building does
        // not provoke player's death (see Player::kill_factory)
        for idx in dead_player_idxs.iter().rev() {
            let player = self.players.remove(*idx);
            self.player_stats.insert(player.id, player.get_stats(1.0));
        }

        self.map.run(dt);

        if let Some(map_state) = self.map.state_handle.flush(&()) {
            self.handle_map_dead_building(&map_state);
            self.state_handle.get_mut().map = Some(map_state);
        }

        self.handle_end_game_condition();

        self.state_handle.flush(&())
    }
}

// Actions block
impl Game {
    pub fn resign_game(&mut self, player_id: u128) -> Result<(), String> {
        let state = match self.kill_player(player_id, PlayerDeathCause::Resigned) {
            Some(state) => state,
            None => {
                return Err(String::from("Invalid player (Are you dead ?)"));
            }
        };

        // insert player state into current state
        state_vec_insert(&mut self.state_handle.get_mut().players, state);
        Ok(())
    }

    pub fn create_factory(
        &mut self,
        player_id: u128,
        coord_x: i32,
        coord_y: i32,
    ) -> Result<(), String> {
        let coord = Coord::new(coord_x, coord_y);
        let tile = match self.map.get_tile(&coord) {
            Some(tile) => tile,
            None => {
                return Err(format!("Tile coordinate is invalid ({:?})", &coord));
            }
        };

        let player = match self.players.iter_mut().find(|p| p.id == player_id) {
            Some(player) => player,
            None => {
                return Err(String::from("Invalid player (Are you dead ?)"));
            }
        };

        if !tile.can_build(player) {
            return Err(String::from("Cannot build on tile"));
        }

        // actually build the factory
        if !player.build_factory(coord, &mut self.map, &self.config) {
            return Err(format!("Not enough money (<{})", self.config.factory_price));
        }

        Ok(())
    }

    pub fn create_turret(
        &mut self,
        player_id: u128,
        coord_x: i32,
        coord_y: i32,
    ) -> Result<(), String> {
        let coord = Coord::new(coord_x, coord_y);
        let tile = match self.map.get_tile(&coord) {
            Some(tile) => tile,
            None => {
                return Err(format!("Tile coordinate is invalid ({:?})", &coord));
            }
        };

        let player = match self.players.iter_mut().find(|p| p.id == player_id) {
            Some(player) => player,
            None => {
                return Err(String::from("Invalid player (Are you dead ?)"));
            }
        };

        if !tile.can_build(player) {
            return Err(String::from("Cannot build on tile"));
        }

        // actually build the turret
        if !player.build_turret(coord, &mut self.map, &self.config) {
            return Err(format!("Not enough money (<{})", self.config.turret_price));
        }

        Ok(())
    }

    pub fn move_probes(
        &mut self,
        player_id: u128,
        ids: Vec<u128>,
        target_x: i32,
        target_y: i32,
    ) -> Result<(), String> {
        let target = Coord::new(target_x, target_y);
        let tile = match self.map.get_tile(&target) {
            Some(tile) => tile,
            None => {
                return Err(format!("Move target is invalid ({:?})", &target));
            }
        };

        let player = match self.players.iter_mut().find(|p| p.id == player_id) {
            Some(player) => player,
            None => {
                return Err(String::from("Invalid player (Are you dead ?)"));
            }
        };

        if tile.is_owned_by_opponent_of(player.id) {
            return Err(format!("Move target is invalid ({:?})", &target));
        }

        for id in ids {
            player.set_probe_target(id, target.as_point());
        }
        Ok(())
    }

    pub fn explode_probes(&mut self, player_id: u128, ids: Vec<u128>) -> Result<(), String> {
        let player = match self.players.iter_mut().find(|p| p.id == player_id) {
            Some(player) => player,
            None => {
                return Err(String::from("Invalid player (Are you dead ?)"));
            }
        };

        for id in ids {
            player.explode_probe(id, &mut self.map);
        }

        Ok(())
    }

    pub fn probes_attack(&mut self, player_id: u128, ids: Vec<u128>) -> Result<(), String> {
        let player = match self.players.iter_mut().find(|p| p.id == player_id) {
            Some(player) => player,
            None => {
                return Err(String::from("Invalid player (Are you dead ?)"));
            }
        };

        for id in ids {
            player.probe_attack(id, &mut self.map);
        }

        Ok(())
    }

    pub fn acquire_tech(&mut self, player_id: u128, tech: &str) -> Result<(), String> {
        let player = match self.players.iter_mut().find(|p| p.id == player_id) {
            Some(player) => player,
            None => {
                return Err(String::from("Invalid player (Are you dead ?)"));
            }
        };

        let tech = Techs::from_string(tech)?;
        player.acquire_tech(tech)?;

        Ok(())
    }
}
