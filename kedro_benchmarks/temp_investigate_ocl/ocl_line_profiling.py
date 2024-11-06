import line_profiler
import yaml
import random
from pathlib import Path
from kedro.config import OmegaConfigLoader

# Define paths for the config files
base_path = Path.cwd() / "conf" / "base"
globals_path = base_path / "globals.yml"

# Ensure directories exist
base_path.mkdir(parents=True, exist_ok=True)


# Define the custom resolver function
def random_choice(*args):
    return random.choice(args)


def generate_large_catalog(num_entries=1000):
    """Generates a large catalog file with dummy datasets and interpolations."""
    catalog = {}
    for i in range(num_entries):
        dataset_name = f"dummy_dataset_{i}"
        catalog[dataset_name] = {
            "type": "pandas.CSVDataSet",
            "filepath": f"data/{dataset_name}.csv",
            "save_args": {
                "index": False,
                # Use interpolation to reference the global setting
                "compression": "${globals:compression_type}",
            },
            "load_args": {
                "sep": "${globals:separator}",
                # Use custom resolver to select random encoding
                "encoding": "${random_choice: utf-8, iso-8859-1, utf-16}",
            },
        }

    # Write catalog to YAML
    with open(base_path / "catalog.yml", "w") as f:
        yaml.dump(catalog, f)


def generate_large_parameters(num_entries=1000):
    """Generates a large parameters file with dummy parameters and interpolation."""
    parameters = {"defaults": {"random_seed": "${globals:random_seed}"}}
    for i in range(num_entries):
        param_name = f"param_{i}"
        parameters[param_name] = random.randint(1, 1000)

    # Write parameters to YAML
    with open(base_path / "parameters.yml", "w") as f:
        yaml.dump(parameters, f)


def generate_globals():
    """Generates a global config file with interpolations and custom resolvers."""
    globals_data = {
        "project_name": "Dummy Kedro Project",
        "env": "base",
        "compression_type": "${random_choice: gzip, bz2, xz, None}",
        "separator": "${random_choice: ,, \t, |}",
        "random_seed": 42,
        "logging": {"level": "DEBUG", "handlers": ["console", "file"]},
    }

    # Write globals to YAML
    with open(globals_path, "w") as f:
        yaml.dump(globals_data, f)


generate_large_catalog()
generate_large_parameters()
generate_globals()


@line_profiler.profile
def get_loader():
    loader = OmegaConfigLoader(
        conf_source="conf",
        base_env="base",
        default_run_env="base",
        custom_resolvers={"random_choice": random_choice},
    )
    return loader


@line_profiler.profile
def get_catalog(loader):
    return loader["catalog"]


@line_profiler.profile
def get_parameters(loader):
    return loader["parameters"]


@line_profiler.profile
def get_globals(loader):
    return loader["globals"]


if __name__ == "__main__":
    # Run functions to create dummy files

    ocl = get_loader()
    get_globals(ocl)
    get_catalog(ocl)
    get_parameters(ocl)
