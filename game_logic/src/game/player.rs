use std::collections::HashSet;

use log;

use crate::game::state_vec_insert;

use super::{
    core::State,
    core::NOT_IDENTIFIABLE,
    factory::{Factory, FactoryState},
    probe::{Probe, ProbeState},
    turret::{Turret, TurretDeathCause, TurretState},
    Coord, Delayer, FactoryDeathCause, FactoryPolicy, FrameContext, GameConfig, Identifiable, Map,
    Point, StateHandler,
};

/// All player technologies
#[derive(Eq, Hash, PartialEq, Clone, Debug)]
pub enum Techs {
    PROBE_EXPLOSION_INTENSITY,
    PROBE_CLAIM_INTENSITY,
    PROBE_HP,
    FACTORY_BUILD_DELAY,
    FACTORY_PROBE_PRICE,
    FACTORY_MAX_PROBE,
    TURRET_SCOPE,
    TURRET_FIRE_DELAY,
    TURRET_MAINTENANCE_COSTS,
}

impl Techs {
    /// Create an instance from a string \
    /// Return an error in case the `string` is invalid
    pub fn from_string(string: &str) -> Result<Self, String> {
        match string {
            "PROBE_EXPLOSION_INTENSITY" => Ok(Techs::PROBE_EXPLOSION_INTENSITY),
            "PROBE_CLAIM_INTENSITY" => Ok(Techs::PROBE_CLAIM_INTENSITY),
            "PROBE_HP" => Ok(Techs::PROBE_HP),
            "FACTORY_BUILD_DELAY" => Ok(Techs::FACTORY_BUILD_DELAY),
            "FACTORY_PROBE_PRICE" => Ok(Techs::FACTORY_PROBE_PRICE),
            "FACTORY_MAX_PROBE" => Ok(Techs::FACTORY_MAX_PROBE),
            "TURRET_SCOPE" => Ok(Techs::TURRET_SCOPE),
            "TURRET_FIRE_DELAY" => Ok(Techs::TURRET_FIRE_DELAY),
            "TURRET_MAINTENANCE_COSTS" => Ok(Techs::TURRET_MAINTENANCE_COSTS),
            _ => Err(format!("Invalid tech name: {}", string)),
        }
    }

    /// Return if the `tech` doesn't conflicts with the `techs`
    pub fn is_tech_acquirable(techs: &HashSet<Self>, tech: &Self) -> bool {
        match tech {
            Techs::PROBE_CLAIM_INTENSITY => {
                !techs.contains(&Techs::PROBE_EXPLOSION_INTENSITY)
                    && !techs.contains(&Techs::PROBE_HP)
            }
            Techs::PROBE_EXPLOSION_INTENSITY => {
                !techs.contains(&Techs::PROBE_CLAIM_INTENSITY) && !techs.contains(&Techs::PROBE_HP)
            }
            Techs::PROBE_HP => {
                !techs.contains(&Techs::PROBE_CLAIM_INTENSITY)
                    && !techs.contains(&Techs::PROBE_EXPLOSION_INTENSITY)
            }
            Techs::FACTORY_BUILD_DELAY => {
                !techs.contains(&Techs::FACTORY_MAX_PROBE)
                    && !techs.contains(&Techs::FACTORY_PROBE_PRICE)
            }
            Techs::FACTORY_MAX_PROBE => {
                !techs.contains(&Techs::FACTORY_BUILD_DELAY)
                    && !techs.contains(&Techs::FACTORY_PROBE_PRICE)
            }
            Techs::FACTORY_PROBE_PRICE => {
                !techs.contains(&Techs::FACTORY_MAX_PROBE)
                    && !techs.contains(&Techs::FACTORY_BUILD_DELAY)
            }
            Techs::TURRET_FIRE_DELAY => {
                !techs.contains(&Techs::TURRET_MAINTENANCE_COSTS)
                    && !techs.contains(&Techs::TURRET_SCOPE)
            }
            Techs::TURRET_MAINTENANCE_COSTS => {
                !techs.contains(&Techs::TURRET_FIRE_DELAY) && !techs.contains(&Techs::TURRET_SCOPE)
            }
            Techs::TURRET_SCOPE => {
                !techs.contains(&Techs::TURRET_MAINTENANCE_COSTS)
                    && !techs.contains(&Techs::TURRET_FIRE_DELAY)
            }
        }
    }

