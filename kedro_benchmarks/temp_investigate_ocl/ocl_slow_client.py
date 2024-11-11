from pathlib import Path
import time
import matplotlib.pyplot as plt
from kedro.config import OmegaConfigLoader

# Set up paths
base_path = Path.cwd() / "conf" / "base"
base_path.mkdir(parents=True, exist_ok=True)

# Measure the load time for OmegaConfigLoader
def load_and_time_catalog():
    loader = OmegaConfigLoader(
        conf_source="conf",
        base_env="base",
        default_run_env="base",
    )
    start_time = time.time()
    config = loader["catalog"]
    load_time = time.time() - start_time
    return load_time, len(config)


if __name__ == "__main__":
    # Run tests and plot
    results = load_and_time_catalog()

    print(results)