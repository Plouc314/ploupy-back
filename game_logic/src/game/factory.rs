use std::slice::IterMut;

use log;

use super::core::{state_vec_insert, Coord, FrameContext, State};
use super::player::Player;
use super::probe::{Probe, ProbeDeathCause, ProbeState};
use super::{core, geometry, Delayer, GameConfig, Identifiable, StateHandler, Techs};

pub enum FactoryPolicy {
    Expand,
    Produce,
    Wait,
}

#[derive(Clone, Debug)]
pub enum FactoryDeathCause {
    Conquered,
    Scrapped,
}

struct FactoryConfig {
    max_probe: u32,
    expansion_size: u32,
    maintenance_costs: f64,
    probe_maintenance_costs: f64,
    tech_max_probe_increase: u32,
}

#[derive(Clone, Debug)]
pub struct FactoryState {
    pub id: u128,
    /// Only specified once, when the factory dies
    pub death: Option<FactoryDeathCause>,
    pub coord: Option<Coord>,
    pub probes: Vec<ProbeState>,
}

impl Identifiable for FactoryState {
    fn id(&self) -> u128 {
        self.id
    }
}

impl State for FactoryState {
    type Metadata = u128;

    fn new(_metadata: &Self::Metadata) -> Self {
        FactoryState {
            id: *_metadata,
            death: None,
            coord: None,
            probes: Vec::new(),
        }
    }

    fn merge(&mut self, state: Self) {
        if let Some(death) = state.death {
            self.death = Some(death);
        }
        if let Some(coord) = state.coord {
            self.coord = Some(coord);
        }
        for probe in state.probes {
            state_vec_insert(&mut self.probes, probe);
        }
    }
}

pub struct Factory {
    pub id: u128,
    config: FactoryConfig,
    state_handle: StateHandler<FactoryState>,
    policy: FactoryPolicy,
    pub pos: Coord,
    probes: Vec<Probe>,
    /// step in the expansion phase
    expand_step: u32,
    /// Delay to wait to produce probe
    delayer_produce: Delayer,
    /// Delay to wait between expand step
    delayer_expand: Delayer,
}

impl Factory {
    pub fn new(config: &GameConfig, pos: Coord) -> Self {
        let id = core::generate_unique_id();
        Factory {
            id: id,
            config: FactoryConfig {
                max_probe: config.factory_max_probe,
                expansion_size: config.factory_expansion_size,
                maintenance_costs: config.factory_maintenance_costs,
                probe_maintenance_costs: config.probe_maintenance_costs,
                tech_max_probe_increase: config.tech_factory_max_probe_increase,
            },
            state_handle: StateHandler::new(&id),
            policy: FactoryPolicy::Expand,
            pos: pos,
            probes: Vec::new(),
            expand_step: 0,
            delayer_produce: Delayer::new(config.factory_build_probe_delay),
            delayer_expand: Delayer::new(0.5),
        }
    }

    /// factory policy getter
    pub fn get_policy(&self) -> &FactoryPolicy {
        &self.policy
    }

    /// Return complete current factory state
    pub fn get_complete_state(&self) -> FactoryState {
        let mut state = FactoryState {
            id: self.id,
            death: None,
            coord: Some(self.pos.clone()),
            probes: Vec::with_capacity(self.probes.len()),
        };
        for probe in self.probes.iter() {
            state.probes.push(probe.get_complete_state());
        }
        state
    }

    /// Attach a new probe to the factory
    pub fn attach_probe(&mut self, probe: Probe) {
        self.probes.push(probe);
    }

    /// Set the build probe delay
    pub fn set_build_probe_delay(&mut self, delay: f64) {
        self.delayer_produce.set_delay(delay);
    }

    /// Return the number of probes currently attached to the factory
    pub fn get_num_probes(&self) -> usize {
        self.probes.len()
    }

    /// Iterator over each probe of factory
    pub fn iter_mut_probes(&mut self) -> IterMut<Probe> {
        self.probes.iter_mut()
    }