    /// Return the price of `tech`
    pub fn get_tech_price(config: &PlayerConfig, tech: &Self) -> f64 {
        match tech {
            Techs::PROBE_CLAIM_INTENSITY => config.tech_probe_claim_intensity_price,
            Techs::PROBE_EXPLOSION_INTENSITY => config.tech_probe_explosion_intensity_price,
            Techs::PROBE_HP => config.tech_probe_hp_price,
            Techs::FACTORY_BUILD_DELAY => config.tech_factory_build_delay_price,
            Techs::FACTORY_MAX_PROBE => config.tech_factory_max_probe_price,
            Techs::FACTORY_PROBE_PRICE => config.tech_factory_probe_price_price,
            Techs::TURRET_FIRE_DELAY => config.tech_turret_fire_delay_price,
            Techs::TURRET_MAINTENANCE_COSTS => config.tech_turret_maintenance_costs_price,
            Techs::TURRET_SCOPE => config.tech_turret_scope_price,
        }
    }
}

#[derive(Clone, Debug)]
pub enum PlayerDeathCause {
    Defeated,
    Resigned,
}

pub struct PlayerConfig {
    income_rate: f64,
    base_income: f64,
    probe_price: f64,
    factory_price: f64,
    factory_build_probe_delay: f64,
    turret_price: f64,
    turret_fire_delay: f64,
    tech_factory_probe_price_decrease: f64,
    tech_factory_build_delay_decrease: f64,
    tech_turret_fire_delay_decrease: f64,
    tech_probe_explosion_intensity_price: f64,
    tech_probe_claim_intensity_price: f64,
    tech_probe_hp_price: f64,
    tech_factory_build_delay_price: f64,
    tech_factory_probe_price_price: f64,
    tech_factory_max_probe_price: f64,
    tech_turret_scope_price: f64,
    tech_turret_fire_delay_price: f64,
    tech_turret_maintenance_costs_price: f64,
}

#[derive(Clone)]
pub struct PlayerStats {
    pub money: Vec<f64>,
    pub occupation: Vec<u32>,
    pub factories: Vec<usize>,
    pub turrets: Vec<usize>,
    pub probes: Vec<usize>,
}

impl PlayerStats {
    pub fn new() -> Self {
        PlayerStats {
            money: Vec::new(),
            occupation: Vec::new(),
            factories: Vec::new(),
            turrets: Vec::new(),
            probes: Vec::new(),
        }
    }

    pub fn record(
        &mut self,
        time: f64,
        money: f64,
        occupation: u32,
        factories: usize,
        turrets: usize,
        probes: usize,
    ) {
        self.money.push(money);
        self.occupation.push(occupation);
        self.factories.push(factories);
        self.turrets.push(turrets);
        self.probes.push(probes);
    }
}

#[derive(Clone, Debug)]
pub struct PlayerState {
    pub id: u128,
    /// Only specified once, when the player dies
    pub death: Option<PlayerDeathCause>,
    pub money: Option<f64>,
    pub income: Option<f64>,
    pub techs: Vec<Techs>,
    pub factories: Vec<FactoryState>,
    pub turrets: Vec<TurretState>,
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
            techs: Vec::new(),
            factories: Vec::new(),
            turrets: Vec::new(),
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
        for turret in state.turrets {
            state_vec_insert(&mut self.turrets, turret);
        }
    }
}

pub struct Player {
    pub id: u128,
    config: PlayerConfig,
    state_handle: StateHandler<PlayerState>,
    stats: PlayerStats,
    techs: HashSet<Techs>,
    money: f64,
    pub factories: Vec<Factory>,
    pub turrets: Vec<Turret>,
    /// Delay to wait between two incomes
    delayer_income: Delayer,
}

