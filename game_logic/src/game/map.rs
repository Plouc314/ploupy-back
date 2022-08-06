use std::collections::HashMap;

use super::{core, core::Coord, geometry, player::Player, probe::Probe, random, GameConfig};

use log::warn;

struct MapConfig {
    pub dim: Coord,
    pub max_occupation: u32,
    pub income_rate: f64,
}

#[derive(Clone, Debug)]
pub struct MapState {
    pub tiles: Vec<TileState>,
    /// store state of dead factories
    /// Internal to rust implementation
    dead_building: HashMap<u128, Vec<u128>>,
}

impl MapState {
    pub fn new() -> Self {
        MapState {
            tiles: Vec::new(),
            dead_building: HashMap::new(),
        }
    }

    /// Return `dead_building` attribute
    pub fn get_dead_building(&self) -> &HashMap<u128, Vec<u128>> {
        &self.dead_building
    }
}

pub struct Map {
    config: MapConfig,
    tiles: Vec<Vec<Tile>>,
    /// Store potential map state at this frame
    /// used to gradually build map state during
    /// run() functions (executed by all Runnable entities)
    /// Should not be dealt with directly, or see `is_state`
    current_state: MapState,
    /// Indicates if a probe state was built in
    /// the current frame
    is_state: bool,
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
                income_rate: config.income_rate,
            },
            tiles: tiles,
            current_state: MapState::new(),
            is_state: false,
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

    /// Return the current state
    /// AND stores that there is a map state
    /// (see self.is_state)
    fn mut_state(&mut self) -> &mut MapState {
        self.is_state = true;
        &mut self.current_state
    }

    /// Return the income of all his owned tiles to one player
    pub fn get_player_income(&self, player: &Player) -> f64 {
        let mut income = 0.0;
        for col in self.tiles.iter() {
            for tile in col.iter() {
                if tile.is_owned_by(player) {
                    income += tile.occupation as f64 * self.config.income_rate;
                }
            }
        }
        income
    }

    /// Return current state \
    /// In case is_state is true,
    /// reset current state and create new MapState instance
    pub fn flush_state(&mut self) -> Option<MapState> {
        if !self.is_state {
            return None;
        }
        let state = self.current_state.clone();
        self.current_state = MapState::new();
        self.is_state = false;
        Some(state)
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

        if !tile.is_owned_by(player) {
            // check if tile occupied by an other player
            if tile.occupation > 3 {
                return false;
            } else {
                // assert that tile is not isolated
                let neighbours = self.get_neighbour_tiles(tile, 1);
                for neighbour in neighbours.iter() {
                    if neighbour.is_owned_by(player) {
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
    pub fn get_probe_attack_target(&self, player: &Player, probe: &Probe) -> Option<Coord> {
        let mut target_tile: Option<&Tile> = None;

        let mut idx = 0;

        for coord in geometry::iter_vortex(&probe.get_coord()) {
            if let Some(tile) = self.get_tile(&coord) {
                if tile.is_owned_by_opponent_of(player) {
                    target_tile = Some(tile);
                    break;
                }
            }
            idx += 1;
            if idx == 1000 {
                warn!("Didn't found attack target");
                return None;
            }
        }
        // choose tile in region
        let mut tiles = self.get_neighbour_tiles(&target_tile.unwrap(), 2);
        random::shuffle_vec(&mut tiles);
        for tile in tiles {
            if tile.is_owned_by_opponent_of(player) {
                return Some(tile.coord.clone());
            }
        }
        None
    }

    /// Claim the tile at the coordinate of the probe \
    /// Store the tile state, potential building death in current state \
    /// Return if it could be done
    pub fn claim_tile(&mut self, player: &Player, coord: &Coord) -> bool {
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
                tile.set_owner(player);
            }
            Some(owner_id) => {
                if owner_id == player.id {
                    tile.incr_occupation();
                } else {
                    tile.decr_occupation();
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
        let state = TileState::from_tile(tile);
        self.mut_state().tiles.push(state);

        // add building death to current state
        if let Some((owner, building)) = deaths {
            if let Some(ids) = self.current_state.dead_building.get_mut(&owner) {
                ids.push(building);
            } else {
                self.current_state
                    .dead_building
                    .insert(owner, vec![building]);
            }
        }

        true
    }
}

struct TileConfig {
    max_occupation: u32,
}

#[derive(Clone, Debug)]
pub struct TileState {
    pub id: u128,
    pub coord: Option<Coord>,
    pub occupation: Option<u32>,
    pub owner_id: Option<u128>,
}

impl TileState {
    pub fn from_tile(tile: &Tile) -> Self {
        TileState {
            id: tile.id,
            coord: None, // only specify coord on map creation
            occupation: Some(tile.occupation),
            owner_id: tile.owner_id,
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

    /// Return if the tile is owned by the given player
    pub fn is_owned_by(&self, player: &Player) -> bool {
        match self.owner_id {
            None => false,
            Some(id) => id == player.id,
        }
    }

    /// Return if the tile is owned someone else than `player`
    pub fn is_owned_by_opponent_of(&self, player: &Player) -> bool {
        match self.owner_id {
            None => false,
            Some(id) => id != player.id,
        }
    }

    /// Set the owner of the tile
    /// Reset the occupation
    pub fn set_owner(&mut self, player: &Player) {
        self.owner_id = Some(player.id);
        self.occupation = 1;
    }

    /// Increment tile occupation
    pub fn incr_occupation(&mut self) {
        if self.occupation < self.config.max_occupation {
            self.occupation += 1;
        }
    }

    /// Decrement tile occupation
    pub fn decr_occupation(&mut self) {
        if self.occupation > 0 {
            self.occupation -= 1;
        }
    }
}
