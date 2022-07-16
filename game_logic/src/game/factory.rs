use std::rc::{Rc, Weak};

use super::core::{Coord, FrameContext, Runnable};
use super::player::Player;
use super::probe::{Probe, ProbeState};
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
    pub player: Weak<Player>,
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
    pub fn new(player: &Rc<Player>, config: &GameConfig, pos: Coord) -> Self {
        let id = core::generate_unique_id();
        Factory {
            id: id,
            player: Rc::downgrade(player),
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

    fn rc_player(&self) -> Rc<Player> {
        self.player.upgrade().unwrap()
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

    /// Claim tiles next to the factory
    /// When done, switch to Produce policy
    fn expand(&mut self, ctx: &mut FrameContext) {
        self.expand_step += 1;
        if self.expand_step == 4 {
            self.expand_step = 0;
            self.policy = FactoryPolicy::Produce;
            return;
        }
        let coords = geometry::square(&self.pos, self.expand_step);
        for coord in coords.iter() {
            ctx.map.claim_tile(self.rc_player().as_ref(), coord);
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
}

impl Runnable for Factory {
    type State = FactoryState;

    fn run(&mut self, ctx: &mut FrameContext) -> Option<Self::State> {
        match self.policy {
            FactoryPolicy::Expand => {
                self.expand(ctx);
            }
            FactoryPolicy::Produce => {
                self.produce(ctx);
            }
            FactoryPolicy::Wait => {
                self.wait(ctx);
            }
        }

        for probe in self.probes.iter_mut() {
            if let Some(state) = probe.run(ctx) {
                // manual call to mut_state() cause of borrowing-stuff
                self.current_state.probes.push(state);
                self.is_state = true;
            }
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
