use log;

use super::core::{Coord, FrameContext};
use super::player::Player;
use super::probe::{Probe, ProbeDeathCause, ProbeState};
use super::{core, geometry, Delayer, GameConfig};

pub enum FactoryPolicy {
    Expand,
    Produce,
    Wait,
}

#[derive(Clone, Debug)]
pub enum FactoryDeathCause {
    Conquered,
}

struct FactoryConfig {
    max_probe: u32,
    build_probe_delay: f64,
    probe_maintenance_costs: f64,
}

#[derive(Clone, Debug)]
pub struct FactoryState {
    pub id: u128,
    /// Only specified once, when the factory dies
    pub death: Option<FactoryDeathCause>,
    pub coord: Option<Coord>,
    pub probes: Vec<ProbeState>,
}

impl FactoryState {
    pub fn from_id(id: u128) -> Self {
        FactoryState {
            id: id,
            death: None,
            coord: None,
            probes: Vec::new(),
        }
    }
}

pub struct Factory {
    pub id: u128,
    config: FactoryConfig,
    policy: FactoryPolicy,
    pub pos: Coord,
    probes: Vec<Probe>,
    /// step in the expansion phase
    expand_step: u32,
    /// Delay to wait to produce probe
    delayer_produce: Delayer,
    /// Delay to wait between expand step
    delayer_expand: Delayer,
    /// Store potential factory state at this frame
    /// used to gradually build factory state during
    /// run() function
    /// Should not be dealt with directly
    current_state: FactoryState,
    /// Indicates if a factory state was built in
    /// the current frame
    is_state: bool,
}

impl Factory {
    pub fn new(config: &GameConfig, pos: Coord) -> Self {
        let id = core::generate_unique_id();
        Factory {
            id: id,
            config: FactoryConfig {
                max_probe: config.factory_max_probe,
                build_probe_delay: config.factory_build_probe_delay,
                probe_maintenance_costs: config.probe_maintenance_costs,
            },
            policy: FactoryPolicy::Expand,
            pos: pos,
            probes: Vec::new(),
            expand_step: 0,
            delayer_produce: Delayer::new(config.factory_build_probe_delay),
            delayer_expand: Delayer::new(0.5),
            current_state: FactoryState::from_id(id),
            is_state: false,
        }
    }

    /// factory policy getter
    pub fn get_policy(&self) -> &FactoryPolicy {
        &self.policy
    }

    /// Return current state \
    /// In case is_state is true,
    /// reset current state and create new FactoryState instance
    pub fn flush_state(&mut self) -> Option<FactoryState> {
        if !self.is_state {
            return None;
        }
        let state = self.current_state.clone();
        self.current_state = FactoryState::from_id(self.id);
        self.is_state = false;
        Some(state)
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

    /// Create the probe state of a new probe
    fn create_probe_state(&self) -> ProbeState {
        ProbeState {
            id: None,
            death: None,
            pos: Some(self.pos.as_point()),
            target: None,
        }
    }

    /// Return factory income (costs)
    pub fn get_income(&self) -> f64 {
        -(self.probes.len() as f64) * self.config.probe_maintenance_costs
    }

    /// Kill all factory's probes \
    /// Return their states (with death cause)
    pub fn die(&mut self) -> Vec<ProbeState> {
        let mut probe_states = Vec::with_capacity(self.probes.len());
        for probe in self.probes.iter_mut() {
            let mut state = ProbeState::from_id(probe.id);
            state.death = Some(ProbeDeathCause::Scrapped);
            probe_states.push(state);
        }
        probe_states
    }

    /// Claim tiles next to the factory
    /// When done, switch to Produce policy
    fn expand(&mut self, player: &Player, ctx: &mut FrameContext) {
        if !self.delayer_expand.wait(ctx) {
            return;
        }
        self.expand_step += 1;
        if self.expand_step == 4 {
            self.expand_step = 0;
            self.policy = FactoryPolicy::Wait;
            return;
        }
        let coords = geometry::square(&self.pos, self.expand_step);
        for coord in coords.iter() {
            ctx.map.claim_tile(player, coord);
        }
    }

    /// Wait for produce delay then produce a new probe
    /// (by putting it in `current_state`), then repeat. \
    /// Note: doesn't check for player money, will be done by player
    /// when resolving states (thus there is no guarantee that the probe
    /// will effectively be created) \
    /// Switch to Wait policy when `max_probe` reached
    fn produce(&mut self, ctx: &mut FrameContext) {
        if self.probes.len() == self.config.max_probe as usize {
            self.policy = FactoryPolicy::Wait;
            return;
        }
        if self.delayer_produce.wait(ctx) {
            self.current_state.probes.push(self.create_probe_state());
            self.is_state = true;
        }
    }

    /// Switch to Produce policy when having less than `max_probe`
    fn wait(&mut self, ctx: &mut FrameContext) {
        // if self.probes.len() < self.config.max_probe as usize {
        //     self.policy = FactoryPolicy::Produce;
        // }
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
                self.expand(player, ctx);
            }
            FactoryPolicy::Produce => {
                self.produce(ctx);
            }
            FactoryPolicy::Wait => {
                self.wait(ctx);
            }
        }

        let mut dead_probe_idxs = Vec::new();
        for (i, probe) in self.probes.iter_mut().enumerate() {
            if let Some(state) = probe.run(player, ctx) {
                // remove death probes (for any death cause)
                if state.death.is_some() {
                    dead_probe_idxs.push(i);
                }

                self.current_state.probes.push(state);
                self.is_state = true;
            }
        }

        // remove all death probes (note: in REVERSE order)
        for idx in dead_probe_idxs.iter().rev() {
            self.probes.remove(*idx);
        }

        self.flush_state()
    }
}
