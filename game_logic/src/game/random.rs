use rand::{prelude::SliceRandom, thread_rng, Rng};

pub fn shuffle_vec<T>(vec: &mut Vec<T>) {
    vec.shuffle(&mut thread_rng());
}

pub fn random() -> f64 {
    thread_rng().gen()
}
