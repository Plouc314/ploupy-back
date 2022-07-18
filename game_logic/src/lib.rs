mod game;
mod pybindings;

use std::env;

use env_logger;
use game::Tile;
use pybindings::AsDict;
use pyo3::{prelude::*, types::PyDict};

#[pyclass]
struct Game {
    game: game::Game,
}

#[pymethods]
impl Game {
    #[new]
    fn new(player_ids: Vec<u128>) -> Self {
        let config = game::GameConfig {
            dim: game::Coord { x: 10, y: 10 },
            n_player: 3,
            initial_money: 20.0,
            initial_n_probes: 3,
            base_income: 0.0,
            building_occupation_min: 0,
            factory_price: 0.0,
            factory_max_probe: 0,
            factory_build_probe_delay: 0.0,
            max_occupation: 0,
            probe_speed: 0.0,
            probe_price: 0.0,
            probe_claim_delay: 0.0,
            probe_maintenance_costs: 0.0,
            turret_price: 0.0,
            turret_fire_delay: 0,
            turret_scope: 0.0,
            turret_maintenance_costs: 0.0,
            income_rate: 0.0,
            deprecate_rate: 0.0,
        };
        Game {
            game: game::Game::new(player_ids, config),
        }
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
