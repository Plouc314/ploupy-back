use std::collections::HashMap;

use super::{
    core,
    factory::{Factory, FactoryState},
    probe::{Probe, ProbeState},
    FrameContext, GameConfig, Runnable,
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
    pub factories: HashMap<u128, Factory>,
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
            factories: HashMap::new(),
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
    fn create_probe(&self, state: &mut ProbeState, ctx: &mut FrameContext) -> Option<Probe> {
        // if let Some(pos) = &state.pos {
        //     let mut probe = Probe::new(self, ctx.config, pos.clone());
        //     if let Some(target) = ctx.map.get_probe_farm_target(self, &probe) {
        //         probe.set_target(target.as_point());
        //         state.target = Some(target);
        //     }
        //     return Some(probe);
        // }
        None
    }
}

impl Runnable for Player {
    type State = ();

    fn run(&mut self, ctx: &mut FrameContext) -> Option<Self::State> {
        let mut probe_to_creates: HashMap<u128, Vec<ProbeState>> = HashMap::new();
        let mut probe_states: HashMap<u128, Vec<ProbeState>> = HashMap::new();
        for (_, factory) in self.factories.iter_mut() {
            let state = factory.run(ctx);
            if let Some(state) = state {
                self.is_state = true;
                for probe_state in state.probes {
                    match probe_state.id {
                        None => {
                            if self.money <= self.config.probe_price {
                                self.money -= self.config.probe_price;
                                match probe_to_creates.get_mut(&factory.id) {
                                    None => {
                                        probe_to_creates.insert(factory.id, vec![probe_state]);
                                    }
                                    Some(states) => {
                                        states.push(probe_state);
                                    }
                                };
                            }
                        }
                        Some(_) => {
                            match probe_states.get_mut(&factory.id) {
                                None => {
                                    probe_states.insert(factory.id, vec![probe_state]);
                                }
                                Some(states) => {
                                    states.push(probe_state);
                                }
                            };
                        }
                    }
                }
            }
        }
        for (factory_id, mut states) in probe_to_creates {
            for state in states.iter_mut() {
                if let Some(probe) = self.create_probe(state, ctx) {
                    if let Some(factory) = self.factories.get_mut(&factory_id) {
                        factory.attach_probe(probe);
                    }
                }
            }
            match probe_states.get_mut(&factory_id) {
                None => {
                    probe_states.insert(factory_id, states);
                }
                Some(existing_states) => {
                    existing_states.extend(states);
                }
            };
        }

        None
    }
}
