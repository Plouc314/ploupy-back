mod core;
mod factory;
mod game;
mod geometry;
mod map;
mod player;
mod probe;
mod random;
mod turret;

pub use self::core::*;
pub use self::factory::*;
pub use self::game::*;
pub use self::geometry::*;
pub use self::map::*;
pub use self::player::*;
pub use self::probe::*;
pub use self::turret::*;

pub struct GameConfig {
    /// dimension of the map (unit: coord),
    pub dim: Coord,

    /// number of players in the game
    pub n_player: u32,

    /// money players start with
    pub initial_money: f64,

    /// initial number of probes to start with (must be smaller
    /// than `factory_max_probe`)
    pub initial_n_probes: u32,

    /// base income that each player receive unconditionally
    pub base_income: f64,

    /// minimal occupation value on tile required to build a building (factory/turret)
    pub building_occupation_min: u32,

    /// amount to pay to build a new factory
    pub factory_price: f64,

    /// maximal number of probe generated by a factory
    pub factory_max_probe: u32,

    /// delay to wait to build a probe from the factory (sec)
    pub factory_build_probe_delay: f64,

    /// maximal occupation value that can be reached
    pub max_occupation: u32,

    /// speed of the probe in coordinate/sec
    pub probe_speed: f64,

    // probe hitpoints
    pub probe_hp: u32,

    /// intensity of claiming when farming
    pub probe_claim_intensity: u32,

    /// intensity of claiming when exploding
    pub probe_explosion_intensity: u32,

    /// amount to pay to produce one probe
    pub probe_price: f64,

    /// delay to wait claim a tile, the probe can be manually moved but not claim
    /// another tile during the delay (see Probe `is_claiming` flag for details)
    pub probe_claim_delay: f64,

    /// Costs of possessing one probe (computed in the player's income)
    pub probe_maintenance_costs: f64,

    /// amount to pay to build a new turret
    pub turret_price: f64,

    /// amount of damage inflicted to probe's hp
    pub turret_damage: u32,

    /// delay to wait for the turret between two fires (sec)
    pub turret_fire_delay: f64,

    /// scope of the turret (unit: coord)
    pub turret_scope: f64,

    /// Costs of possessing one turret (computed in the player's income)
    pub turret_maintenance_costs: f64,

    /// factor of how the occupation level of a tile reflects on its income,
    /// as `income = occupation * rate`
    pub income_rate: f64,

    /// probability that a tile with maximum occupation lose 2 occupation
    pub deprecate_rate: f64,

    /// how much the probe explosion intensity of claiming
    /// is increased
    pub tech_probe_explosion_intensity_increase: u32,

    /// price of probe explosion intensity tech
    pub tech_probe_explosion_intensity_price: f64,

    /// how much the probe claim intensity is increased (farming)
    pub tech_probe_claim_intensity_increase: u32,

    /// price of probe claim intensity tech
    pub tech_probe_claim_intensity_price: f64,

    /// how much the probe hp are increased (turret fire)
    pub tech_probe_hp_increase: u32,

    /// price of probe hp tech
    pub tech_probe_hp_price: f64,

    /// how much the build probe delay is decreased
    pub tech_factory_build_delay_decrease: f64,

    /// price of factory build delay tech
    pub tech_factory_build_delay_price: f64,

    /// how much the probe price is decreased
    pub tech_factory_probe_price_decrease: f64,

    /// price of factory probe price tech
    pub tech_factory_probe_price_price: f64,

    /// how much the factory max probe is decreased
    pub tech_factory_max_probe_increase: u32,

    /// price of factory max probe tech
    pub tech_factory_max_probe_price: f64,

    /// how much the turret scope is increased
    pub tech_turret_scope_increase: f64,

    /// price of turret scope tech
    pub tech_turret_scope_price: f64,

    /// how much the turret fire delay is decreased
    pub tech_turret_fire_delay_decrease: f64,

    /// price of turret fire delay tech
    pub tech_turret_fire_delay_price: f64,

    /// how much the turret maintenance costs are decreased
    pub tech_turret_maintenance_costs_decrease: f64,

    /// price of turret maintenance costs tech
    pub tech_turret_maintenance_costs_price: f64,
}
