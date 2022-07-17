use super::{
    core::FrameContext,
    map::{Map, MapState},
    player::{Player, PlayerState},
    probe::Probe,
    Coord, GameConfig,
};
use std::cmp;

#[derive(Clone, Debug)]
pub struct GameState {
    map: Option<MapState>,
    players: Vec<PlayerState>,
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

    /// Reset current state
    /// In case is_state is true
    /// create new PlayerState instance
    fn reset_state(&mut self) {
        if self.is_state {
            self.current_state = GameState::new();
        }
        self.is_state = false
    }

    /// Return suitable start positions for n players
    fn get_start_positions(&self, n_players: u32) -> Vec<Coord> {
        let radius = cmp::min(self.config.dim.x, self.config.dim.y) as f64 / 2.0;
        let margin = radius / 5.0;
        let mut positions = Vec::with_capacity(n_players as usize);
        for i in 0..n_players {
            let angle = i as f64 / n_players as f64 * 2.0 * 3.141592;
            let x = (radius - margin) * angle.sin() + radius;
            let y = (radius - margin) * angle.cos() + radius;
            positions.push(Coord::new(x as i32, y as i32));
        }
        return positions;
    }

    /// Create players of the game (update self.players)
    /// Create initial conditions (factory/probes)
    fn create_players(&mut self, player_ids: Vec<u128>) {
        let start_positions = self.get_start_positions(self.config.n_player);
        println!("start positions {:?}", start_positions);
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
            self.current_state.map = Some(map_state);
            self.is_state = true;
        }

        // handle state
        let mut state = None;
        if self.is_state {
            state = Some(self.current_state.clone());
        }
        self.reset_state();
        state
    }
}
