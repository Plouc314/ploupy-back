/**
 * Schemas of the firebase realtime database
 */

/**
 * User's unique id, generated by the auth service
 */
type UID = string
/**
 * Id generated by the db service
 */
type ID = string

/**
 * Date and time, formatted as ISO 8601
 */
type DateTime = string

type int = number
type float = number

/**
 * Overall schema of the entire database
 * 
 * @path /
 */
type DB = {
    config: Config
    users: Record<UID, User>
    stats: Record<UID, UserStats>
}

/**
 * Global configurations
 * 
 * @path /config
 */
type Config = {
    /**
     * Game modes
     */
    modes: Record<ID, GameMode>
}

/**
 * @path /config/modes/{id}
 */
type GameMode = {
    name: string
    config: GameConfig
}

/**
 * @path /users/{uid}
 */
type User = {
    username: string
    email: string
    avatar: string
    joined_on: DateTime
    last_online: DateTime
}

/**
 * Collection of statistics for all game modes
 * where the user played in
 * 
 * @path /stats/{uid}
 */
type UserStats = {
    /**
     * Current user MMR
     * ID: Config.modes.ID
     */
    mmrs: Record<ID, int>
    /**
     * History of the games per game mode
     * ID: Config.modes.ID
     */
    history: Record<ID, GameHistory>
}


/**
 * Collection of all played games statistics
 * indexed by datetime (for one game mode)
 * 
 * @path /stats/{uid}/history/{id}
 */
type GameHistory = Record<DateTime, GameStats>


/**
 * Statistics for one game
 * 
 * @path /stats/{uid}/history/{id}/{datetime}
 */
type GameStats = {
    /**
     * MMR of the user AFTER the game
     */
    mmr: int
    /**
     * List of UIDs of the player in the game (including self)
     * sorted by resulting position, i.e. best (index 0) to worst
     */
    ranking: UID[]
}

/**
 * Global configuration of the game
 * 
 * @path /config/modes/{id}/config
 */
type GameConfig = {
    /** 
     * dimension of the map (unit: coord)
     */
    dim: { x: int, y: int }
    /**
     * number of players in the game
     */
    n_player: int
    /**
     * money players start with
     */
    initial_money: int
    /** 
     * initial number of probes to start with (must be smaller
     * than `factory_max_probe`) 
     */
    initial_n_probes: int
    /**
     * base income that each player receive unconditionally
     */
    base_income: float
    /**
     * minimal occupation value on tile required to build a building (factory/turret)
     */
    building_occupation_min: int
    /**
     * amount to pay to build a new factory
     */
    factory_price: int
    /**
     * maximal number of probe generated by a factory
     */
    factory_max_probe: int
    /**
     * delay to wait to build a probe from the factory (sec)
     */
    factory_build_probe_delay: float
    /**
     * maximal occupation value that can be reached
     */
    max_occupation: int
    /**
     * speed of the probe in coordinate/sec
     */
    probe_speed: float
    /**
     * amount to pay to produce one probe
     */
    probe_price: int
    /**
     * delay to wait claim a tile, the probe can be manually moved but not claim
     * another tile during the delay (see Probe `is_claiming` flag for details)
     */
    probe_claim_delay: float
    /**
     * Costs of possessing one probe (computed in the player's income)
     */
    probe_maintenance_costs: float
    /**
     * amount to pay to build a new turret
     */
    turret_price: int
    /**
     * delay to wait for the turret between two fires (sec)
     */
    turret_fire_delay: float
    /**
     * scope of the turret (unit| coord)
     */
    turret_scope: float
    /**
     * Costs of possessing one turret (computed in the player's income)
     */
    turret_maintenance_costs: float
    /**
     * factor of how the occupation level of a tile reflects on its income,
     * as `income = occupation * rate`
     */
    income_rate: float
    /**
     * probability that a tile with maximum occupation lose 1 occupation
     */
    deprecate_rate: float
}