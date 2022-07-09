use super::*;

pub struct Player<'a> {
    id: String,
    pub factories: Vec<Factory<'a>>,
}
impl Player<'_> {
    pub fn new() -> Self {
        Player {
            id: generate_unique_id(),
            factories: Vec::new(),
        }
    }
}

impl<'a> Runnable for Player<'a> {
    type State = ();

    fn run(&mut self, ctx: &mut FrameContext) -> Option<Self::State> {
        for factory in self.factories.iter_mut() {
            factory.run(ctx);
        }
        None
    }
}

impl<'a> Identifiable for Player<'a> {
    fn get_id(&self) -> &str {
        &self.id
    }
}