impl Player {
    pub fn new(id: u128, config: &GameConfig) -> Self {
        Player {
            id: id,
            config: PlayerConfig {
                income_rate: config.income_rate,
                base_income: config.base_income,
                probe_price: config.probe_price,
                factory_price: config.factory_price,
                factory_build_probe_delay: config.factory_build_probe_delay,
                turret_price: config.turret_price,
                turret_fire_delay: config.turret_fire_delay,
                tech_factory_probe_price_decrease: config.tech_factory_probe_price_decrease,
                tech_factory_build_delay_decrease: config.tech_factory_build_delay_decrease,
                tech_turret_fire_delay_decrease: config.tech_turret_fire_delay_decrease,
                tech_probe_explosion_intensity_price: config.tech_probe_explosion_intensity_price,
                tech_probe_claim_intensity_price: config.tech_probe_claim_intensity_price,
                tech_probe_hp_price: config.tech_probe_hp_price,
                tech_factory_build_delay_price: config.tech_factory_build_delay_price,
                tech_factory_probe_price_price: config.tech_factory_probe_price_price,
                tech_factory_max_probe_price: config.tech_factory_max_probe_price,
                tech_turret_scope_price: config.tech_turret_scope_price,
                tech_turret_fire_delay_price: config.tech_turret_fire_delay_price,
                tech_turret_maintenance_costs_price: config.tech_turret_maintenance_costs_price,
            },
            state_handle: StateHandler::new(&id),
            stats: PlayerStats::new(),
            techs: HashSet::new(),
            money: config.initial_money,
            factories: Vec::new(),
            turrets: Vec::new(),
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
            techs: Vec::with_capacity(self.techs.len()),
            factories: Vec::with_capacity(self.factories.len()),
            turrets: Vec::with_capacity(self.turrets.len()),
        };
        for tech in self.techs.iter() {
            state.techs.push(tech.clone());
        }

        for factory in self.factories.iter() {
            state.factories.push(factory.get_complete_state());
        }
        for turret in self.turrets.iter() {
            state.turrets.push(turret.get_complete_state());
        }
        state
    }

    /// Player dies \
    /// Kill all player's factories & turrets \
    /// Return player state
    pub fn die(&self, death_cause: PlayerDeathCause) -> PlayerState {
        // kill player's factories
        let mut factory_states = Vec::with_capacity(self.factories.len());
        for factory in self.factories.iter() {
            factory_states.push(factory.die(FactoryDeathCause::Scrapped));
        }
        // kill player's turrets
        let mut turret_states = Vec::with_capacity(self.turrets.len());
        for turret in self.turrets.iter() {
            turret_states.push(turret.die(TurretDeathCause::Scrapped));
        }
        let mut state = PlayerState::new(&self.id);
        state.factories = factory_states;
        state.turrets = turret_states;
        state.death = Some(death_cause);
        state
    }

    /// Create a new probe, set a target for the probe \
    /// Return the new probe state
    fn create_probe(&self, state: &mut ProbeState, ctx: &mut FrameContext) -> Option<Probe> {
        if let Some(pos) = &state.pos {
            let mut probe = Probe::new(ctx.config, &self, pos.clone());
            // set id
            state.id = probe.id;
            // set target
            let target = match ctx.map.get_probe_farm_target(self, &probe) {
                Some(target) => target,
                None => pos.as_coord(),
            };

            probe.set_target_manually(target.as_point());
            state.target = Some(target);

            return Some(probe);
        }
        None
    }

    /// Iterator over each probe of each factory of player
    pub fn iter_mut_probes(&mut self) -> impl Iterator<Item = &mut Probe> {
        self.factories.iter_mut().flat_map(|f| f.iter_mut_probes())
    }

    /// Return the probe with the given id, if it exists
    fn get_mut_probe_by_id(&mut self, probe_id: u128) -> Option<&mut Probe> {
        self.factories
            .iter_mut()
            .find_map(|f| f.get_mut_probe_by_id(probe_id))
    }

    /// Return if the player has acquired the `tech`
    pub fn has_tech(&self, tech: &Techs) -> bool {
        self.techs.contains(tech)
    }

    /// Return the probe price, taking tech into account
    fn get_probe_price(&self) -> f64 {
        if self.has_tech(&Techs::FACTORY_PROBE_PRICE) {
            return self.config.probe_price - self.config.tech_factory_probe_price_decrease;
        }
        self.config.probe_price
    }

    /// Set a new target for the probe \
    /// Update involved states \
    /// Return if it could be done (if the probe exists)
    pub fn set_probe_target(&mut self, probe_id: u128, target: Point) -> bool {
        let probe = match self.get_mut_probe_by_id(probe_id) {
            Some(probe) => probe,
            None => {
                return false;
            }
        };
        probe.set_farm_target(target);
        true
    }

    /// Explode the probe \
    /// Update involved states \
    /// Return if it could be done (if the probe exists)
    pub fn explode_probe(&mut self, probe_id: u128, map: &mut Map) -> bool {
        let id = self.id;
        let is_expl_int = self.techs.contains(&Techs::PROBE_EXPLOSION_INTENSITY);
        let probe = match self.get_mut_probe_by_id(probe_id) {
            Some(probe) => probe,
            None => {
                return false;
            }
        };
        probe.explode(id, map, is_expl_int);
        true
    }

