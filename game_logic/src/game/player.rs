use std::collections::HashMap;

use super::{
    core,
    factory::{Factory, FactoryState},
    probe::{Probe, ProbeState},
    FrameContext, GameConfig,
};

pub struct PlayerConfig {
    initial_money: f64,
    initial_n_probes: u32,
    base_income: f64,
    probe_price: f64,
}

pub struct PlayerState {
    pub id: u128,
    pub factories: Vec<FactoryState>,
}

impl PlayerState {
    pub fn from_id(id: u128) -> Self {
        PlayerState {
            id: id,
            factories: Vec::new(),
        }
    }
}

pub struct Player {
    pub id: u128,
    config: PlayerConfig,
    money: f64,
    pub factories: Vec<Factory>,
    /// Store potential player state at this frame
    /// used to gradually build player state during
    /// run() function (see mut_state)
    /// Should not be dealt with directly
    current_state: PlayerState,
    /// Indicates if a player state was built in
    /// the current frame
    is_state: bool,
}

impl Player {
    pub fn new(config: &GameConfig) -> Self {
        let id = core::generate_unique_id();
        Player {
            id: id,
            config: PlayerConfig {
                initial_money: config.initial_money,
                initial_n_probes: config.initial_n_probes,
                base_income: config.base_income,
                probe_price: config.probe_price,
            },
            money: 0.0,
            factories: Vec::new(),
            current_state: PlayerState::from_id(id),
            is_state: false,
        }
    }

    /// Reset current state
    /// In case is_state is true
    /// create new PlayerState instance
    fn reset_state(&mut self) {
        if self.is_state {
            self.current_state = PlayerState::from_id(self.id);
        }
        self.is_state = false
    }

    /// Return the current state
    /// AND stores that there is a player state
    /// (see self.is_state)
    fn mut_state(&mut self) -> &mut PlayerState {
        self.is_state = true;
        &mut self.current_state
    }

    /// create a new probe
    fn create_probe(&mut self, state: &mut ProbeState, ctx: &mut FrameContext) -> Option<Probe> {
        if self.money <= self.config.probe_price {
            self.money -= self.config.probe_price;
            if let Some(pos) = &state.pos {
                let mut probe = Probe::new(ctx.config, pos.clone());
                if let Some(target) = ctx.map.get_probe_farm_target(self, &probe) {
                    probe.set_target(target.as_point());
                    state.target = Some(target);
                }
                return Some(probe);
            }
        }
        None
    }

    /// run function
    pub fn run(&mut self, ctx: &mut FrameContext) -> Option<PlayerState> {
        let mut factories: Vec<Factory> = self.factories.drain(..).collect();
        let mut dead_factory_idxs = Vec::new();
        for (i, factory) in factories.iter_mut().enumerate() {
            if let Some(mut state) = factory.run(&self, ctx) {
                if state.death.is_some() {
                    factory.die();
                    dead_factory_idxs.push(i);
                }

                for probe_state in state.probes.iter_mut() {
                    if probe_state.id.is_none() {
                        if let Some(probe) = self.create_probe(probe_state, ctx) {
                            factory.attach_probe(probe);
                        }
                    }
                }

                self.is_state = true;
                self.current_state.factories.push(state);
            }
        }

        // remove all death probes
        for idx in dead_factory_idxs {
            self.factories.remove(idx);
        }

        None
    }
}
