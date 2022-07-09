mod game;

use game::iter_vortex;
use game::square;
use game::square_without_origin;
use game::Coord;

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

fn main() {
    let origin = Coord::new(5, 5);
    let mut coords = square_without_origin(&origin, 3);

    display(&origin, &coords);
}
