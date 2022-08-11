use std::collections::HashMap;

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

    /// Normalize self
    pub fn normalize(&mut self) {
        let norm = self.norm();
        if norm == 0.0 {
            return;
        }
        self.x /= norm;
        self.y /= norm;
    }

    /// Return the norm of the point
    pub fn norm(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
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

pub fn generate_unique_id() -> u128 {
    loop {
        match uuid::Uuid::new_v4().as_u128() {
            NOT_IDENTIFIABLE => {
                continue;
            }
            id => {
                return id;
            }
        }
    }
}

/// Delayer
/// Designed to be called each frame (see `wait()`)
pub struct Delayer {
    delay: f64,
    counter: f64,
    total_delayed: f64,
}

impl Delayer {
    /// Create new instance
    /// Specify the delay to wait (unit: sec)
    pub fn new(delay: f64) -> Self {
        Delayer {
            delay: delay,
            counter: 0.0,
            total_delayed: 0.0,
        }
    }

    /// Return amount of time waited since the creation of
    /// the instance (not affected by `reset`)
    pub fn get_total_delayed(&self) -> f64 {
        self.total_delayed
    }

    /// Reset the delay counter
    pub fn reset(&mut self) {
        self.total_delayed += self.counter;
        self.counter = 0.0;
    }

    /// Set the delay to wait (unit: sec)
    pub fn set_delay(&mut self, delay: f64) {
        self.delay = delay;
    }

    /// Increment the delay counter,
    /// when the delay is reached: reset the counter
    /// and return true
    pub fn wait(&mut self, dt: f64) -> bool {
        self.counter += dt;
        if self.counter >= self.delay {
            self.reset();
            return true;
        }
        false
    }
}

/// Define type as identifiable
pub trait Identifiable {
    fn id(&self) -> u128;

    /// Return if `other` is the same as self \
    /// Note: Takes `NOT_IDENTIFIABLE` into account when
    /// comparing ids.
    fn is(&self, other: &Self) -> bool {
        let id = self.id();
        id != NOT_IDENTIFIABLE && id == other.id()
    }
}

/// Similar to NaN, will always be considered different
/// from any other id
pub const NOT_IDENTIFIABLE: u128 = 0;

/// Define state type \
/// Store state data (indented to contains partial attributes)
pub trait State: Clone {
    /// Metadata is what is passed to the constructor
    type Metadata;

    /// Create a new state instance
    fn new(_metadata: &Self::Metadata) -> Self;

    /// Merge (inplace) the state with another one (consumed)
    fn merge(&mut self, state: Self);
}

/// Insert `state` in the `states` vector \
/// In case the state already exists (as defined by `Identifiable`)
/// in `states`: merge it with `state`, else push it to the vector
pub fn state_vec_insert<T>(states: &mut Vec<T>, state: T)
where
    T: State + Identifiable,
{
    for current_state in states.iter_mut() {
        if current_state.is(&state) {
            current_state.merge(state);
            return;
        }
    }
    states.push(state);
}

/// State wrapper \
/// Used to gradually build state
pub struct StateHandler<T: State> {
    state: T,
    /// Indicates if a state was built in
    /// the current frame
    is_state: bool,
}

impl<T> StateHandler<T>
where
    T: State,
{
    /// Create new StateHandler instance
    pub fn new(_metadata: &T::Metadata) -> Self {
        StateHandler {
            is_state: false,
            state: T::new(_metadata),
        }
    }

    /// Return the handler's current state \
    /// Do NOT set `is_state` flag
    pub fn get(&self) -> &T {
        &self.state
    }

    /// Return the handler's current state \
    /// Set `is_state` flag
    pub fn get_mut(&mut self) -> &mut T {
        self.is_state = true;
        &mut self.state
    }

    /// Merge given state with current one
    /// Set `is_state` flag
    pub fn merge(&mut self, state: T) {
        self.state.merge(state);
        self.is_state = true;
    }

    /// If `is_state` flag is set:
    /// return handler's current state,
    /// else `None` \
    /// Reset current state & `is_state` flag
    pub fn flush(&mut self, _metadata: &T::Metadata) -> Option<T> {
        if !self.is_state {
            return None;
        }
        let state = self.state.clone();
        self.state = T::new(_metadata);
        self.is_state = false;
        Some(state)
    }
}
