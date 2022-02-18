
# Micro-packaging

Micro-packaging allows users to share Kedro pipelines across codebases, organisations and beyond.

## Package a modular pipeline

You can package a modular pipeline by executing: `kedro pipeline package pipelines.<pipeline_name>`


* This will generate a new [tar](https://docs.python.org/3/distutils/sourcedist.html) file for this pipeline.
* By default, the tar file will be saved into `dist` directory inside your project.
* You can customise the target with the `--destination` (`-d`) option.

When you package your modular pipeline, Kedro will also automatically package files from 3 locations:

```text
├── conf
│   └── base
│       └── parameters
│           └── {{pipeline_name*}}  <-- All parameter file(s)
└── src
    ├── my_project
    │   ├── __init__.py
    │   └── pipelines
    │       └── {{pipeline_name}}    <-- Pipeline folder
    └── tests
        ├── __init__.py
        └── pipelines
            └── {{pipeline_name}}    <-- Pipeline tests
```

Kedro will also include any requirements found in `src/<python_package>/pipelines/<pipeline_name>/requirements.txt` in the modular pipeline tar file. These requirements will later be taken into account when pulling a pipeline via `kedro pipeline pull`.

```eval_rst
.. note::  Kedro will not package the catalog config files even if those are present in ``conf/<env>/catalog/<pipeline_name>.yml``.
```

If you plan to publish your packaged modular pipeline to some Python package repository like [PyPI](https://pypi.org/), you need to make sure that your modular pipeline name doesn't clash with any of the existing packages in that repository. However, there is no need to rename any of your source files if that is the case. Simply alias your package with a new name by running `kedro pipeline package --alias <new_package_name> <pipeline_name>`.

In addition to [PyPI](https://pypi.org/), you can also share the packaged tar file directly, or via a cloud storage such as AWS S3.

## Package multiple modular pipelines

To package multiple modular pipelines in bulk, run `kedro pipeline package --all`. This will package all pipelines specified in the `tool.kedro.package` manifest section of the project's `pyproject.toml` file:

```toml
[tool.kedro.pipeline.package]
first_package = {alias = "aliased_package", destination = "somewhere/else", env = "uat"}
"utils.cleaning" = {}
```

* The keys (`first_package`, `utils.cleaning`) are the Python module paths of the micro-packages, relative to your project's package name.
* The values are the options accepted by the `kedro pipeline package <pipeline_name>` CLI command.

```eval_rst
.. note::  Make sure `destination` is specified as a POSIX path even when working on a Windows machine.
```

```eval_rst
.. note::  The examples above apply to any generic Python package, modular pipelines fall under this category and can be easily addressed via the ``pipelines.pipeline_name`` syntax.
```


## Pull a modular pipeline

You can pull a modular pipeline from a tar file by executing `kedro pipeline pull <package_name>`.

* The `<package_name>` must either be a package name on PyPI or a path to the tar file.
* Kedro will unpack the tar file, and install the files in following locations in your Kedro project:
  * All the modular pipeline code in `src/<python_package>/<micropackage_name>/`
  * Configuration files in `conf/<env>/parameters/<pipeline_name>.yml`, where `<env>` defaults to `base`.
  * To place parameters from a different config environment, run `kedro pipeline pull <pipeline_name> --env <env_name>`
  * Pipeline unit tests in `src/tests/<micropackage_name>`
* Kedro will also parse any requirements packaged with the modular pipeline and add them to project level `requirements.in`.
* It is advised to do `kedro build-reqs` to compile the updated list of requirements after pulling a modular pipeline.

```eval_rst
.. note::  If a modular pipeline has embedded requirements and a project ``requirements.in`` file does not already exist, it will be generated based on the project ``requirements.txt`` before appending the modular pipeline requirements.
```

You can pull a modular pipeline from different locations, including local storage, PyPI and the cloud:

```eval_rst
+--------------------------------+-----------------------------------------------------------------------------------------+
| Operation                      | Command                                                                                 |
+================================+=========================================================================================+
| Pulling from a local directory | ``kedro pipeline pull <project-root>/src/dist/<pipeline_name>-0.1-py3-none-any.tar.gz`` |
+--------------------------------+-----------------------------------------------------------------------------------------+
| Pull from cloud storage        | ``kedro pipeline pull s3://my_bucket/<pipeline_name>-0.1-py3-none-any.tar.gz``          |
+--------------------------------+-----------------------------------------------------------------------------------------+
| Pull from PyPI like endpoint   | ``kedro pipeline pull <pypi-package-name>``                                             |
+--------------------------------+-----------------------------------------------------------------------------------------+
```

### Providing `fsspec` arguments

* If you are pulling the pipeline from a location that isn't PyPI, Kedro uses [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to locate and pull down your pipeline.
* You can use the `--fs-args` option to point to a YAML that contains the required configuration.

```bash
kedro pipeline pull https://<url-to-pipeline.tar.gz> --fs-args pipeline_pull_args.yml
```

```yaml
# `pipeline_pull_args.yml`
client_kwargs:
  headers:
    Authorization: token <token>
```

## Pull multiple modular pipelines

* To pull multiple modular pipelines in bulk, run `kedro pipeline pull --all`.
* This will pull and unpack all pipelines specified in the `tool.kedro.pipeline.pull` manifest section of the project's `pyproject.toml` file:

```toml
[tool.kedro.pipeline.pull]
"src/dist/first-pipeline-0.1-py3-none-any.tar.gz" = {}
"https://www.url.to/second-pipeline.tar.gz" = {alias = "aliased_pipeline", destination = "pipelines", fs-args = "pipeline_pull_args.yml"}
```

* The keys (tar references in this case) are the package paths
* The values are the options that `kedro pipeline pull <package_path>` CLI command accepts.

```eval_rst
.. attention:: As per the `TOML specification <https://toml.io/en/v1.0.0#keys>`_, a key that contains any character outside ``A-Za-z0-9_-`` must be quoted.
```
