use std::collections::HashMap;

use super::{
    core, core::Coord, geometry, player::Player, probe::Probe, random, state_vec_insert, Delayer,
    GameConfig, GameState, Identifiable, State, StateHandler,
};

use log;

struct MapConfig {
    pub dim: Coord,
    pub max_occupation: u32,
    pub deprecate_rate: f64,
}

#[derive(Clone, Debug)]
pub struct MapState {
    pub tiles: Vec<TileState>,
    /// store state of dead factories
    /// Internal to rust implementation
    dead_building: HashMap<u128, Vec<u128>>,
}

impl State for MapState {
    type Metadata = ();

    fn new(_metadata: &Self::Metadata) -> Self {
        MapState {
            tiles: Vec::new(),
            dead_building: HashMap::new(),
        }
    }

    fn merge(&mut self, state: Self) {
        for tile in state.tiles.iter() {
            state_vec_insert(&mut self.tiles, tile.clone());
        }

        for (owner, mut buildings) in state.dead_building {
            if let Some(ids) = self.dead_building.get_mut(&owner) {
                ids.append(&mut buildings);
            } else {
                self.dead_building.insert(owner, buildings);
            }
        }
    }
}

impl MapState {
    /// Return `dead_building` attribute
    pub fn get_dead_building(&self) -> &HashMap<u128, Vec<u128>> {
        &self.dead_building
    }
}

pub struct Map {
    config: MapConfig,
    pub state_handle: StateHandler<MapState>,
    tiles: Vec<Vec<Tile>>,
    delayer_deprecate: Delayer,
}

impl Map {
    pub fn new(config: &GameConfig) -> Self {
        let dim = config.dim.clone();
        let mut tiles: Vec<Vec<Tile>> = Vec::with_capacity((dim.x * dim.y) as usize);
        for x in 0..dim.x {
            let mut col = Vec::with_capacity(dim.y as usize);
            for y in 0..dim.y {
                let tile = Tile::new(config, Coord::new(x, y));
                col.push(tile);
            }
            tiles.push(col);
        }
        return Map {
            config: MapConfig {
                dim: dim,
                max_occupation: config.max_occupation,
                deprecate_rate: config.deprecate_rate,
            },
            state_handle: StateHandler::new(&()),
            tiles: tiles,
            delayer_deprecate: Delayer::new(1.0),
        };
    }

    /// Return a reference to tile if it exists
    pub fn get_tile(&self, coord: &Coord) -> Option<&Tile> {
        if !coord.is_positive() {
            return None;
        }
        self.tiles.get(coord.x as usize)?.get(coord.y as usize)
    }

    /// Return a mutable reference to tile if it exists
    pub fn get_mut_tile(&mut self, coord: &Coord) -> Option<&mut Tile> {
        if !coord.is_positive() {
            return None;
        }
        self.tiles
            .get_mut(coord.x as usize)?
            .get_mut(coord.y as usize)
    }

    /// Return the total occupation of all owned tiles of player
    pub fn get_player_occupation(&self, player: &Player) -> u32 {
        let mut occupation = 0;
        for col in self.tiles.iter() {
            for tile in col.iter() {
                if tile.is_owned_by(player.id) {
                    occupation += tile.occupation;
                }
            }
        }
        occupation
    }

    /// Return complete current map state
    pub fn get_complete_state(&self) -> MapState {
        let n_tiles = self.config.dim.x * self.config.dim.y;
        let mut state = MapState {
            tiles: Vec::with_capacity(n_tiles as usize),
            dead_building: HashMap::new(),
        };
        for col in self.tiles.iter() {
            for tile in col.iter() {
                state.tiles.push(tile.get_complete_state());
            }
        }
        state
    }

    /// Return the tiles that are neighbour of the `tile` \
    /// Neighbours as defined by `geometry::square_without_origin(tile.coord, distance)`
    pub fn get_neighbour_tiles(&self, tile: &Tile, distance: u32) -> Vec<&Tile> {
        let mut neighbours = Vec::new();
        let coords = geometry::square_without_origin(&tile.coord, distance);

        for coord in coords.iter() {
            let neighbour = self.get_tile(coord);
            if let Some(neighbour) = neighbour {
                neighbours.push(neighbour);
            }
        }
        return neighbours;
    }

