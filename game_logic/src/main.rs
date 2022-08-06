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
        dim: Coord { x: 10, y: 10 },
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
        turret_fire_delay: 0.0,
        turret_scope: 0.0,
        turret_maintenance_costs: 0.0,
        income_rate: 0.0,
        deprecate_rate: 0.0,
    };
    let player_ids = vec![1, 2, 3];
    let mut game = Game::new(player_ids, config);

    println!("Start run game...");
    let state = game.run();
    println!("{:?}", state);
    println!("End run game.");
}

fn main() {
    test_game();
}
