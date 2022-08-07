use log;

use crate::game::state_vec_insert;

use super::{
    core::State,
    factory::{Factory, FactoryState},
    probe::{Probe, ProbeState},
    Coord, Delayer, FactoryDeathCause, FactoryPolicy, FrameContext, GameConfig, Identifiable, Map,
    StateHandler,
};

#[derive(Clone, Debug)]
pub enum PlayerDeathCause {
    Defeated,
    Resigned,
}

pub struct PlayerConfig {
    initial_money: f64,
    initial_n_probes: u32,
    base_income: f64,
    probe_price: f64,
    factory_price: f64,
    factory_build_probe_delay: f64,
}

#[derive(Clone, Debug)]
pub struct PlayerState {
    pub id: u128,
    /// Only specified once, when the player dies
    pub death: Option<PlayerDeathCause>,
    pub money: Option<f64>,
    pub income: Option<f64>,
    pub factories: Vec<FactoryState>,
}

impl Identifiable for PlayerState {
    fn id(&self) -> u128 {
        self.id
    }
}

impl State for PlayerState {
    type Metadata = u128;

    fn new(_metadata: &Self::Metadata) -> Self {
        PlayerState {
            id: *_metadata,
            death: None,
            money: None,
            income: None,
            factories: Vec::new(),
        }
    }

    fn merge(&mut self, state: Self) {
        if let Some(death) = state.death {
            self.death = Some(death);
        }
        if let Some(money) = state.money {
            self.money = Some(money);
        }
        if let Some(income) = state.income {
            self.income = Some(income);
        }
        for factory in state.factories {
            state_vec_insert(&mut self.factories, factory);
        }
    }
}

pub struct Player {
    pub id: u128,
    config: PlayerConfig,
    state_handle: StateHandler<PlayerState>,
    money: f64,
    pub factories: Vec<Factory>,
    /// Delay to wait between two incomes
    delayer_income: Delayer,
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
                factory_price: config.factory_price,
                factory_build_probe_delay: config.factory_build_probe_delay,
            },
            state_handle: StateHandler::new(&id),
            money: config.initial_money,
            factories: Vec::new(),
            delayer_income: Delayer::new(1.0),
        }
    }

    /// Return complete current player state
    pub fn get_complete_state(&self) -> PlayerState {
        let mut state = PlayerState {
            id: self.id,
            death: None,
            money: Some(self.money),
            income: Some(0.0),
            factories: Vec::with_capacity(self.factories.len()),
        };
        for factory in self.factories.iter() {
            state.factories.push(factory.get_complete_state());
        }
        state
    }

    /// Kill all player's factories \
    /// Return their states (with death cause)
    pub fn die(&self) -> Vec<FactoryState> {
        let mut factory_states = Vec::with_capacity(self.factories.len());
        for factory in self.factories.iter() {
            let mut state = FactoryState::new(&factory.id);
            state.death = Some(FactoryDeathCause::Scrapped);
            state.probes = factory.die();
            factory_states.push(state);
        }
        factory_states
    }

    /// Create a new probe, set a target for the probe \
    /// Return the new probe state
    fn create_probe(&self, state: &mut ProbeState, ctx: &mut FrameContext) -> Option<Probe> {
        if let Some(pos) = &state.pos {
            let mut probe = Probe::new(ctx.config, pos.clone());
            // set id
            state.id = probe.id;
            // set target
            if let Some(target) = ctx.map.get_probe_farm_target(self, &probe) {
                probe.set_target(target.as_point());
                state.target = Some(target);
            } else {
                log::warn!(
                    "[Player {:.3}] (create_probe) No target found",
                    self.id.to_string()
                );
            }
            return Some(probe);
        }
        None
    }

    /// Create a new factory, add it to player's factories,
    /// notify tile of new building. \
    /// Return the new factory state
    ///
    /// Note:
    /// - Do NOT care about player's money (see `build_factory` instead)
    /// - Won't fail in case of invalid pos (tile just won't be notified)
    pub fn create_factory(
        &mut self,
        pos: Coord,
        map: &mut Map,
        config: &GameConfig,
    ) -> FactoryState {
        let factory = Factory::new(config, pos.clone());

        if let Some(tile) = map.get_mut_tile(&pos) {
            tile.building_id = Some(factory.id);
        }

        let mut state = FactoryState::new(&factory.id);
        state.coord = Some(pos);
        self.factories.push(factory);
        state
    }

    /// If player has enough money, create a new factory (see `create_factory`) \
    /// Return if the new factory could be created
    pub fn build_factory(&mut self, pos: Coord, map: &mut Map, config: &GameConfig) -> bool {
        if self.money < self.config.factory_price {
            return false;
        }
        self.money -= self.config.factory_price;
        self.state_handle.get_mut().money = Some(self.money);

        let state = self.create_factory(pos, map, config);
        state_vec_insert(&mut self.state_handle.get_mut().factories, state);

        true
    }

    /// Kill a factory (if `factory_id` is valid) \
    /// Return factory state
    pub fn kill_factory(
        &mut self,
        factory_id: u128,
        death_cause: FactoryDeathCause,
    ) -> Option<FactoryState> {
        let idx = self.factories.iter().position(|f| f.id == factory_id);

        if let Some(idx) = idx {
            let factory = self.factories.remove(idx);
            let mut state = FactoryState::new(&factory.id);
            state.death = Some(death_cause);
            state.probes = factory.die();
            return Some(state);
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

        self.state_handle.get_mut().money = Some(self.money);
        self.state_handle.get_mut().income = Some(prediction);
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
                    if probe_state.just_created() && self.money >= self.config.probe_price {
                        if let Some(probe) = self.create_probe(probe_state, ctx) {
                            is_money_change = true;
                            self.money -= self.config.probe_price;
                            factory.attach_probe(probe);
                        }
                    }
                }

                state_vec_insert(&mut self.state_handle.get_mut().factories, state);
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
            self.state_handle.get_mut().money = Some(self.money);
        }

        self.state_handle.flush(&self.id)
    }
}
