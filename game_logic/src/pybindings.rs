use std::ops::{Add, Sub};

use super::game::{
    Coord, FactoryDeathCause, FactoryState, GameConfig, GameState, MapState, PlayerState, Point,
    ProbeDeathCause, ProbeState, TileState,
};
use pyo3::{exceptions, types::PyDict, FromPyObject, PyClass, PyErr, PyResult, Python};

pub trait AsDict<'a> {
    fn to_dict(&self, _py: Python<'a>) -> PyResult<&'a PyDict>;
}

pub trait FromDict
where
    Self: Sized,
{
    fn from_dict(dict: &PyDict) -> PyResult<Self>;
}

/// Add the item add the given key if not None \
/// Example: `set_item(dict, "foo", Some(2))` \
/// `{"foo": 2}`
fn set_item<T>(dict: &PyDict, key: &str, item: &Option<T>) -> PyResult<()>
where
    T: pyo3::ToPyObject,
{
    if let Some(item) = item {
        dict.set_item(key, item)?;
    }
    Ok(())
}

/// Add the item add the given key if not None \
/// Example:
/// `set_item(dict, "foo", Some(Coord::new(2, 3)))` \
/// `{"foo": {"x": 2, "y": 3}}`
fn set_dict_item<'a, T>(_py: Python<'a>, dict: &PyDict, key: &str, item: &Option<T>) -> PyResult<()>
where
    T: AsDict<'a>,
{
    if let Some(item) = item {
        dict.set_item(key, item.to_dict(_py)?)?;
    }
    Ok(())
}

/// Add the item add the given key if not None \
/// Example:
/// `set_item(_py, dict, "foo", vec![Coord::new(2, 3)])` \
/// `{"foo": [{"x": 2, "y": 3}]}`
fn set_vec_dict_item<'a, T>(
    _py: Python<'a>,
    dict: &PyDict,
    key: &str,
    item: &Vec<T>,
) -> PyResult<()>
where
    T: AsDict<'a>,
{
    let mut items = Vec::with_capacity(item.len());
    for item in item.iter() {
        items.push(item.to_dict(_py)?);
    }
    dict.set_item(key, items)?;
    Ok(())
}

