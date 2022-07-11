use log::warn;

use super::core::{self, FrameContext, Runnable};
use super::core::{Coord, Point};
use super::player::Player;
use super::{geometry, GameConfig};

#[derive(Debug)]
pub enum ProbePolicy {
    Farm,
    Attack,
    Claim,
}

#[derive(Clone)]
pub enum ProbeDeathCause {
    Exploded,
    Shot,
}

struct ProbeConfig {
    speed: f64,
    claim_delay: f64,
}

#[derive(Clone)]
pub struct ProbeState {
    /// If id is None -> the probe has just been created
    pub id: Option<u128>,
    /// Only specified once, when the probe dies
    pub death: Option<ProbeDeathCause>,
    pub pos: Option<Point>,
    pub target: Option<Coord>,
}

impl ProbeState {
    pub fn new(probe: &Probe) -> Self {
        ProbeState {
            id: Some(probe.id),
            death: None,
            pos: None,
            target: None,
        }
    }

    pub fn from_id(id: u128) -> Self {
        ProbeState {
            id: Some(id),
            death: None,
            pos: None,
            target: None,
        }
    }
}

pub struct Probe<'a> {
    pub id: u128,
    pub player: &'a Player<'a>,
    config: ProbeConfig,
    policy: ProbePolicy,
    pub pos: Point,
    /// store target as Point for optimization
    /// but target is always a coordinate
    target: Point,
    /// direction of the movement to the target
    move_dir: Point,
    /// Store potential probe state at this frame
    /// used to gradually build probe state during
    /// run() function (see mut_state)
    /// Should not be dealt with directly
    current_state: ProbeState,
    /// Indicates if a probe state was built in
    /// the current frame
    is_state: bool,
    /// Amount of time already waited during the claiming (unit: sec)
    claim_counter: f64,
}

impl<'a> Probe<'a> {
    pub fn new(player: &'a Player, config: &GameConfig, pos: Point) -> Self {
        let id = core::generate_unique_id();
        Probe {
            id: id,
            player: player,
            config: ProbeConfig {
                speed: config.probe_speed,
                claim_delay: config.probe_claim_delay,
            },
            policy: ProbePolicy::Farm,
            target: pos.clone(),
            pos: pos,
            move_dir: Point::new(0.0, 0.0),
            current_state: ProbeState::from_id(id),
            is_state: false,
            claim_counter: 0.0,
        }
    }

    pub fn get_coord(&self) -> Coord {
        self.pos.as_coord()
    }

    /// Reset current state
    /// In case is_state is true
    /// create new ProbeState instance
    fn reset_state(&mut self) {
        if self.is_state {
            self.current_state = ProbeState::from_id(self.current_state.id.unwrap());
        }
        self.is_state = false
    }

    /// Return the current state
    /// AND stores that there is a probe state
    /// (see self.is_state)
    fn mut_state(&mut self) -> &mut ProbeState {
        self.is_state = true;
        &mut self.current_state
    }

    /// Select a new target and (if found) set the new target
    /// and update the current state
    fn select_next_target(&mut self, ctx: &mut FrameContext) {
        let target;
        match &self.policy {
            ProbePolicy::Farm => {
                target = ctx.map.get_probe_farm_target(self.player, &self);
            }
            ProbePolicy::Attack => {
                target = ctx.map.get_probe_attack_target(self.player, &self);
            }
            _ => {
                warn!("Unexpected probe policy: {:?}", self.policy);
                return;
            }
        };
        if let Some(target) = target {
            let target = target.as_point();
            // in case the target has changed -> update current state
            if target != self.target {
                self.mut_state().target = Some(target.as_coord());
            }
            self.set_target(target);
        }
    }

    /// Set a new target,
    /// Compute new move direction
    fn set_target(&mut self, target: Point) {
        self.target = target;
        self.move_dir =
            Point::new(self.target.x - self.pos.x, self.target.y - self.pos.y).normalize();
        self.move_dir.mul(self.config.speed);
    }

    /// Return if the current position is sufficiently close to the target
    /// to be considered equals
    fn is_target_reached(&self, ctx: &mut FrameContext) -> bool {
        let dx = self.target.x - self.pos.x;
        let dy = self.target.y - self.pos.y;
        let threshold = 1.1 * ctx.dt * self.config.speed;
        (dx * dx + dy * dy) < threshold * threshold
    }

    /// Update current position: move to target
    fn update_pos(&mut self, ctx: &mut FrameContext) {
        self.pos.x += self.move_dir.x * ctx.dt;
        self.pos.y += self.move_dir.y * ctx.dt;
    }

    /// Claim the tile at the current pos
    /// Switch to Claim policy
    fn claim(&mut self, ctx: &mut FrameContext) {
        ctx.map.claim_tile(self.player, &self.get_coord());
        self.claim_counter = 0.0;
        self.policy = ProbePolicy::Claim;
    }

    /// Claims neighbours tiles twice \
    /// Notify death in probe state
    fn explode(&mut self, ctx: &mut FrameContext) {
        self.mut_state().death = Some(ProbeDeathCause::Exploded);
        let coords = geometry::square(&self.get_coord(), 1);
        for coord in coords.iter() {
            ctx.map.claim_tile(self.player, coord);
            ctx.map.claim_tile(self.player, coord);
        }
    }

    /// Wait for `claim_delay` then switch to Farm policy
    fn wait_claim(&mut self, ctx: &mut FrameContext) {
        self.claim_counter += ctx.dt;
        if self.claim_counter >= self.config.claim_delay {
            self.policy = ProbePolicy::Farm;
            self.select_next_target(ctx);
        }
    }
}

impl<'a> Runnable for Probe<'a> {
    type State = ProbeState;

    fn run(&mut self, ctx: &mut FrameContext) -> Option<Self::State> {
        match self.policy {
            ProbePolicy::Farm => {
                self.update_pos(ctx);
                if self.is_target_reached(ctx) {
                    self.claim(ctx);
                }
            }
            ProbePolicy::Attack => {
                self.update_pos(ctx);
                if self.is_target_reached(ctx) {
                    self.explode(ctx);
                }
            }
            ProbePolicy::Claim => {
                self.wait_claim(ctx);
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
