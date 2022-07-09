use super::core::Coord;

/// Return the coordinates from `distance` of the origin,
/// without the origin, in a square shape:
/// ```
/// distance: 1 & 2 & 3
///                                   *
///                   *             * * *
///       *         * * *         * * * * *
///     *   *     * *   * *     * * *   * * *
///       *         * * *         * * * * *
///                   *             * * *
///                                   *
/// ```
pub fn square_without_origin(origin: &Coord, distance: u32) -> Vec<Coord> {
    let mut coords: Vec<Coord> = Vec::new();
    let distance = distance as i32;
    for y in 0..distance as i32 {
        for x in 0..(2 * y + 1) {
            coords.push(Coord::new(origin.x + x - y, origin.y - distance + y));
            coords.push(Coord::new(origin.x + x - y, origin.y + distance - y));
        }
    }

    for x in 0..distance {
        coords.push(Coord::new(origin.x - distance + x, origin.y));
    }
    for x in 0..distance {
        coords.push(Coord::new(origin.x + x + 1, origin.y));
    }

    return coords;
}

/// Return the coordinates from `distance` of the origin,
/// in a square shape:
/// ```
/// distance: 1 & 2 & 3
///                                   *
///                   *             * * *
///       *         * * *         * * * * *
///     * * *     * * * * *     * * * * * * *
///       *         * * *         * * * * *
///                   *             * * *
///                                   *
/// ```
pub fn square(origin: &Coord, distance: u32) -> Vec<Coord> {
    let mut coords: Vec<Coord> = Vec::new();
    let distance = distance as i32;
    for y in 0..distance as i32 {
        for x in 0..(2 * y + 1) {
            coords.push(Coord::new(origin.x + x - y, origin.y - distance + y));
            coords.push(Coord::new(origin.x + x - y, origin.y + distance - y));
        }
    }

    for x in 0..(2 * distance + 1) {
        coords.push(Coord::new(origin.x - distance + x, origin.y));
    }

    return coords;
}

/// Return the coordinates at `distance` of the origin,
/// in a square shape:
/// ```
/// distance: 1 & 2 & 3
///                                   *
///                   *             *   *
///       *         *   *         *       *
///     *   *     *       *     *           *
///       *         *   *         *       *
///                   *             *   *
///                                   *
/// ```
pub fn ring(origin: &Coord, distance: u32) -> Vec<Coord> {
    let mut coords: Vec<Coord> = Vec::new();
    let distance = distance as i32;

    if distance == 0 {
        coords.push(origin.clone());
        return coords;
    }

    for y in 1..distance as i32 {
        coords.push(Coord::new(origin.x - y, origin.y - distance + y));
        coords.push(Coord::new(origin.x - y, origin.y + distance - y));
        coords.push(Coord::new(origin.x + y, origin.y - distance + y));
        coords.push(Coord::new(origin.x + y, origin.y + distance - y));
    }

    coords.push(Coord::new(origin.x, origin.y + distance));
    coords.push(Coord::new(origin.x, origin.y - distance));
    coords.push(Coord::new(origin.x + distance, origin.y));
    coords.push(Coord::new(origin.x - distance, origin.y));

    return coords;
}

/// Return an iterator that yield the coordinates around
/// the origin (first coordinate yielded) from the successive
/// rings (with distance 1, 2, 3, ...), never stops. \
/// Example, first 5 coordinates yielded:
/// ```
///  1.      2.      3.      4.      5.
///                                     *  
///     *       * *   * * *   * * *   * * *
///                             *       *  
/// ```
pub fn iter_vortex<'a>(origin: &'a Coord) -> IterVortex {
    IterVortex::new(origin)
}

pub struct IterVortex<'a> {
    origin: &'a Coord,
    distance: u32,
    ring: Vec<Coord>,
    idx: usize,
}

impl<'a> IterVortex<'a> {
    pub fn new(origin: &'a Coord) -> Self {
        IterVortex {
            origin: origin,
            distance: 0,
            ring: vec![origin.clone()],
            idx: 0,
        }
    }
}

impl<'a> Iterator for IterVortex<'a> {
    type Item = Coord;
    fn next(&mut self) -> Option<Self::Item> {
        match self.ring.get(self.idx) {
            Some(coord) => {
                self.idx += 1;
                return Some(coord.clone());
            }
            None => {
                self.distance += 1;
                self.ring = ring(self.origin, self.distance);
                self.idx = 1;
                return Some(self.ring[0].clone());
            }
        }
    }
}