    /// Return if the given tile can be farmed by a probe of `player`
    fn is_tile_valid_farm_target(&self, tile: &Tile, player: &Player) -> bool {
        // check if tile occupation full
        if tile.occupation == self.config.max_occupation {
            return false;
        }

        if !tile.is_owned_by(player.id) {
            // check if tile occupied by an other player
            if tile.occupation > 3 {
                return false;
            } else {
                // assert that tile is not isolated
                let neighbours = self.get_neighbour_tiles(tile, 1);
                for neighbour in neighbours.iter() {
                    if neighbour.is_owned_by(player.id) {
                        return true;
                    }
                }
                return false;
            }
        }
        return true;
    }

    /// Return a target to farm (own or unoccupied tile)
    /// in the surroundings of the probe if possible
    fn get_close_probe_farm_target(&self, player: &Player, coord: &Coord) -> Option<Coord> {
        let mut coords = geometry::square_without_origin(coord, 3);
        random::shuffle_vec(&mut coords);

        for coord in coords.iter() {
            // get tile on coord
            let tile = match self.get_tile(coord) {
                Some(v) => v,
                None => {
                    continue;
                }
            };

            if self.is_tile_valid_farm_target(tile, player) {
                return Some(tile.coord.clone());
            }
        }
        None
    }

    /// Return a target for the probe to farm (own or unoccupied tile)
    /// either in surroundings of the probe or next to a player's factory
    pub fn get_probe_farm_target(&self, player: &Player, probe: &Probe) -> Option<Coord> {
        // first look next to the probe itself
        if let Some(target) = self.get_close_probe_farm_target(player, &probe.get_coord()) {
            return Some(target);
        };

        // then look next to the factories
        for factory in player.factories.iter() {
            if let Some(target) = self.get_close_probe_farm_target(player, &factory.pos) {
                return Some(target);
            }
        }
        None
    }

    /// Return a target for the probe to attack
    pub fn get_probe_attack_target(&self, player_id: u128, probe: &Probe) -> Option<Coord> {
        let mut target_tile: Option<&Tile> = None;

        let mut idx = 0;

        for coord in geometry::iter_vortex(&probe.get_coord()) {
            if let Some(tile) = self.get_tile(&coord) {
                if tile.is_owned_by_opponent_of(player_id) {
                    target_tile = Some(tile);
                    break;
                }
            }
            idx += 1;
            if idx == 1000 {
                log::warn!("Didn't found attack target");
                return None;
            }
        }
        // choose tile in region
        let mut tiles = self.get_neighbour_tiles(&target_tile.unwrap(), 2);
        tiles.push(target_tile.unwrap());
        random::shuffle_vec(&mut tiles);
        for tile in tiles {
            if tile.is_owned_by_opponent_of(player_id) {
                return Some(tile.coord.clone());
            }
        }
        None
    }

    /// For each tile, if it meets the conditions,
    /// decrease its occupation with a certain probability.
    fn deprecate_tiles(&mut self) {
        let half = self.config.max_occupation as f64 / 2.0;
        for tile in self.tiles.iter_mut().flat_map(|c| c.iter_mut()) {
            let occ = tile.occupation as f64;
            if occ <= half {
                continue;
            }

            // compute probability
            let mut prob = (occ - half) / (self.config.max_occupation as f64 - half);
            prob *= self.config.deprecate_rate;

            if random::random() <= prob {
                tile.decr_occupation(2);

                let state = TileState::new(&tile);
                state_vec_insert(&mut self.state_handle.get_mut().tiles, state);
            }
        }
    }

