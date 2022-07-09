use super::{
    core,
    core::{Coord, Identifiable},
    geometry,
    player::Player,
    probe::Probe,
    random, GameConfig,
};

use log::warn;

struct MapConfig {
    pub dim: Coord,
    pub max_occupation: u32,
}

pub struct Map {
    config: MapConfig,
    tiles: Vec<Vec<Tile>>,
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
            },
            tiles: tiles,
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
}

impl Map {
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
            }
        }
        return false;
    }

    /// Return a target to farm (own or unoccupied tile)
    /// in the surroundings of the probe if possible
    fn get_close_probe_farm_target(&self, player: &Player, coord: &Coord) -> Option<Coord> {
        let mut coords = geometry::square(coord, 3);
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
    /// Return if it could be done
    pub fn claim_tile(&mut self, probe: &Probe) -> bool {
        let tile = self.get_mut_tile(&probe.get_coord());
        let tile = match tile {
            None => {
                return false;
            }
            Some(tile) => tile,
        };
        match &tile.owner_id {
            None => {
                tile.set_owner(probe.player);
            }
            Some(owner_id) => {
                if owner_id == probe.player.get_id() {
                    tile.incr_occupation();
                } else {
                    tile.decr_occupation();
                    if tile.occupation == 0 {
                        tile.owner_id = None;
                    }
                }
            }
        }
        true
    }
}

struct TileConfig {
    max_occupation: u32,
}

pub struct Tile {
    id: String,
    config: TileConfig,
    coord: Coord,
    pub occupation: u32,
    pub owner_id: Option<String>,
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
        };
    }

    /// Return if the tile is owned by the given player
    pub fn is_owned_by(&self, player: &Player) -> bool {
        match &self.owner_id {
            None => false,
            Some(id) => id.as_str() == player.get_id(),
        }
    }

    /// Return if the tile is owned someone else than `player`
    pub fn is_owned_by_opponent_of(&self, player: &Player) -> bool {
        match &self.owner_id {
            None => false,
            Some(id) => id.as_str() != player.get_id(),
        }
    }

    /// Set the owner of the tile
    /// Reset the occupation
    pub fn set_owner(&mut self, player: &Player) {
        self.owner_id = Some(player.get_id().to_owned());
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

impl Identifiable for Tile {
    fn get_id(&self) -> &str {
        &self.id
    }
}
