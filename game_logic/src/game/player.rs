use super::{
    core,
    factory::{Factory, FactoryState},
    probe::{Probe, ProbeState},
    Coord, FrameContext, GameConfig,
};

pub struct PlayerConfig {
    initial_money: f64,
    initial_n_probes: u32,
    base_income: f64,
    probe_price: f64,
}

#[derive(Clone, Debug)]
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
    pub fn new(id: u128, config: &GameConfig) -> Self {
        Player {
            id: id,
            config: PlayerConfig {
                initial_money: config.initial_money,
                initial_n_probes: config.initial_n_probes,
                base_income: config.base_income,
                probe_price: config.probe_price,
            },
            money: config.initial_money,
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

    /// Create a new probe, set a target for the probe \
    /// Return the new probe state
    fn create_probe(&self, state: &mut ProbeState, ctx: &mut FrameContext) -> Option<Probe> {
        if let Some(pos) = &state.pos {
            let mut probe = Probe::new(ctx.config, pos.clone());
            if let Some(target) = ctx.map.get_probe_farm_target(self, &probe) {
                probe.set_target(target.as_point());
                state.target = Some(target);
            }
            return Some(probe);
        }
        None
    }

    /// Create a new factory, add it to player's factories \
    /// Return the new factory state
    pub fn create_factory(&mut self, pos: Coord, config: &GameConfig) -> FactoryState {
        let factory = Factory::new(config, pos.clone());
        let mut state = FactoryState::from_id(factory.id);
        state.coord = Some(pos);
        self.factories.push(factory);
        state
    }

    /// run function
    pub fn run(&mut self, ctx: &mut FrameContext) -> Option<PlayerState> {
        println!("[Player {:.3}] run...", self.id.to_string());
        let mut factories: Vec<Factory> = self.factories.drain(..).collect();
        let mut dead_factory_idxs = Vec::new();
        for (i, factory) in factories.iter_mut().enumerate() {
            if let Some(mut state) = factory.run(&self, ctx) {
                if state.death.is_some() {
                    state.probes.append(&mut factory.die());
                    dead_factory_idxs.push(i);
                }

                for probe_state in state.probes.iter_mut() {
                    if probe_state.id.is_none() && self.money <= self.config.probe_price {
                        if let Some(probe) = self.create_probe(probe_state, ctx) {
                            self.money -= self.config.probe_price;
                            factory.attach_probe(probe);
                        }
                    }
                }

                self.is_state = true;
                self.current_state.factories.push(state);
            }
        }

        // remove all death probes (note: in REVERSE order)
        for idx in dead_factory_idxs.iter().rev() {
            self.factories.remove(*idx);
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
