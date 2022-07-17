use super::game::TileState;
use pyo3::{types::PyDict, Python};

pub trait AsDict<'a> {
    fn to_dict(&self, _py: Python<'a>) -> &'a PyDict;
}

impl<'a> AsDict<'a> for TileState {
    fn to_dict(&self, _py: Python<'a>) -> &'a PyDict {
        let dict = PyDict::new(_py);
        dict.set_item("id", self.id).unwrap();
        if let Some(occupation) = self.occupation {
            dict.set_item("occupation", occupation).unwrap();
        }
        if let Some(owner_id) = self.owner_id {
            dict.set_item("owner_id", owner_id).unwrap();
        }
        dict
    }
}