    /// Make the probe attack \
    /// Update involved states \
    /// Return if it could be done (if the probe exists)
    pub fn probe_attack(&mut self, probe_id: u128, map: &mut Map) -> bool {
        let id = self.id;
        let probe = match self.get_mut_probe_by_id(probe_id) {
            Some(probe) => probe,
            None => {
                return false;
            }
        };
        probe.set_attack(id, map);
        true
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

        map.set_new_building(&pos, factory.id).unwrap();

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
    ///
    /// Note: This function won't provoke the player's death
    /// even it's the last factory
    pub fn kill_factory(
        &mut self,
        factory_id: u128,
        death_cause: FactoryDeathCause,
    ) -> Option<FactoryState> {
        let idx = self.factories.iter().position(|f| f.id == factory_id);

        if let Some(idx) = idx {
            let factory = self.factories.remove(idx);
            return Some(factory.die(death_cause));
        }
        None
    }

    /// Create a new turret, add it to player's turrets,
    /// notify tile of new building. \
    /// Return the new turret state
    ///
    /// Note:
    /// - Do NOT care about player's money (see `build_turret` instead)
    /// - Won't fail in case of invalid pos (tile just won't be notified)
    pub fn create_turret(&mut self, pos: Coord, map: &mut Map, config: &GameConfig) -> TurretState {
        let turret = Turret::new(config, pos.clone());

        map.set_new_building(&pos, turret.id).unwrap();

        let mut state = TurretState::new(&turret.id);
        state.coord = Some(pos);
        self.turrets.push(turret);
        state
    }

    /// If player has enough money, create a new turret (see `create_turret`) \
    /// Return if the new turret could be created
    pub fn build_turret(&mut self, pos: Coord, map: &mut Map, config: &GameConfig) -> bool {
        if self.money < self.config.turret_price {
            return false;
        }
        self.money -= self.config.turret_price;
        self.state_handle.get_mut().money = Some(self.money);

        let state = self.create_turret(pos, map, config);
        state_vec_insert(&mut self.state_handle.get_mut().turrets, state);
        true
    }

    /// Kill a turret (if `turret_id` is valid) \
    /// Return turret state
    ///
    /// Note: This function won't provoke the player's death
    /// even it's the last turret
    pub fn kill_turret(
        &mut self,
        turret_id: u128,
        death_cause: TurretDeathCause,
    ) -> Option<TurretState> {
        let idx = self.turrets.iter().position(|t| t.id == turret_id);

        if let Some(idx) = idx {
            let turret = self.turrets.remove(idx);
            return Some(turret.die(death_cause));
        }
        None
    }

    /// Acquire the given technology \
    /// Return an error in case this fails
    pub fn acquire_tech(&mut self, tech: Techs) -> Result<(), String> {
        if self.techs.contains(&tech) {
            return Err(String::from("Technology already acquired."));
        }

        if !Techs::is_tech_acquirable(&self.techs, &tech) {
            return Err(String::from(
                "Can't acquire multiple technologies of same category.",
            ));
        }
        let price = Techs::get_tech_price(&self.config, &tech);

        if self.money < price {
            return Err(format!("Not enough money (<{})", price));
        }

        self.techs.insert(tech.clone());
        self.state_handle.get_mut().techs.push(tech);

        self.money -= price;
        self.state_handle.get_mut().money = Some(self.money);

        Ok(())
    }

    /// Compute the income prediction given the last computed income
    fn get_income_prediction(&self, income: f64) -> f64 {
        let mut prediction = income;
        // NOTE: do not take into account factory production costs for now
        // let probe_price = self.get_probe_price();
        // for factory in self.factories.iter() {
        //     match factory.get_policy() {
        //         FactoryPolicy::Produce => {
        //             prediction -= probe_price / self.config.factory_build_probe_delay;
        //         }
        //         _ => {}
        //     }
        // }
        prediction
    }

    /// Wait for income delay, then compute income,
    /// update money and compute income prediction
    fn update_money(&mut self, ctx: &mut FrameContext) {
        if !self.delayer_income.wait(ctx.dt) {
            return;
        }
        let total_occupation = ctx.map.get_player_occupation(&self);

        let mut income = self.config.base_income;
        income += total_occupation as f64 * self.config.income_rate;
        for factory in self.factories.iter() {
            income += factory.get_income();
        }
        for turret in self.turrets.iter() {
            income += turret.get_income(&self);
        }

        self.money = f64::max(self.money + income, 0.0);

        let prediction = self.get_income_prediction(income);

        self.state_handle.get_mut().money = Some(self.money);
        self.state_handle.get_mut().income = Some(prediction);

        self.record(total_occupation);
    }

    /// Record player metrics
    fn record(&mut self, total_occupation: u32) {
        self.stats.record(
            self.delayer_income.get_total_delayed(),
            self.money,
            total_occupation,
            self.factories.len(),
            self.turrets.len(),
            self.factories.iter().map(|f| f.get_num_probes()).sum(),
        );
    }

    /// Compile player state
    pub fn get_stats(&self, time_unit: f64) -> PlayerStats {
        self.stats.clone()
    }

    /// Handle new techs that require one-off actions
    fn handle_new_techs(&mut self) {
        let mut is_build_delay = false;
        let mut is_fire_delay = false;
        for tech in self.state_handle.get().techs.iter() {
            match tech {
                Techs::FACTORY_BUILD_DELAY => {
                    is_build_delay = true;
                }
                Techs::TURRET_FIRE_DELAY => {
                    is_fire_delay = true;
                }
                _ => {}
            };
        }

        if is_build_delay {
            for factory in self.factories.iter_mut() {
                factory.set_build_probe_delay(
                    self.config.factory_build_probe_delay
                        - self.config.tech_factory_build_delay_decrease,
                );
            }
        }
        if is_fire_delay {
            for turret in self.turrets.iter_mut() {
                turret.set_fire_delay(
                    self.config.turret_fire_delay - self.config.tech_turret_fire_delay_decrease,
                );
            }
        }
    }

    /// Check lose condition \
    /// If reached, kill player, update state
    fn handle_lose_condition(&mut self) {
        if self.factories.len() == 0 {
            self.state_handle
                .merge(self.die(PlayerDeathCause::Defeated));
        }
    }

    /// run function
    pub fn run(
        &mut self,
        ctx: &mut FrameContext,
        mut opponents: Vec<&mut Player>,
    ) -> Option<PlayerState> {
        log::debug!("[Player {:.3}] run...", self.id.to_string());

        let probe_price = self.get_probe_price();

        // extract factories for iteration
        let mut factories: Vec<Factory> = self.factories.drain(..).collect();

        let mut dead_factory_idxs = Vec::new();
        let mut is_money_change = false;

        for (i, factory) in factories.iter_mut().enumerate() {
            if let Some(mut state) = factory.run(&self, ctx) {
                // remove dead factories
                if state.death.is_some() {
                    dead_factory_idxs.push(i);
                }

                // create new probes
                for probe_state in state.probes.iter_mut() {
                    if probe_state.just_created() && self.money >= probe_price {
                        if let Some(probe) = self.create_probe(probe_state, ctx) {
                            is_money_change = true;
                            self.money -= probe_price;
                            factory.attach_probe(probe);
                        }
                    }
                }
                // remove probe states that could not be created
                state.probes = state
                    .probes
                    .into_iter()
                    .filter(|p| p.id != NOT_IDENTIFIABLE)
                    .collect();

                state_vec_insert(&mut self.state_handle.get_mut().factories, state);
            }
        }

        // put back factories
        self.factories = factories.drain(..).collect();

        // remove all death factories (note: in REVERSE order)
        for idx in dead_factory_idxs.iter().rev() {
            self.factories.remove(*idx);
        }

        // extract turrets for iteration
        let mut turrets: Vec<Turret> = self.turrets.drain(..).collect();

        let mut dead_turret_idxs = Vec::new();

        for (i, turret) in turrets.iter_mut().enumerate() {
            if let Some(state) = turret.run(&self, ctx, &mut opponents) {
                // remove dead turrets
                if state.death.is_some() {
                    dead_turret_idxs.push(i);
                }

                state_vec_insert(&mut self.state_handle.get_mut().turrets, state);
            }
        }

        // put back turrets
        self.turrets = turrets.drain(..).collect();

        // remove all death turrets (note: in REVERSE order)
        for idx in dead_turret_idxs.iter().rev() {
            self.turrets.remove(*idx);
        }

        self.update_money(ctx);
        self.handle_new_techs();
        self.handle_lose_condition();

        if is_money_change {
            self.state_handle.get_mut().money = Some(self.money);
        }

        self.state_handle.flush(&self.id)
    }
}