    /// Claim the tile at the coordinate of the probe
    /// with the given intensity \
    /// Store the tile state, potential building death in current state \
    /// Return if it could be done
    pub fn claim_tile(&mut self, player_id: u128, coord: &Coord, intensity: u32) -> bool {
        let tile = self.get_mut_tile(coord);
        let tile = match tile {
            None => {
                return false;
            }
            Some(tile) => tile,
        };

        let mut deaths: Option<(u128, u128)> = None;
        match tile.owner_id {
            None => {
                tile.set_owner(player_id);
                tile.incr_occupation(intensity);
            }
            Some(owner_id) => {
                if owner_id == player_id {
                    tile.incr_occupation(intensity);
                } else {
                    tile.decr_occupation(intensity);
                    if tile.occupation == 0 {
                        // notify building death
                        if let Some(building_id) = tile.building_id {
                            deaths = Some((tile.owner_id.unwrap(), building_id));
                        }
                        tile.owner_id = None;
                        tile.building_id = None;
                    }
                }
            }
        }
        let state = TileState::new(&tile);
        state_vec_insert(&mut self.state_handle.get_mut().tiles, state);

        // add building death to current state
        if let Some((owner, building)) = deaths {
            if let Some(ids) = self.state_handle.get_mut().dead_building.get_mut(&owner) {
                ids.push(building);
            } else {
                self.state_handle
                    .get_mut()
                    .dead_building
                    .insert(owner, vec![building]);
            }
        }

        true
    }

    /// run the map
    pub fn run(&mut self, dt: f64) {
        if self.delayer_deprecate.wait(dt) {
            self.deprecate_tiles();
        }
    }
}

struct TileConfig {
    max_occupation: u32,
    building_occupation_min: u32,
}

#[derive(Clone, Debug)]
pub struct TileState {
    pub id: u128,
    pub coord: Option<Coord>,
    pub occupation: Option<u32>,
    pub owner_id: Option<u128>,
}

impl Identifiable for TileState {
    fn id(&self) -> u128 {
        self.id
    }
}

impl State for TileState {
    type Metadata = Tile;

    fn new(_metadata: &Self::Metadata) -> Self {
        TileState {
            id: _metadata.id,
            coord: None, // only specify coord on map creation
            occupation: Some(_metadata.occupation),
            owner_id: _metadata.owner_id,
        }
    }

    fn merge(&mut self, state: Self) {
        if let Some(coord) = state.coord {
            self.coord = Some(coord);
        }
        if let Some(occupation) = state.occupation {
            self.occupation = Some(occupation);
        }
        if let Some(owner_id) = state.owner_id {
            self.owner_id = Some(owner_id);
        }
    }
}

pub struct Tile {
    pub id: u128,
    config: TileConfig,
    coord: Coord,
    pub occupation: u32,
    pub owner_id: Option<u128>,
    /// may be id of: Factory, Turret
    pub building_id: Option<u128>,
}

impl Tile {
    pub fn new(config: &GameConfig, coord: Coord) -> Self {
        return Tile {
            id: core::generate_unique_id(),
            config: TileConfig {
                max_occupation: config.max_occupation,
                building_occupation_min: config.building_occupation_min,
            },
            coord: coord,
            occupation: 0,
            owner_id: None,
            building_id: None,
        };
    }

    /// Return complete current tile state
    pub fn get_complete_state(&self) -> TileState {
        TileState {
            id: self.id,
            coord: Some(self.coord.clone()),
            occupation: Some(self.occupation),
            owner_id: self.owner_id,
        }
    }

    /// Return if the given player can build on tile
    pub fn can_build(&self, player: &Player) -> bool {
        self.building_id.is_none()
            && self.is_owned_by(player.id)
            && self.occupation >= self.config.building_occupation_min
    }

    /// Return if the tile is owned by the given player
    pub fn is_owned_by(&self, player_id: u128) -> bool {
        match self.owner_id {
            None => false,
            Some(id) => id == player_id,
        }
    }

    /// Return if the tile is owned someone else than `player`
    pub fn is_owned_by_opponent_of(&self, player_id: u128) -> bool {
        match self.owner_id {
            None => false,
            Some(id) => id != player_id,
        }
    }

    /// Set the owner of the tile
    pub fn set_owner(&mut self, player_id: u128) {
        self.owner_id = Some(player_id);
    }

    /// Increment tile occupation by `value`
    pub fn incr_occupation(&mut self, value: u32) {
        self.occupation = u32::min(self.occupation + value, self.config.max_occupation);
    }

    /// Decrement tile occupation by `value`
    pub fn decr_occupation(&mut self, value: u32) {
        // don't use the max way -> negative value don't exists on unsigned
        if self.occupation >= value {
            self.occupation -= value;
        } else {
            self.occupation = 0;
        }
    }
}
