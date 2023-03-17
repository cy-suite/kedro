# Set up the spaceflights project

This section shows how to create a new project (with `kedro new` using the [Kedro spaceflights starter](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights)) and install project dependencies (with `pip install -r src/requirements.txt`).

## Create a new project

[Set up Kedro](../get_started/install.md) if you have not already done so.

```{important}
We recommend that you use the same version of Kedro that was most recently used to test this tutorial (0.18.6). To check the version installed, type `kedro -V` in your terminal window.
```

In your terminal, navigate to the folder you want to store the project. Type the following to generate the project from the [Kedro spaceflights starter](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights). The project will be populated with a complete set of working example code:

```bash
kedro new --starter=spaceflights
```

When prompted for a project name, you should accept the default choice (`Spaceflights`) as the rest of this tutorial assumes that project name.

When Kedro has created the project, navigate to the [project root directory](./spaceflights_tutorial.md#project-root-directory):

```bash
cd spaceflights
```

## Install project dependencies

Kedro projects have a `requirements.txt` file to specify their dependencies and enable sharable projects by ensuring consistency across Python packages and versions.

The spaceflights project dependencies are stored in `src/requirements.txt`(you may find that the versions differ slightly depending on the version of Kedro):

```text
# code quality packages
black==22.0
flake8>=3.7.9, <5.0
ipython>=7.31.1, <8.0
isort~=5.0
nbstripout~=0.4

# notebook tooling
jupyter~=1.0
jupyterlab~=3.0
jupyterlab_server>=2.11.1, <2.16.0

# Pytest + useful extensions
pytest-cov~=3.0
pytest-mock>=1.7.1, <2.0
pytest~=7.2

# Kedro dependencies and datasets to work with different data formats (including CSV, Excel, and Parquet)
kedro~=0.18.6
kedro-datasets[pandas.CSVDataSet, pandas.ExcelDataSet, pandas.ParquetDataSet]~=1.0.0
kedro-telemetry~=0.2.0
kedro-viz~=5.0 # Visualise pipelines

# For modelling in the data science pipeline
scikit-learn~=1.0
```

### Install the dependencies

To install all the project-specific dependencies, run the following from the project root directory:

```bash
pip install -r src/requirements.txt
```

[You can learn more about dependencies in the project setup documentation](../kedro_project_setup/dependencies.md).

## Optional: configuration and logging

In your Kedro projects, you may want to store credentials such as usernames and passwords if they are needed for specific data sources.

To do this, add them to `conf/local/credentials.yml` (some examples are included in that file for illustration).

You can find additional information in the [advanced documentation on configuration](../kedro_project_setup/configuration.md).

You might also want to [set up logging](../logging/logging.md) at this stage of the workflow, but we do not use it in this tutorial.
