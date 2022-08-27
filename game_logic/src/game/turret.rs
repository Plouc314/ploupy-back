use super::{
    core, Coord, Delayer, FrameContext, GameConfig, Identifiable, Player, Point, ProbeDeathCause,
    State, StateHandler, Techs,
};

pub enum TurretPolicy {
    Ready,
    Wait,
}

#[derive(Clone, Debug)]
pub enum TurretDeathCause {
    Conquered,
    Scrapped,
}

struct TurretConfig {
    turret_scope: f64,
    turret_damage: u32,
    turret_maintenance_costs: f64,
    tech_scope_increase: f64,
    tech_maintenance_costs_decrease: f64,
}

#[derive(Clone, Debug)]
pub struct TurretState {
    pub id: u128,
    /// Only specified once, when the turret dies
    pub death: Option<TurretDeathCause>,
    pub coord: Option<Coord>,
    /// id of the probe that was shot
    pub shot_id: Option<u128>,
}

impl Identifiable for TurretState {
    fn id(&self) -> u128 {
        self.id
    }
}

impl State for TurretState {
    type Metadata = u128;

    fn new(_metadata: &Self::Metadata) -> Self {
        TurretState {
            id: *_metadata,
            death: None,
            coord: None,
            shot_id: None,
        }
    }

    fn merge(&mut self, state: Self) {
        if let Some(death) = state.death {
            self.death = Some(death);
        }
        if let Some(coord) = state.coord {
            self.coord = Some(coord);
        }
    }
}

pub struct Turret {
    pub id: u128,
    config: TurretConfig,
    state_handle: StateHandler<TurretState>,
    policy: TurretPolicy,
    pos: Coord,
    /// Delay to wait to fire probe
    delayer_fire: Delayer,
}

impl Turret {
    pub fn new(config: &GameConfig, pos: Coord) -> Self {
        let id = core::generate_unique_id();
        Turret {
            id: id,
            config: TurretConfig {
                turret_scope: config.turret_scope,
                turret_damage: config.turret_damage,
                turret_maintenance_costs: config.turret_maintenance_costs,
                tech_scope_increase: config.tech_turret_scope_increase,
                tech_maintenance_costs_decrease: config.tech_turret_maintenance_costs_decrease,
            },
            state_handle: StateHandler::new(&id),
            policy: TurretPolicy::Ready,
            pos: pos,
            delayer_fire: Delayer::new(config.turret_fire_delay),
        }
    }

    /// Return complete current turret state
    pub fn get_complete_state(&self) -> TurretState {
        TurretState {
            id: self.id,
            death: None,
            coord: Some(self.pos.clone()),
            shot_id: None,
        }
    }

    /// Return turret death state
    pub fn die(&self, death_cause: TurretDeathCause) -> TurretState {
        let mut state = TurretState::new(&self.id);
        state.death = Some(death_cause);
        state
    }

    /// Set the fire delay
    pub fn set_fire_delay(&mut self, delay: f64) {
        self.delayer_fire.set_delay(delay);
    }

    /// Return the turret scope, taking tech into account
    fn get_scope(&self, player: &Player) -> f64 {
        if player.has_tech(&Techs::TURRET_SCOPE) {
            return self.config.turret_scope + self.config.tech_scope_increase;
        }
        self.config.turret_scope
    }

    /// Return turret income (costs)
    pub fn get_income(&self, player: &Player) -> f64 {
        if player.has_tech(&Techs::TURRET_MAINTENANCE_COSTS) {
            return -self.config.turret_maintenance_costs
                + self.config.tech_maintenance_costs_decrease;
        }
        -self.config.turret_maintenance_costs
    }

    /// Return if the given pos is in range of the turret
    fn is_in_range(&self, pos: &Point, scope: f64) -> bool {
        let origin = self.pos.as_point();
        let dx = origin.x - pos.x;
        let dy = origin.y - pos.y;
        dx * dx + dy * dy <= scope.powi(2)
    }

    /// Check for each probe of each opponent
    /// if it is in range, in that case, kill probe (update its state)
    /// and switch to Wait policy
    fn handle_fire_probe(&mut self, player: &Player, opponents: &mut Vec<&mut Player>) {
        let scope = self.get_scope(player);
        for opp in opponents {
            for probe in opp.iter_mut_probes() {
                if self.is_in_range(&probe.pos, scope) {
                    self.state_handle.get_mut().shot_id = Some(probe.id);
                    probe.inflict_damage(self.config.turret_damage);
                    self.policy = TurretPolicy::Wait;
                    return;
                }
            }
        }
    }

    /// Switch to Produce policy when having less than `max_probe`
    fn wait(&mut self, ctx: &mut FrameContext) {
        if self.delayer_fire.wait(ctx.dt) {
            self.policy = TurretPolicy::Ready;
        }
    }

    /// run function
    pub fn run(
        &mut self,
        player: &Player,
        ctx: &mut FrameContext,
        opponents: &mut Vec<&mut Player>,
    ) -> Option<TurretState> {
        log::debug!(
            "[({:.3}) Turret {:.3}] run...",
            player.id.to_string(),
            self.id.to_string()
        );

        match self.policy {
            TurretPolicy::Ready => {
                self.handle_fire_probe(player, opponents);
            }
            TurretPolicy::Wait => {
                self.wait(ctx);
            }
        }

        self.state_handle.flush(&self.id)
    }
}