    /// Return the probe with the given id, if it exists
    pub fn get_mut_probe_by_id(&mut self, probe_id: u128) -> Option<&mut Probe> {
        self.probes.iter_mut().find(|p| p.id == probe_id)
    }

    /// Create the probe state of a new probe
    fn create_probe_state(&self) -> ProbeState {
        ProbeState::create_created_state(self.pos.as_point())
    }

    /// Return factory income (costs)
    pub fn get_income(&self) -> f64 {
        -(self.probes.len() as f64) * self.config.probe_maintenance_costs
            - self.config.maintenance_costs
    }

    /// Return the maximum number of probe the factory can have,
    /// taking tech into account
    fn get_max_probe(&self, player: &Player) -> u32 {
        if player.has_tech(&Techs::FACTORY_MAX_PROBE) {
            return self.config.max_probe + self.config.tech_max_probe_increase;
        }
        self.config.max_probe
    }

    /// Factory dies \
    /// Kill all factory's probes \
    /// Return factory state
    pub fn die(&self, death_cause: FactoryDeathCause) -> FactoryState {
        let mut probe_states = Vec::with_capacity(self.probes.len());
        for probe in self.probes.iter() {
            let mut state = ProbeState::new(&probe.id);
            state.death = Some(ProbeDeathCause::Scrapped);
            probe_states.push(state);
        }
        let mut state = FactoryState::new(&self.id);
        state.probes = probe_states;
        state.death = Some(death_cause);
        state
    }

    /// Claim tiles next to the factory
    /// When done, switch to Produce policy
    fn expand(&mut self, player_id: u128, ctx: &mut FrameContext) {
        if !self.delayer_expand.wait(ctx.dt) {
            return;
        }
        self.expand_step += 1;
        if self.expand_step == self.config.expansion_size + 1 {
            self.expand_step = 0;
            self.policy = FactoryPolicy::Produce;
            return;
        }
        let coords = geometry::square(&self.pos, self.expand_step);
        for coord in coords.iter() {
            ctx.map.claim_tile(player_id, coord, 2);
        }
    }

    /// Wait for produce delay then produce a new probe
    /// (by putting it in `current_state`), then repeat. \
    /// Note: doesn't check for player money, will be done by player
    /// when resolving states (thus there is no guarantee that the probe
    /// will effectively be created) \
    /// Switch to Wait policy when `max_probe` reached
    fn produce(&mut self, player: &Player, ctx: &mut FrameContext) {
        if self.probes.len() == self.get_max_probe(player) as usize {
            self.policy = FactoryPolicy::Wait;
            return;
        }
        if self.delayer_produce.wait(ctx.dt) {
            let state = self.create_probe_state();
            self.state_handle.get_mut().probes.push(state);
        }
    }

    /// Switch to Produce policy when having less than `max_probe`
    fn wait(&mut self, player: &Player, ctx: &mut FrameContext) {
        if self.probes.len() < self.get_max_probe(player) as usize {
            self.policy = FactoryPolicy::Produce;
        }
    }

    /// run function
    pub fn run(&mut self, player: &Player, ctx: &mut FrameContext) -> Option<FactoryState> {
        log::debug!(
            "[({:.3}) Factory {:.3}] run...",
            player.id.to_string(),
            self.id.to_string()
        );
        match self.policy {
            FactoryPolicy::Expand => {
                self.expand(player.id, ctx);
            }
            FactoryPolicy::Produce => {
                self.produce(player, ctx);
            }
            FactoryPolicy::Wait => {
                self.wait(player, ctx);
            }
        }

        let mut dead_probe_idxs = Vec::new();
        for (i, probe) in self.probes.iter_mut().enumerate() {
            if let Some(state) = probe.run(player, ctx) {
                // remove death probes (for any death cause)
                if state.death.is_some() {
                    dead_probe_idxs.push(i);
                }

                state_vec_insert(&mut self.state_handle.get_mut().probes, state);
            }
        }

        // remove all death probes (note: in REVERSE order)
        for idx in dead_probe_idxs.iter().rev() {
            self.probes.remove(*idx);
        }

        self.state_handle.flush(&self.id)
    }
}
