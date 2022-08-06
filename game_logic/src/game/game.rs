use super::{
    core::FrameContext,
    map::{Map, MapState},
    player::{Player, PlayerState},
    probe::Probe,
    Coord, FactoryDeathCause, FactoryState, GameConfig, ProbeState,
};
use std::cmp;

#[derive(Clone, Debug)]
pub struct GameState {
    pub map: Option<MapState>,
    pub players: Vec<PlayerState>,
}

impl GameState {
    pub fn new() -> Self {
        GameState {
            map: None,
            players: Vec::new(),
        }
    }
}

pub struct Game {
    config: GameConfig,
    map: Map,
    players: Vec<Player>,
    /// Store potential game state at this frame
    /// used to gradually build game state during
    /// run() function (see mut_state)
    /// Should not be dealt with directly
    current_state: GameState,
    /// Indicates if a game state was built in
    /// the current frame
    is_state: bool,
}

impl Game {
    pub fn new(player_ids: Vec<u128>, config: GameConfig) -> Self {
        let mut game = Game {
            map: Map::new(&config),
            config: config,
            players: Vec::new(),
            current_state: GameState::new(),
            is_state: false,
        };
        game.create_players(player_ids);
        game
    }

    /// Return current state \
    /// In case is_state is true,
    /// reset current state and create new GameState instance
    pub fn flush_state(&mut self) -> Option<GameState> {
        if !self.is_state {
            return None;
        }
        let state = self.current_state.clone();
        self.current_state = GameState::new();
        self.is_state = false;
        Some(state)
    }

    /// Return complete current game state
    pub fn get_complete_state(&self) -> GameState {
        println!("GET COMPLETE STATE");
        let mut state = GameState {
            players: Vec::with_capacity(self.players.len()),
            map: Some(self.map.get_complete_state()),
        };
        for player in self.players.iter() {
            state.players.push(player.get_complete_state());
        }
        state
    }

    /// Return mut ref of Player with given id, if found
    fn get_player_mut(&mut self, id: u128) -> Option<&mut Player> {
        for player in self.players.iter_mut() {
            if player.id == id {
                return Some(player);
            }
        }
        None
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
    fn create_player(&self, id: u128, pos: Coord) -> Player {
        // create player
        let mut player = Player::new(id, &self.config);
        // create factory
        player.create_factory(pos.clone(), &self.config);

        // create initial probes
        for _ in 0..self.config.initial_n_probes {
            let mut probe = Probe::new(&self.config, pos.as_point());
            if let Some(target) = self.map.get_probe_farm_target(&player, &probe) {
                probe.set_target(target.as_point());
            }
            let factory = player.factories.last_mut().unwrap();
            factory.attach_probe(probe);
        }
        player
    }

    /// Update player state with given factory states
    /// In case player state doesn't already exists, create it
    fn update_player_state(&mut self, player_id: u128, mut factory_states: Vec<FactoryState>) {
        for player_state in self.current_state.players.iter_mut() {
            if player_state.id == player_id {
                player_state.factories.append(&mut factory_states);
                return;
            }
        }
        let mut player_state = PlayerState::from_id(player_id);
        player_state.factories.append(&mut factory_states);
        self.current_state.players.push(player_state);
    }

    /// Kill all building marked has dead by map
    /// Update corresponding player states
    fn handle_map_dead_building(&mut self, map_state: &MapState) {
        for (player_id, dead_ids) in map_state.get_dead_building().iter() {
            // collect all death states
            let mut factory_states = Vec::new();
            if let Some(player) = self.get_player_mut(*player_id) {
                for id in dead_ids.iter() {
                    // try kill factory (will later be turret too)
                    if let Some(mut probes) = player.kill_factory(*id) {
                        // if it could be killed then it was a factory
                        let mut factory_state = FactoryState::from_id(*id);
                        factory_state.death = Some(FactoryDeathCause::Conquered);
                        factory_state.probes.append(&mut probes);
                        factory_states.push(factory_state);
                    }
                }
            }
            self.update_player_state(*player_id, factory_states);
        }
    }

    pub fn run(&mut self) -> Option<GameState> {
        let mut ctx = FrameContext {
            dt: 1.0 / 60.0,
            config: &self.config,
            map: &mut self.map,
        };

        for player in self.players.iter_mut() {
            let state = player.run(&mut ctx);
            if let Some(state) = state {
                self.current_state.players.push(state);
                self.is_state = true;
            }
        }

        if let Some(map_state) = self.map.flush_state() {
            self.handle_map_dead_building(&map_state);
            self.current_state.map = Some(map_state);
            self.is_state = true;
        }

        self.flush_state()
    }
}
