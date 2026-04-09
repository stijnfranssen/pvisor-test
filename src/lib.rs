/// Rust library for rustic spectra interface for pvisor
/// Author: Stijn Franssen-van Rijsingen
/// E-mail: franssen@nrg.eu
/// Date: April 2025
use pyo3::prelude::*; // For maturin/python coupling
use std::fs::File; // For opening the spectra file
use std::io::{BufRead, BufReader}; // for the buffer reader

// use std::time::Instant; // For timing

// Reading the file line by line:
// https://stackoverflow.com/questions/75353821/what-is-the-most-efficient-way-to-read-the-first-line-of-a-file-separately-to-th

// Boilerplate for coupling Rust🦀 & Python🐍 via maturin
#[pymodule]
fn pvisor(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(rust_read_spectra, m)?)?;
    Ok(())
}

/// # Reads in the spectra file.
///
/// 1. First opens the
/// 1. Gets the number of parameters
/// 1. Gets the parameter names
/// 1. Loops over the rest of the file
///
/// ## SPECTRA plot file shape
/// The SPECTRA data is stored in blocks per timestep with a max width of 10 columns.
/// There are 2 versions of the SPECTRA plot file:
/// 1. 6 digits of percision, n_digits=12
/// 1. 9 digits of precision, n_digits=15
///
/// Parameters
/// ----------
/// file_path: &str
///     the file path
/// n_digits: usize
///     the width of a datafield
///
/// Returns
/// -------
/// all_data: Vec<Vec<f32>>
///     the data stored in a vector of columns/vectors.
///
#[pyfunction]
fn rust_read_spectra(file_path: &str, n_digits: usize) -> (Vec<f32>, Vec<Vec<f32>>) {
    // Open the file and make an iterator out of the lines
    // let now = Instant::now();
    let plot_file = File::open(file_path).expect("Plot file not found!");
    let plot_file_reader = BufReader::new(plot_file);
    let mut plot_file_lines = plot_file_reader
        .lines()
        .map(|line| line.expect("Failed to read line!"));

    // Get the number of parameters out
    let n_params = _get_n_params(plot_file_lines.next().expect("Failed ot read line!"));

    // Get the parameter names out
    let _param_names = _get_param_names(&mut plot_file_lines, n_params);

    // Initialize the data structure
    let mut all_data: Vec<Vec<f32>> = vec![Vec::new(); n_params - 1];
    let mut time: Vec<f32> = vec![];

    // Loop over the data lines until the end of the file is reached.
    loop {
        // Match statement to break at the end of the file
        let mut data_line = match plot_file_lines.next() {
            Some(line) => line,
            None => {
                break;
            }
        };

        // Reading in the actual data in blocks of 10
        for ii in 0..n_params {
            if ii % 10 == 0 {
                // Read in the next line if we have read 10 parameters
                data_line = plot_file_lines.next().expect("Error reading line");
            }

            // Extract the data point from the line
            let number_str = &data_line[ii % 10 * n_digits..(ii % 10 + 1) * n_digits];

            // Convert the str to float and Append/push to the correct column/vector
            if ii == 0 {
                time.push(
                    number_str
                        .trim()
                        .parse::<f32>()
                        .expect("Could not parse line"),
                )
            } else {
                all_data[ii - 1].push(
                    number_str
                        .trim()
                        .parse::<f32>()
                        .expect("Could not parse line"),
                )
            }
        }
    }
    // let elapsed = now.elapsed();
    // println!("🦀 Elapsed in rust library 🦀: {:.0?}", elapsed);

    return (time, all_data);
}

/// The first line of SPECTRA plot file contains the total number of variables.
/// And is usually like: " NPLT  =   6160"
///
/// Parameters
/// ----------
/// line: String
///     the first line of the plot file
///
/// Returns
/// -------
/// n_params: usize
///     the number of variables

// Initialize the amount of parameters
fn _get_n_params(line: String) -> usize {
    let n_params = 0;

    // Split the line
    let parts: Vec<&str> = line.split_whitespace().collect();

    // Extract the number of parameters.
    // Panic if the number cannot be found.
    if let Some(n_params) = parts.last() {
        match n_params.parse::<usize>() {
            Ok(num) => return num,
            Err(_) => {
                println!("Error: '{}' is not a valid number of parameters!", n_params);
                panic!(
                    "The first line should end with the number of parameters:\n'{}'",
                    line
                );
            }
        }
    }
    return n_params;
}

/// Get the parameter names from the SPECTRA plot file.
///
/// Figure out if we want the python or the rust implementation
/// WARNING: Variables still have the units attached!
///
/// Parameters:
/// plot_file_lines: Iterator of Strings
///     the iterator over the file
/// n_params: usize
///     the total number of parameters
///
/// Returns:
/// --------
/// param_names: Vec<String>
///     the list of paramter names.
///
fn _get_param_names<T: Iterator<Item = String>>(
    plot_file_lines: &mut T,
    n_params: usize,
) -> Vec<String> {
    // println!("Warning: Variables still have the units attached!");
    // Initialize the list of paramters
    let mut param_names = Vec::new();

    // Read n_param lines
    for _ii in 0..n_params {
        let line = plot_file_lines.next().expect("Failed to read line!");

        // Split the line
        let parts: Vec<&str> = line.split_whitespace().collect();

        // Push the name to the vector
        if let Some(param_name) = parts.last() {
            param_names.push(param_name.to_string())
        }
    }
    return param_names;
}
