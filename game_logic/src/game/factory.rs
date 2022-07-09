use super::core;
use super::core::{Coord, FrameContext, Identifiable, Runnable};
use super::probe::Probe;

pub struct Factory<'a> {
    id: String,
    pub pos: Coord,
    probes: Vec<Probe<'a>>,
}

impl<'a> Factory<'a> {
    pub fn new(pos: Coord) -> Self {
        Factory {
            id: core::generate_unique_id(),
            pos: pos,
            probes: Vec::new(),
        }
    }
}

impl<'a> Runnable for Factory<'a> {
    type State = ();

    fn run(&mut self, ctx: &mut FrameContext) -> Option<Self::State> {
        for probe in self.probes.iter_mut() {
            probe.run(ctx);
        }
        None
    }
}

impl Identifiable for Factory<'_> {
    fn get_id(&self) -> &str {
        &self.id
    }
}
