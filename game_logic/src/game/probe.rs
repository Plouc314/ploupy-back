use super::core::{self, FrameContext};
use super::core::{Coord, Point};
use super::player::Player;
use super::{
    geometry, Delayer, GameConfig, Identifiable, Map, State, StateHandler, Techs, NOT_IDENTIFIABLE,
};

#[derive(Clone, Debug)]
pub enum ProbePolicy {
    Farm,
    Attack,
    Claim,
}

#[derive(Clone, Debug)]
pub enum ProbeDeathCause {
    Exploded,
    Shot,
    Scrapped,
}

struct ProbeConfig {
    speed: f64,
    claim_delay: f64,
    claim_intensity: u32,
    explosion_intensity: u32,
    tech_explosion_intensity_increase: u32,
    tech_claim_intensity_increase: u32,
}

#[derive(Clone, Debug)]
pub struct ProbeState {
    pub id: u128,
    pub death: Option<ProbeDeathCause>,
    pub pos: Option<Point>,
    pub target: Option<Coord>,
    pub policy: Option<ProbePolicy>,
    /// Specify that the probe should be created
    /// Internal to rust implementation
    just_created: bool,
}

impl Identifiable for ProbeState {
    fn id(&self) -> u128 {
        self.id
    }
}

impl State for ProbeState {
    type Metadata = u128;

    fn new(_metadata: &Self::Metadata) -> Self {
        ProbeState {
            id: *_metadata,
            death: None,
            pos: None,
            target: None,
            policy: None,
            just_created: false,
        }
    }

    fn merge(&mut self, state: Self) {
        if let Some(death) = state.death {
            self.death = Some(death);
        }
        if let Some(pos) = state.pos {
            self.pos = Some(pos);
        }
        if let Some(target) = state.target {
            self.target = Some(target);
        }
    }
}

impl ProbeState {
    /// Return if the probe has just been created
    /// (without id)
    pub fn just_created(&self) -> bool {
        self.just_created
    }

    /// Create the probe state of a new probe,
    /// i.e.: with only a position
    pub fn create_created_state(pos: Point) -> Self {
        ProbeState {
            id: NOT_IDENTIFIABLE,
            death: None,
            pos: Some(pos),
            target: None,
            policy: Some(ProbePolicy::Farm),
            just_created: true,
        }
    }
}

pub struct Probe {
    pub id: u128,
    config: ProbeConfig,
    state_handle: StateHandler<ProbeState>,
    policy: ProbePolicy,
    pub pos: Point,
    hp: u32,
    /// store target as Point for optimization
    /// but target is always a coordinate
    target: Point,
    /// direction of the movement to the target
    move_dir: Point,
    /// Delay to wait to reach target
    delayer_travel: Delayer,
    /// Delay to wait in order to claim a tile
    delayer_claim: Delayer,
}

impl Probe {
    /// Create a new Probe instance \
    /// By default, the target is the same as the position (`pos`)
    /// use, `set_target()` to specify a target, else it will be set
    /// on next frame
    pub fn new(config: &GameConfig, player: &Player, pos: Point) -> Probe {
        let id = core::generate_unique_id();

        let mut hp = config.probe_hp;
        if player.has_tech(&Techs::PROBE_HP) {
            hp += config.tech_probe_hp_increase;
        }

        Probe {
            id: id,
            config: ProbeConfig {
                speed: config.probe_speed,
                claim_delay: config.probe_claim_delay,
                claim_intensity: config.probe_claim_intensity,
                explosion_intensity: config.probe_explosion_intensity,
                tech_explosion_intensity_increase: config.tech_probe_explosion_intensity_increase,
                tech_claim_intensity_increase: config.tech_probe_claim_intensity_increase,
            },
            state_handle: StateHandler::new(&id),
            policy: ProbePolicy::Farm,
            hp: hp,
            target: pos.clone(),
            pos: pos,
            move_dir: Point::new(0.0, 0.0),
            delayer_travel: Delayer::new(0.0),
            delayer_claim: Delayer::new(config.probe_claim_delay),
        }
    }

    pub fn get_coord(&self) -> Coord {
        self.pos.as_coord()
    }

    /// Return complete current probe state
    pub fn get_complete_state(&self) -> ProbeState {
        ProbeState {
            id: self.id,
            death: None,
            pos: Some(self.pos.clone()),
            target: Some(self.target.as_coord()),
            policy: Some(self.policy.clone()),
            just_created: false,
        }
    }

    /// Inflict damage (reduce probe's hp) \
    /// In case, the probe has no hp left: update state with death cause
    pub fn inflict_damage(&mut self, damage: u32) {
        if damage >= self.hp {
            self.hp = 0;
            self.state_handle.get_mut().death = Some(ProbeDeathCause::Shot);
        } else {
            self.hp -= damage;
        }
    }

    /// Select a new target and (if found) set the new target
    /// (see `set_target_mannually` for details), update state
    fn select_farm_target(&mut self, player: &Player, map: &mut Map) {
        let target = match map.get_probe_farm_target(player, &self) {
            Some(target) => target,
            None => {
                return;
            }
        };
        let target = target.as_point();
        // in case the target has changed -> update current state
        if target != self.target {
            self.state_handle.get_mut().target = Some(target.as_coord());
        }
        self.set_target_manually(target);
    }

