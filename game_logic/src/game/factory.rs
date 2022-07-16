use std::borrow::Borrow;
use std::cell::RefCell;
use std::rc::{Rc, Weak};

use super::core::{Coord, FrameContext};
use super::player::Player;
use super::probe::{Probe, ProbeDeathCause, ProbeState};
use super::{core, geometry, GameConfig};

pub enum FactoryPolicy {
    Expand,
    Produce,
    Wait,
}

#[derive(Clone)]
pub enum FactoryDeathCause {
    Conquered,
}

struct FactoryConfig {
    max_probe: u32,
    build_probe_delay: f64,
    probe_maintenance_costs: f64,
}

#[derive(Clone)]
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
    /// Amount of time already waited when producing (unit: sec)
    produce_counter: f64,
    /// Store potential factory state at this frame
    /// used to gradually build factory state during
    /// run() function (see mut_state)
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
            produce_counter: 0.0,
            current_state: FactoryState::from_id(id),
            is_state: false,
        }
    }

    /// Reset current state
    /// In case is_state is true
    /// create new FactoryState instance
    fn reset_state(&mut self) {
        if self.is_state {
            self.current_state = FactoryState::from_id(self.id);
        }
        self.is_state = false
    }

    /// Return the current state
    /// AND stores that there is a factory state
    /// (see self.is_state)
    fn mut_state(&mut self) -> &mut FactoryState {
        self.is_state = true;
        &mut self.current_state
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
        self.expand_step += 1;
        if self.expand_step == 4 {
            self.expand_step = 0;
            self.policy = FactoryPolicy::Produce;
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
        self.produce_counter += ctx.dt;
        if self.produce_counter >= self.config.build_probe_delay {
            self.produce_counter = 0.0;
            self.current_state.probes.push(self.create_probe_state());
            self.is_state = true;
        }
    }

    /// Switch to Produce policy when having less than `max_probe`
    fn wait(&mut self, ctx: &mut FrameContext) {
        if self.probes.len() < self.config.max_probe as usize {
            self.policy = FactoryPolicy::Produce;
        }
    }

    /// run function
    pub fn run(&mut self, player: &Player, ctx: &mut FrameContext) -> Option<FactoryState> {
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

                // manual call to mut_state() cause of borrowing-stuff
                self.current_state.probes.push(state);
                self.is_state = true;
            }
        }

        // remove all death probes
        for idx in dead_probe_idxs {
            self.probes.remove(idx);
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
