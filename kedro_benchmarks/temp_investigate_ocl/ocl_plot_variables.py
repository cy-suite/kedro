import fsspec
import yaml
import random
from pathlib import Path
import time
import matplotlib.pyplot as plt
from kedro.config import OmegaConfigLoader

# Set up paths
base_path = Path.cwd() / "conf" / "base"
base_path.mkdir(parents=True, exist_ok=True)


# Custom resolver function for interpolations
def random_choice(*args):
    return random.choice(args)


# Generate a global config with common variables for interpolation
def generate_globals():
    globals_data = {
        "compression_type": "${random_choice: gzip, bz2, xz, None}",
        "separator": "${random_choice: ,, \t, |}",
        "random_seed": 42,
    }
    with open(base_path / "globals.yml", "w") as f:
        yaml.dump(globals_data, f)


# Generate a catalog with variable interpolations
def generate_variable_interpolation_catalog(start_idx, num_vars):
    """Creates a catalog where each dataset uses interpolated variables."""
    catalog = {}
    for i in range(start_idx, num_vars + start_idx):
        dataset_name = f"interpolated_dataset_{i}"
        catalog[dataset_name] = {
            "type": "pandas.CSVDataSet",
            "filepath": f"data/{dataset_name}.csv",
            "save_args": {
                "index": False,
                "compression": "${globals:compression_type}",  # Interpolated compression type
            },
            "load_args": {
                "sep": "${globals:separator}",  # Interpolated separator
                "encoding": "${random_choice: utf-8, iso-8859-1, utf-16}",  # Random choice encoding
            },
        }

    # Write catalog to YAML file
    catalog_path = base_path / f"catalog_datasets_with_variables.yml"
    with open(catalog_path, "w") as f:
        yaml.dump(catalog, f)
    return catalog_path


# Measure the load time for OmegaConfigLoader
def load_and_time_catalog(catalog_path):
    loader = OmegaConfigLoader(
        conf_source="conf",
        base_env="base",
        default_run_env="base",
        custom_resolvers={"random_choice": random_choice},
    )
    start_time = time.time()
    config = loader["catalog"]
    load_time = time.time() - start_time
    return load_time, len(config)


# Run scaling tests for various configurations
def run_scaling_tests():
    results = []

    # Generate and load catalogs with increasing variable interpolations
    start_idx = 0
    for num_vars in [10, 100, 500, 1000, 2000, 5000, 8000, 10000]:
        catalog_path = generate_variable_interpolation_catalog(start_idx, num_vars)
        load_time, config_len = load_and_time_catalog(catalog_path)
        results.append(
            (
                f"Catalog with {num_vars} datasets with variable interpolation",
                num_vars,
                load_time,
                config_len,
            )
        )
        start_idx += num_vars

    for scenario, entries, load_time, config_len in results:
        print(f"{scenario:<30} {entries:<10} {load_time:<15.5f} {config_len}")

    return results


# Plot the results
def plot_results(results):
    plt.figure(figsize=(10, 6))

    # Group results by scenario
    for scenario in set(s[0] for s in results):
        scenario_results = [
            (entries, load_time)
            for s, entries, load_time, _ in results
            if s == scenario
        ]
        entries, load_times = zip(*scenario_results)
        plt.scatter(entries, load_times, label=scenario)

    plt.title("OmegaConfigLoader Scaling Properties with Variable Interpolations")
    plt.xlabel("Number of Datasets")
    plt.ylabel("Load Time (s)")
    plt.legend()
    plt.grid(True)
    plt.show()


if __name__ == "__main__":
    # Clean up if conf is present
    fs = fsspec.filesystem("file")

    if fs.exists(base_path):
        fs.rm(base_path, recursive=True)

    # fresh conf
    base_path.mkdir(parents=True, exist_ok=True)

    # Generate globals file
    generate_globals()

    # Run tests and plot
    results = run_scaling_tests()
    plot_results(results)
