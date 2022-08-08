mod game;
mod pybindings;

use env_logger;
use pybindings::{AsDict, FromDict};
use pyo3::{exceptions, prelude::*, types::PyDict};

#[pyclass]
struct Game {
    game: game::Game,
}

#[pymethods]
impl Game {
    #[new]
    fn new(player_ids: Vec<u128>, config: &PyDict) -> PyResult<Self> {
        env_logger::init();
        let config = game::GameConfig::from_dict(&config)?;
        Ok(Game {
            game: game::Game::new(player_ids, config),
        })
    }

    pub fn get_state<'a>(&self, _py: Python<'a>) -> PyResult<&'a PyDict> {
        self.game.get_complete_state().to_dict(_py)
    }

    pub fn run<'a>(&mut self, _py: Python<'a>, dt: f64) -> PyResult<Option<&'a PyDict>> {
        let state = self.game.run(dt);

        match state {
            None => Ok(None),
            Some(state) => Ok(Some(state.to_dict(_py)?)),
        }
    }

    pub fn action_resign_game<'a>(&mut self, _py: Python<'a>, player_id: u128) -> PyResult<()> {
        match self.game.resign_game(player_id) {
            Err(msg) => Err(PyErr::new::<exceptions::PyValueError, _>(msg)),
            Ok(v) => Ok(v),
        }
    }

    pub fn action_build_factory<'a>(
        &mut self,
        _py: Python<'a>,
        player_id: u128,
        coord_x: i32,
        coord_y: i32,
    ) -> PyResult<()> {
        match self.game.create_factory(player_id, coord_x, coord_y) {
            Err(msg) => Err(PyErr::new::<exceptions::PyValueError, _>(msg)),
            Ok(v) => Ok(v),
        }
    }

    pub fn action_move_probes<'a>(
        &mut self,
        _py: Python<'a>,
        player_id: u128,
        ids: Vec<u128>,
        target_x: i32,
        target_y: i32,
    ) -> PyResult<()> {
        match self.game.move_probes(player_id, ids, target_x, target_y) {
            Err(msg) => Err(PyErr::new::<exceptions::PyValueError, _>(msg)),
            Ok(v) => Ok(v),
        }
    }

    pub fn action_explode_probes<'a>(
        &mut self,
        _py: Python<'a>,
        player_id: u128,
        ids: Vec<u128>,
    ) -> PyResult<()> {
        match self.game.explode_probes(player_id, ids) {
            Err(msg) => Err(PyErr::new::<exceptions::PyValueError, _>(msg)),
            Ok(v) => Ok(v),
        }
    }

    pub fn action_probes_attack<'a>(
        &mut self,
        _py: Python<'a>,
        player_id: u128,
        ids: Vec<u128>,
    ) -> PyResult<()> {
        match self.game.probes_attack(player_id, ids) {
            Err(msg) => Err(PyErr::new::<exceptions::PyValueError, _>(msg)),
            Ok(v) => Ok(v),
        }
    }
}

/// A Python module implemented in Rust.
#[pymodule]
fn game_logic(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Game>()?;
    Ok(())
}
