use log;

use super::{
    core,
    factory::{Factory, FactoryState},
    probe::{Probe, ProbeState},
    Coord, Delayer, FactoryPolicy, FrameContext, GameConfig,
};

pub struct PlayerConfig {
    initial_money: f64,
    initial_n_probes: u32,
    base_income: f64,
    probe_price: f64,
    factory_build_probe_delay: f64,
}

#[derive(Clone, Debug)]
pub struct PlayerState {
    pub id: u128,
    pub money: Option<f64>,
    pub income: Option<f64>,
    pub factories: Vec<FactoryState>,
}

impl PlayerState {
    pub fn from_id(id: u128) -> Self {
        PlayerState {
            id: id,
            money: None,
            income: None,
            factories: Vec::new(),
        }
    }
}

pub struct Player {
    pub id: u128,
    config: PlayerConfig,
    money: f64,
    pub factories: Vec<Factory>,
    /// Delay to wait between two incomes
    delayer_income: Delayer,
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
                factory_build_probe_delay: config.factory_build_probe_delay,
            },
            money: config.initial_money,
            factories: Vec::new(),
            delayer_income: Delayer::new(1.0),
            current_state: PlayerState::from_id(id),
            is_state: false,
        }
    }

    /// Return current state \
    /// In case is_state is true,
    /// reset current state and create new PlayerState instance
    pub fn flush_state(&mut self) -> Option<PlayerState> {
        if !self.is_state {
            return None;
        }
        let state = self.current_state.clone();
        self.current_state = PlayerState::from_id(self.id);
        self.is_state = false;
        Some(state)
    }

    /// Return complete current player state
    pub fn get_complete_state(&self) -> PlayerState {
        println!("PLAYER COMPLETE STATE");
        let mut state = PlayerState {
            id: self.id,
            money: Some(self.money),
            income: Some(0.0),
            factories: Vec::with_capacity(self.factories.len()),
        };
        for factory in self.factories.iter() {
            state.factories.push(factory.get_complete_state());
        }
        state
    }

    /// Create a new probe, set a target for the probe \
    /// Return the new probe state
    fn create_probe(&self, state: &mut ProbeState, ctx: &mut FrameContext) -> Option<Probe> {
        println!("create probe: {:?}", state);
        if let Some(pos) = &state.pos {
            let mut probe = Probe::new(ctx.config, pos.clone());
            // set id
            state.id = Some(probe.id);
            // set target
            if let Some(target) = ctx.map.get_probe_farm_target(self, &probe) {
                probe.set_target(target.as_point());
                state.target = Some(target);
            } else {
                println!("No target found");
            }
            println!("done: {:?}", state);
            return Some(probe);
        }
        println!("Invalid pos {:?}", &state.pos);
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

    /// Kill a factory (if `factory_id` is valid) \
    /// Return probe states of dead probes (see `Factory.die()`)
    pub fn kill_factory(&mut self, factory_id: u128) -> Option<Vec<ProbeState>> {
        let mut idx = None;
        for (i, factory) in self.factories.iter_mut().enumerate() {
            if factory.id == factory_id {
                idx = Some(i);
                break;
            }
        }
        if let Some(idx) = idx {
            let mut factory = self.factories.remove(idx);
            return Some(factory.die());
        }
        None
    }

    /// Compute the income prediction given the last computed income
    fn get_income_prediction(&self, income: f64) -> f64 {
        let mut prediction = income;
        for factory in self.factories.iter() {
            match factory.get_policy() {
                FactoryPolicy::Produce => {
                    prediction -= self.config.probe_price / self.config.factory_build_probe_delay;
                }
                _ => {}
            }
        }
        prediction
    }

    /// Wait for income delay, then compute income,
    /// update money and compute income prediction
    fn update_money(&mut self, ctx: &mut FrameContext) {
        if !self.delayer_income.wait(ctx) {
            return;
        }
        let mut income = self.config.base_income;
        income += ctx.map.get_player_income(&self);
        for factory in self.factories.iter() {
            income += factory.get_income();
        }

        self.money += income;
        let prediction = self.get_income_prediction(income);

        self.current_state.money = Some(self.money);
        self.current_state.income = Some(prediction);
    }

    /// run function
    pub fn run(&mut self, ctx: &mut FrameContext) -> Option<PlayerState> {
        log::debug!("[Player {:.3}] run...", self.id.to_string());
        let mut factories: Vec<Factory> = self.factories.drain(..).collect();
        let mut dead_factory_idxs = Vec::new();
        let mut is_money_change = false;
        for (i, factory) in factories.iter_mut().enumerate() {
            if let Some(mut state) = factory.run(&self, ctx) {
                // handle death factories
                if state.death.is_some() {
                    state.probes.append(&mut factory.die());
                    dead_factory_idxs.push(i);
                }

                // create new probes
                for probe_state in state.probes.iter_mut() {
                    if probe_state.id.is_none() && self.money >= self.config.probe_price {
                        if let Some(probe) = self.create_probe(probe_state, ctx) {
                            is_money_change = true;
                            self.money -= self.config.probe_price;
                            factory.attach_probe(probe);
                        }
                    }
                }

                self.is_state = true;
                self.current_state.factories.push(state);
            }
        }

        // put back factories
        self.factories = factories.drain(..).collect();

        // remove all death factories (note: in REVERSE order)
        for idx in dead_factory_idxs.iter().rev() {
            self.factories.remove(*idx);
        }

        self.update_money(ctx);

        if is_money_change {
            self.current_state.money = Some(self.money);
        }

        self.flush_state()
    }
}
