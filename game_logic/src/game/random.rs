use rand::{prelude::SliceRandom, thread_rng};

pub fn shuffle_vec<T>(vec: &mut Vec<T>) {
    vec.shuffle(&mut thread_rng());
}