/// Extract item from a dict
fn get_item<'a, T>(dict: &'a PyDict, key: &str) -> PyResult<T>
where
    T: FromPyObject<'a>,
{
    match dict.get_item(key) {
        Some(x) => Ok(x.extract::<'a, T>()?),
        None => Err(PyErr::new::<exceptions::PyValueError, _>(format!(
            "Missing '{}' key in {:?}",
            key, dict
        ))),
    }
}

impl<'a> AsDict<'a> for Coord {
    fn to_dict(&self, _py: Python<'a>) -> PyResult<&'a PyDict> {
        let dict = PyDict::new(_py);
        dict.set_item("x", self.x)?;
        dict.set_item("y", self.y)?;
        Ok(dict)
    }
}

impl<'a> AsDict<'a> for Point {
    fn to_dict(&self, _py: Python<'a>) -> PyResult<&'a PyDict> {
        let dict = PyDict::new(_py);
        dict.set_item("x", self.x)?;
        dict.set_item("y", self.y)?;
        Ok(dict)
    }
}

impl<'a> AsDict<'a> for TileState {
    fn to_dict(&self, _py: Python<'a>) -> PyResult<&'a PyDict> {
        let dict = PyDict::new(_py);
        dict.set_item("id", self.id)?;
        set_dict_item(_py, dict, "coord", &self.coord)?;
        set_item(dict, "occupation", &self.occupation)?;
        set_item(dict, "owner_id", &self.owner_id)?;

        Ok(dict)
    }
}

impl<'a> AsDict<'a> for ProbeState {
    fn to_dict(&self, _py: Python<'a>) -> PyResult<&'a PyDict> {
        let dict = PyDict::new(_py);
        match self.id {
            None => {
                // In case the state doesn't have an id (as for new probe)
                // raise a python error (cause why not)
                return Err(PyErr::new::<exceptions::PyValueError, _>("Missing id"));
            }
            Some(id) => {
                dict.set_item("id", id)?;
            }
        }

        if let Some(death) = &self.death {
            let death = match death {
                ProbeDeathCause::Exploded => "Exploded",
                ProbeDeathCause::Shot => "Shot",
                ProbeDeathCause::Scrapped => "Scrapped",
            };
            dict.set_item("death", death)?;
        }

        set_dict_item(_py, dict, "pos", &self.pos)?;
        set_dict_item(_py, dict, "target", &self.target)?;

        Ok(dict)
    }
}

impl<'a> AsDict<'a> for FactoryState {
    fn to_dict(&self, _py: Python<'a>) -> PyResult<&'a PyDict> {
        let dict = PyDict::new(_py);
        dict.set_item("id", self.id)?;

        if let Some(death) = &self.death {
            let death = match death {
                FactoryDeathCause::Conquered => "Conquered",
            };
            dict.set_item("death", death)?;
        }

        set_dict_item(_py, dict, "coord", &self.coord)?;
        set_vec_dict_item(_py, dict, "probes", &self.probes)?;

        Ok(dict)
    }
}

impl<'a> AsDict<'a> for PlayerState {
    fn to_dict(&self, _py: Python<'a>) -> PyResult<&'a PyDict> {
        let dict = PyDict::new(_py);

        dict.set_item("id", self.id)?;
        set_item(dict, "money", &self.money)?;
        set_item(dict, "income", &self.income)?;
        set_vec_dict_item(_py, dict, "factories", &self.factories)?;
        dict.set_item("turrets", &Vec::<i32>::new())?;

        Ok(dict)
    }
}

impl<'a> AsDict<'a> for MapState {
    fn to_dict(&self, _py: Python<'a>) -> PyResult<&'a PyDict> {
        let dict = PyDict::new(_py);

        set_vec_dict_item(_py, dict, "tiles", &self.tiles)?;

        Ok(dict)
    }
}

impl<'a> AsDict<'a> for GameState {
    fn to_dict(&self, _py: Python<'a>) -> PyResult<&'a PyDict> {
        let dict = PyDict::new(_py);

        set_dict_item(_py, dict, "map", &self.map)?;
        set_vec_dict_item(_py, dict, "players", &self.players)?;

        Ok(dict)
    }
}

impl FromDict for Coord {
    fn from_dict(dict: &PyDict) -> PyResult<Self> {
        let x: f64 = get_item(dict, "x")?;
        let y: f64 = get_item(dict, "y")?;
        Ok(Coord::new(x as i32, y as i32))
    }
}

impl FromDict for GameConfig {
    fn from_dict(dict: &PyDict) -> PyResult<Self> {
        let dim = match dict.get_item("dim") {
            Some(v) => match v.downcast() {
                Ok(v) => Coord::from_dict(v),
                Err(_) => Err(PyErr::new::<exceptions::PyValueError, _>(
                    "dim has to be a dict",
                )),
            },
            None => {
                return Err(PyErr::new::<exceptions::PyValueError, _>(format!(
                    "Missing 'dim' key in {:?}",
                    dict
                )));
            }
        }?;

        Ok(GameConfig {
            dim: dim,
            n_player: get_item(dict, "n_player")?,
            initial_money: get_item(dict, "initial_money")?,
            initial_n_probes: get_item(dict, "initial_n_probes")?,
            base_income: get_item(dict, "base_income")?,
            building_occupation_min: get_item(dict, "building_occupation_min")?,
            factory_price: get_item(dict, "factory_price")?,
            factory_max_probe: get_item(dict, "factory_max_probe")?,
            factory_build_probe_delay: get_item(dict, "factory_build_probe_delay")?,
            max_occupation: get_item(dict, "max_occupation")?,
            probe_speed: get_item(dict, "probe_speed")?,
            probe_price: get_item(dict, "probe_price")?,
            probe_claim_delay: get_item(dict, "probe_claim_delay")?,
            probe_maintenance_costs: get_item(dict, "probe_maintenance_costs")?,
            turret_price: get_item(dict, "turret_price")?,
            turret_fire_delay: get_item(dict, "turret_fire_delay")?,
            turret_scope: get_item(dict, "turret_scope")?,
            turret_maintenance_costs: get_item(dict, "turret_maintenance_costs")?,
            income_rate: get_item(dict, "income_rate")?,
            deprecate_rate: get_item(dict, "deprecate_rate")?,
        })
    }
}
