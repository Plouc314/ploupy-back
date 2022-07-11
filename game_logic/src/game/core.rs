use super::*;

#[derive(Debug, PartialEq)]
pub struct Point {
    pub x: f64,
    pub y: f64,
}

impl Point {
    pub fn new(x: f64, y: f64) -> Self {
        Point { x, y }
    }

    /// Return the Coord equivalent of self
    pub fn as_coord(&self) -> Coord {
        Coord::new(self.x as i32, self.y as i32)
    }

    /// Consume self \
    /// Return normalized point
    pub fn normalize(mut self) -> Self {
        let norm = (self.x * self.x + self.y * self.y).sqrt();
        if norm == 0.0 {
            return self;
        }
        self.x /= norm;
        self.y /= norm;
        self
    }

    /// Add another point to self (inplace)
    pub fn add(&mut self, point: &Point) {
        self.x += point.x;
        self.y += point.y;
    }

    /// Multiply components by given factor (inplace)
    pub fn mul(&mut self, factor: f64) {
        self.x *= factor;
        self.y *= factor;
    }
}

impl Clone for Point {
    fn clone(&self) -> Self {
        Point::new(self.x, self.y)
    }
}

#[derive(Debug, PartialEq)]
pub struct Coord {
    pub x: i32,
    pub y: i32,
}

impl Coord {
    pub fn new(x: i32, y: i32) -> Self {
        Coord { x, y }
    }

    pub fn as_point(&self) -> Point {
        Point::new(self.x as f64, self.y as f64)
    }

    pub fn is_positive(&self) -> bool {
        self.x >= 0 && self.y >= 0
    }
}

impl Clone for Coord {
    fn clone(&self) -> Self {
        Coord::new(self.x, self.y)
    }
}

pub struct FrameContext<'a> {
    pub dt: f64,
    pub config: &'a GameConfig,
    pub map: &'a mut Map,
}

pub trait Runnable {
    type State;
    fn run(&mut self, ctx: &mut FrameContext) -> Option<Self::State>;
}

pub fn generate_unique_id() -> u128 {
    return 0;
}
