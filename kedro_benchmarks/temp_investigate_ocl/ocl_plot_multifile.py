import fsspec
import yaml
import random
import time
from pathlib import Path
import matplotlib.pyplot as plt
from kedro.config import OmegaConfigLoader

# Set up paths
base_path = Path.cwd() / "conf" / "base"


# Define the custom resolver function
def random_choice(*args):
    return random.choice(args)


def generate_globals():
    """Generates a global config file with interpolation and custom resolvers."""
    globals_data = {
        "project_name": "Dummy Kedro Project",
        "compression_type": "${random_choice: gzip, bz2, xz, None}",
        "separator": "${random_choice: ,, \t, |}",
        "random_seed": 42,
    }
    with open(base_path / "globals.yml", "w") as f:
        yaml.dump(globals_data, f)


def generate_multiple_catalog_files(pattern, num_files, num_entries):
    """Generates multiple config files following a given pattern."""
    for i in range(1, num_files + 1):
        catalog = {
            f"dataset_{i}_{j}": {
                "type": "pandas.CSVDataSet",
                "filepath": f"data/dataset_{i}_{j}.csv",
            }
            for j in range(num_entries)
        }
        with open(base_path / f"{pattern}_{i}.yml", "w") as f:
            yaml.dump(catalog, f)


def load_and_time_config():
    """Load config files that match a pattern and measure time taken."""
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


def run_scaling_tests():
    """Run scaling tests for different scenarios."""
    results = []

    # Test multiple config files following a given pattern
    for num_files in [10, 100, 500, 1000, 2000]:
        generate_multiple_catalog_files(
            "catalog", num_files, 10
        )  # Each file has 10 entries
        load_time, config_len = load_and_time_config()
        results.append(
            (
                f"Conf source with {num_files} catalog files",
                num_files,
                load_time,
                config_len,
            )
        )

    for scenario, entries, load_time, config_len in results:
        print(f"{scenario:<30} {entries:<10} {load_time:<15.5f} {config_len}")

    return results


def plot_results(results):
    """Plots the scaling test results as a scatter plot."""
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

    plt.title("OmegaConfigLoader Scaling Properties with multiple catalog files")
    plt.xlabel("Number of Entries")
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
