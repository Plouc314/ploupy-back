use std::{cell::RefCell, collections::HashMap, rc::Rc};

use super::*;

pub struct Game {
    config: GameConfig,
    map: Map,
    players: Vec<Rc<RefCell<Player>>>,
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

    /// create a new probe
    fn create_probe(&self, player: &Rc<Player>, state: &mut ProbeState) -> Option<Probe> {
        if let Some(pos) = &state.pos {
            let mut probe = Probe::new(&self.config, pos.clone());
            state.id = Some(probe.id);
            if let Some(target) = self.map.get_probe_farm_target(player, &probe) {
                probe.set_target(target.as_point());
                state.target = Some(target);
            }
            return Some(probe);
        }
        None
    }

    pub fn run(&mut self) {
        let mut ctx = FrameContext {
            dt: 1.0 / 60.0,
            config: &self.config,
            map: &mut self.map,
        };
        let mut player_states: Vec<PlayerState> = Vec::new();
        for player in self.players.iter() {
            let mut player = player.borrow_mut();
            let state = player.run(&mut ctx);
            if let Some(state) = state {
                player_states.push(state);
            }
        }
    }
}
