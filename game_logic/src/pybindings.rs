use super::game::{
    Coord, FactoryDeathCause, FactoryState, GameState, MapState, PlayerState, Point,
    ProbeDeathCause, ProbeState, TileState,
};
use pyo3::{exceptions, types::PyDict, PyErr, PyResult, Python};

pub trait AsDict<'a> {
    fn to_dict(&self, _py: Python<'a>) -> PyResult<&'a PyDict>;
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

impl<'a> AsDict<'a> for Coord {
    fn to_dict(&self, _py: Python<'a>) -> PyResult<&'a PyDict> {
        let dict = PyDict::new(_py);
        dict.set_item("x", self.x)?;
        dict.set_item("y", self.x)?;
        Ok(dict)
    }
}

impl<'a> AsDict<'a> for Point {
    fn to_dict(&self, _py: Python<'a>) -> PyResult<&'a PyDict> {
        let dict = PyDict::new(_py);
        dict.set_item("x", self.x)?;
        dict.set_item("y", self.x)?;
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
        set_vec_dict_item(_py, dict, "factories", &self.factories)?;

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
