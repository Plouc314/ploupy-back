use super::*;

pub struct Game {
    config: GameConfig,
    map: Map,
    players: Vec<Player>,
}

impl Game {
    pub fn new(config: GameConfig) -> Self {
        let map = Map::new(&config);
        return Game {
            config: config,
            map: map,
            players: Vec::new(),
        };
    }

    pub fn run(&mut self) {
        let mut ctx = FrameContext {
            dt: 1.0 / 60.0,
            config: &self.config,
            map: &mut self.map,
        };
        for player in self.players.iter_mut() {
            player.run(&mut ctx);
        }
    }
}
