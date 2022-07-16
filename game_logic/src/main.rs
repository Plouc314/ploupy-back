mod game;

use std::cell::RefCell;
use std::rc::Rc;
use std::rc::Weak;

use game::iter_vortex;
use game::square;
use game::square_without_origin;
use game::Coord;
use game::Game;
use game::GameConfig;

fn display(origin: &Coord, coords: &Vec<Coord>) {
    let mut chars = vec![vec![' '; 10]; 10];

    chars[origin.x as usize][origin.y as usize] = 'X';
    for coord in coords.iter() {
        chars[coord.x as usize][coord.y as usize] = 'o';
    }

    for seq in chars.iter() {
        for char in seq.iter() {
            print!("{}", char);
        }
        println!();
    }
}

fn modify<'a>(a: Weak<RefCell<i32>>) {
    let a = &*a.upgrade().unwrap();
    *a.borrow_mut() += 2;
    println!("{}", a.borrow());
}

fn ref_stuff() {
    let a = Rc::new(RefCell::new(2));
    println!("a = {}", (*a).borrow());
    modify(Rc::downgrade(&a));
    println!("a = {}", (*a).borrow());
}

fn test_game() {
    let config = GameConfig {
        dim: Coord { x: 0, y: 0 },
        n_player: 0,
        initial_money: 0.0,
        initial_n_probes: 0,
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
    let mut game = Game::new(config);
    // game.create_player();
    println!("Start run game...");
    game.run();
    println!("End run game.");
}

struct A(i32);

impl Drop for A {
    fn drop(&mut self) {
        println!("Drop {}", &self.0);
    }
}

fn main() {
    let mut a = vec![A(1), A(2), A(3)];
    println!("Will swap");
    let b: Vec<A> = a.drain(..).collect();
    println!("Done swap");
}
