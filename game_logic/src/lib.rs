mod game;
mod pybindings;

use std::env;

use env_logger;
use game::Tile;
use pybindings::{AsDict, FromDict};
use pyo3::{prelude::*, types::PyDict};

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

    pub fn run<'a>(&mut self, _py: Python<'a>) -> PyResult<Option<&'a PyDict>> {
        let state = self.game.run();

        match state {
            None => Ok(None),
            Some(state) => Ok(Some(state.to_dict(_py)?)),
        }
    }
}

/// A Python module implemented in Rust.
#[pymodule]
fn game_logic(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Game>()?;
    Ok(())
}
