use super::core::{Coord, FrameContext, Identifiable, Runnable};
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
    probe_price: u32,
    probe_maintenance_costs: f64,
}

#[derive(Clone)]
pub struct FactoryState {
    pub id: String,
    /// Only specified once, when the factory dies
    pub death: Option<FactoryDeathCause>,
    pub coord: Option<Coord>,
    pub probes: Vec<ProbeState>,
}

impl FactoryState {
    pub fn new(factory: &Factory) -> Self {
        FactoryState {
            id: factory.get_id().to_string(),
            death: None,
            coord: None,
            probes: Vec::new(),
        }
    }

    pub fn from_id(id: String) -> Self {
        FactoryState {
            id: id,
            death: None,
            coord: None,
            probes: Vec::new(),
        }
    }
}

pub struct Factory<'a> {
    id: String,
    pub player: &'a Player<'a>,
    config: FactoryConfig,
    policy: FactoryPolicy,
    pub pos: Coord,
    probes: Vec<Probe<'a>>,
    /// step in the expansion phase
    expand_step: u32,
    /// Store potential factory state at this frame
    /// used to gradually build factory state during
    /// run() function (see get_state)
    /// Should not be dealt with directly
    current_state: FactoryState,
    /// Indicates if a factory state was built in
    /// the current frame
    is_state: bool,
}

impl<'a> Factory<'a> {
    pub fn new(player: &'a Player, config: &GameConfig, pos: Coord) -> Self {
        let id = core::generate_unique_id();
        Factory {
            id: id.clone(),
            player: player,
            config: FactoryConfig {
                max_probe: config.factory_max_probe,
                build_probe_delay: config.factory_build_probe_delay,
                probe_price: config.probe_price,
                probe_maintenance_costs: config.probe_maintenance_costs,
            },
            policy: FactoryPolicy::Expand,
            pos: pos,
            probes: Vec::new(),
            expand_step: 0,
            current_state: FactoryState::from_id(id),
            is_state: false,
        }
    }

    /// Reset current state
    /// In case is_state is true
    /// create new FactoryState instance
    fn reset_state(&mut self) {
        if self.is_state {
            self.current_state = FactoryState::from_id(self.current_state.id.clone());
        }
        self.is_state = false
    }

    /// Return the current state
    /// AND stores that there is a factory state
    /// (see self.is_state)
    fn get_state(&mut self) -> &mut FactoryState {
        self.is_state = true;
        &mut self.current_state
    }

    /// Claim tiles next to the factory
    /// When done, switch to Produce policy
    fn expand(&mut self, ctx: &mut FrameContext) {
        self.expand_step += 1;
        if self.expand_step == 4 {
            self.expand_step = 0;
            self.policy = FactoryPolicy::Produce;
        }
        let coords = geometry::square(&self.pos, self.expand_step);
        for coord in coords.iter() {
            ctx.map.claim_tile(self.player, coord);
        }
    }
}

impl<'a> Runnable for Factory<'a> {
    type State = FactoryState;

    fn run(&mut self, ctx: &mut FrameContext) -> Option<Self::State> {
        match self.policy {
            FactoryPolicy::Expand => {
                self.expand(ctx);
            }
            FactoryPolicy::Produce => {}
            FactoryPolicy::Wait => {}
        }

        for probe in self.probes.iter_mut() {
            if let Some(state) = probe.run(ctx) {
                // manual call to get_state() cause of borrowing-stuff
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

impl Identifiable for Factory<'_> {
    fn get_id(&self) -> &str {
        &self.id
    }
}
