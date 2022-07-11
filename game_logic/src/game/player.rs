use super::*;

pub struct PlayerConfig {
    initial_money: f64,
    initial_n_probes: u32,
    base_income: f64,
    probe_price: f64,
}

pub struct Player<'a> {
    pub id: u128,
    config: PlayerConfig,
    money: f64,
    pub factories: Vec<Factory<'a>>,
}
impl Player<'_> {
    pub fn new(config: &GameConfig) -> Self {
        Player {
            id: generate_unique_id(),
            config: PlayerConfig {
                initial_money: config.initial_money,
                initial_n_probes: config.initial_n_probes,
                base_income: config.base_income,
                probe_price: config.probe_price,
            },
            money: 0.0,
            factories: Vec::new(),
        }
    }

    fn create_probe(&mut self, state: ProbeState, ctx: &mut FrameContext) {
        if self.money < self.config.probe_price {
            return;
        }
        if let Some(pos) = state.pos {
            self.money -= self.config.probe_price;
            let mut probe = Probe::new(self, ctx.config, pos);
            // TODO
        }
    }
}

impl<'a> Runnable for Player<'a> {
    type State = ();

    fn run(&mut self, ctx: &mut FrameContext) -> Option<Self::State> {
        let mut states = Vec::new();
        for factory in self.factories.iter_mut() {
            let state = factory.run(ctx);
            if let Some(state) = state {
                states.push(state);
            }
        }
        None
    }
}
