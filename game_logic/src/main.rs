mod game;

use game::*;

fn display(origin: &Coord, coords: &Vec<Coord>) {
    let mut chars = vec![vec![' '; 30]; 30];

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
fn test_game() {
    let config = GameConfig {
        dim: Coord { x: 10, y: 10 },
        n_player: 3,
        initial_money: 20.0,
        initial_n_probes: 3,
        base_income: 0.0,
        building_occupation_min: 0,
        factory_price: 0.0,
        factory_expansion_size: 4,
        factory_max_probe: 0,
        factory_build_probe_delay: 0.0,
        max_occupation: 0,
        probe_speed: 0.0,
        probe_hp: 0,
        probe_price: 0.0,
        probe_claim_delay: 0.0,
        factory_maintenance_costs: 0.0,
        probe_maintenance_costs: 0.0,
        turret_price: 0.0,
        turret_damage: 0,
        turret_fire_delay: 0.0,
        turret_scope: 0.0,
        turret_maintenance_costs: 0.0,
        income_rate: 0.0,
        deprecate_rate: 0.0,
        tech_probe_explosion_intensity_increase: 0,
        tech_probe_explosion_intensity_price: 0.0,
        tech_probe_claim_intensity_increase: 0,
        tech_probe_claim_intensity_price: 0.0,
        tech_factory_build_delay_decrease: 0.0,
        tech_factory_build_delay_price: 0.0,
        tech_factory_probe_price_decrease: 0.0,
        tech_factory_probe_price_price: 0.0,
        tech_factory_max_probe_increase: 0,
        tech_factory_max_probe_price: 0.0,
        tech_turret_scope_increase: 0.0,
        tech_turret_scope_price: 0.0,
        tech_turret_fire_delay_decrease: 0.0,
        tech_turret_fire_delay_price: 0.0,
        tech_turret_maintenance_costs_decrease: 0.0,
        tech_turret_maintenance_costs_price: 0.0,
        tech_probe_hp_increase: 0,
        tech_probe_hp_price: 0.0,
        probe_claim_intensity: 0,
        probe_explosion_intensity: 0,
    };
    let player_ids = vec![1, 2, 3];
    let mut game = Game::new(player_ids, config);

    println!("Start run game...");
    let state = game.run(1.0 / 60.0);
    println!("{:?}", state);
    println!("End run game.");
}

fn main() {
    let origin = Coord::new(18, 10);
    let mut coords = Vec::new();
    let mut i = 0;
    for coord in game::iter_vortex(&origin) {
        coords.push(coord);
        i += 1;
        if i == 50 {
            break;
        }
    }
    display(&origin, &coords);
}