    /// Select a new target and (if found) set the new target
    /// (see `set_target_mannually` for details), update state
    fn select_attack_target(&mut self, player_id: u128, map: &mut Map) {
        let target = match map.get_probe_attack_target(player_id, &self) {
            Some(target) => target,
            None => {
                log::warn!(
                    "[({:.3}) probe {:.3}] No target found.",
                    player_id.to_string(),
                    self.id.to_string(),
                );
                return;
            }
        };
        let target = target.as_point();
        self.state_handle.get_mut().target = Some(target.as_coord());
        self.set_target_manually(target);
    }

    /// Set a new target \
    /// Compute new move direction and reset travel delayer \
    /// Note: do not update current state or probe's policy
    /// (see `set_farm_target` or `set_attack_target`).
    pub fn set_target_manually(&mut self, target: Point) {
        self.target = target;
        self.move_dir = Point::new(self.target.x - self.pos.x, self.target.y - self.pos.y);
        self.delayer_travel
            .set_delay(self.move_dir.norm() / self.config.speed);
        self.delayer_travel.reset();
        self.move_dir.normalize();
        self.move_dir.mul(self.config.speed);
    }

    /// Set a new farm target \
    /// Update current state, move direction, travel delayer, policy
    pub fn set_farm_target(&mut self, target: Point) {
        self.state_handle.get_mut().pos = Some(self.pos.clone());
        self.state_handle.get_mut().target = Some(target.as_coord());
        self.state_handle.get_mut().policy = Some(ProbePolicy::Farm);
        self.policy = ProbePolicy::Farm;
        self.set_target_manually(target);
    }

    /// Set a new attack target \
    /// Update current state, move direction, travel delayer, policy
    pub fn set_attack(&mut self, player_id: u128, map: &mut Map) {
        self.state_handle.get_mut().pos = Some(self.pos.clone());
        self.state_handle.get_mut().policy = Some(ProbePolicy::Attack);
        self.policy = ProbePolicy::Attack;
        self.select_attack_target(player_id, map);
    }

    /// Return if the current position is sufficiently close to the target
    /// to be considered equals
    fn is_target_reached(&mut self, ctx: &mut FrameContext) -> bool {
        self.delayer_travel.wait(ctx.dt)
    }

    /// Update current position: move to target
    fn update_pos(&mut self, ctx: &mut FrameContext) {
        self.pos.x += self.move_dir.x * ctx.dt;
        self.pos.y += self.move_dir.y * ctx.dt;
    }

    /// Claims neighbours tiles twice \
    /// Notify death in probe state
    pub fn explode(&mut self, player_id: u128, map: &mut Map, tech_explosion_intensity: bool) {
        self.state_handle.get_mut().death = Some(ProbeDeathCause::Exploded);
        let coords = geometry::square(&self.get_coord(), 1);
        for coord in coords.iter() {
            // make sure to explode on opponent tile
            match map.get_tile(coord) {
                None => {
                    continue;
                }
                Some(tile) => {
                    if !tile.is_owned_by_opponent_of(player_id) {
                        continue;
                    }
                }
            };
            let mut intensity = self.config.explosion_intensity;
            if tech_explosion_intensity {
                intensity += self.config.tech_explosion_intensity_increase;
            }
            map.claim_tile(player_id, coord, intensity);
        }
    }

    fn attack(&mut self, player: &Player, ctx: &mut FrameContext) {
        let coord = self.target.as_coord();
        if ctx
            .map
            .get_tile(&coord)
            .unwrap()
            .is_owned_by_opponent_of(player.id)
        {
            self.explode(
                player.id,
                ctx.map,
                player.has_tech(&Techs::PROBE_EXPLOSION_INTENSITY),
            );
        } else {
            self.pos = self.target.clone();
            self.state_handle.get_mut().pos = Some(self.target.clone());
            self.select_attack_target(player.id, ctx.map);
        }
    }

    /// Wait for `claim_delay` then claim the tile
    /// at the current pos, switch to Farm policy
    fn claim(&mut self, player: &Player, ctx: &mut FrameContext) {
        if self.delayer_claim.wait(ctx.dt) {
            self.policy = ProbePolicy::Farm;

            let mut intensity = self.config.claim_intensity;
            if player.has_tech(&Techs::PROBE_CLAIM_INTENSITY) {
                intensity += self.config.tech_claim_intensity_increase;
            }

            ctx.map.claim_tile(player.id, &self.get_coord(), intensity);
            self.select_farm_target(player, ctx.map);
        }
    }

    /// run function
    pub fn run(&mut self, player: &Player, ctx: &mut FrameContext) -> Option<ProbeState> {
        log::debug!(
            "[({:.3}) probe {:.3}] run... ({:?})",
            player.id.to_string(),
            self.id.to_string(),
            &self.policy
        );
        match self.policy {
            ProbePolicy::Farm => {
                self.update_pos(ctx);
                if self.is_target_reached(ctx) {
                    self.policy = ProbePolicy::Claim;
                    self.pos = self.target.clone();
                    self.state_handle.get_mut().pos = Some(self.target.clone());
                }
            }
            ProbePolicy::Attack => {
                self.update_pos(ctx);
                if self.is_target_reached(ctx) {
                    self.attack(player, ctx);
                }
            }
            ProbePolicy::Claim => {
                self.claim(player, ctx);
            }
        }

        self.state_handle.flush(&self.id)
    }
}
