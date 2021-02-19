# Copyright 2021 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import shutil
from functools import partial
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from pandas import DataFrame

from kedro.extras.datasets.pandas import CSVDataSet
from kedro.framework.cli.pipeline import _sync_dirs
from kedro.framework.project import settings
from kedro.framework.session import KedroSession

PACKAGE_NAME = "dummy_package"
PIPELINE_NAME = "my_pipeline"


@pytest.fixture(autouse=True)
def mocked_logging(mocker):
    # Disable logging.config.dictConfig in KedroSession._setup_logging as
    # it changes logging.config and affects other unit tests
    return mocker.patch("logging.config.dictConfig")


@pytest.fixture(autouse=True)
def cleanup_pipelines(fake_repo_path, fake_package_path):
    pipes_path = fake_package_path / "pipelines"
    old_pipelines = {p.name for p in pipes_path.iterdir() if p.is_dir()}
    yield

    # remove created pipeline files after the test
    created_pipelines = {
        p.name for p in pipes_path.iterdir() if p.is_dir() and p.name != "__pycache__"
    }
    created_pipelines -= old_pipelines

    for pipeline in created_pipelines:
        shutil.rmtree(str(pipes_path / pipeline))

        confs = fake_repo_path / settings.CONF_ROOT
        for each in confs.rglob(f"*{pipeline}*"):  # clean all pipeline config files
            if each.is_file():
                each.unlink()

        dirs_to_delete = (
            dirpath
            for pattern in ("parameters", "catalog")
            for dirpath in confs.rglob(pattern)
            if dirpath.is_dir() and not any(dirpath.iterdir())
        )
        for dirpath in dirs_to_delete:
            dirpath.rmdir()

        tests = fake_repo_path / "src" / "tests" / "pipelines" / pipeline
        if tests.is_dir():
            shutil.rmtree(str(tests))


@pytest.fixture(params=["base"])
def make_pipelines(request, fake_repo_path, fake_package_path, mocker):
    source_path = fake_package_path / "pipelines" / PIPELINE_NAME
    tests_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
    conf_path = fake_repo_path / settings.CONF_ROOT / request.param / "parameters"

    for path in (source_path, tests_path, conf_path):
        path.mkdir(parents=True, exist_ok=True)

    (conf_path / f"{PIPELINE_NAME}.yml").touch()
    (tests_path / "test_pipe.py").touch()
    (source_path / "pipe.py").touch()

    yield
    mocker.stopall()
    shutil.rmtree(str(source_path), ignore_errors=True)
    shutil.rmtree(str(tests_path), ignore_errors=True)
    shutil.rmtree(str(conf_path), ignore_errors=True)


@pytest.fixture
def yaml_dump_mock(mocker):
    return mocker.patch("yaml.dump", return_value="Result YAML")


@pytest.fixture
def pipelines_dict():
    pipelines = {
        "de": ["Split Data (split_data)"],
        "ds": [
            "Train Model (train_model)",
            "Predict (predict)",
            "Report Accuracy (report_accuracy)",
        ],
    }
    pipelines["__default__"] = pipelines["de"] + pipelines["ds"]
    return pipelines


@pytest.fixture
def fake_cli_invoke(fake_project_cli, fake_metadata):
    return partial(CliRunner().invoke, fake_project_cli.cli, obj=fake_metadata)


LETTER_ERROR = "It must contain only letters, digits, and/or underscores."
FIRST_CHAR_ERROR = "It must start with a letter or underscore."
TOO_SHORT_ERROR = "It must be at least 2 characters long."


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
class TestPipelineCreateCommand:
    @pytest.mark.parametrize("env", [None, "local"])
    def test_create_pipeline(
        self, fake_repo_path, fake_cli_invoke, env, fake_package_path
    ):  # pylint: disable=too-many-locals
        """Test creation of a pipeline"""
        pipelines_dir = fake_package_path / "pipelines"
        assert pipelines_dir.is_dir()

        assert not (pipelines_dir / PIPELINE_NAME).exists()

        cmd = ["pipeline", "create", PIPELINE_NAME]
        cmd += ["-e", env] if env else []
        result = fake_cli_invoke(cmd)
        assert result.exit_code == 0
        assert (
            f"To be able to run the pipeline `{PIPELINE_NAME}`, you will need "
            f"to add it to `register_pipelines()`" in result.output
        )

        # pipeline
        assert f"Creating the pipeline `{PIPELINE_NAME}`: OK" in result.output
        assert f"Location: `{pipelines_dir / PIPELINE_NAME}`" in result.output
        assert f"Pipeline `{PIPELINE_NAME}` was successfully created." in result.output

        # config
        conf_env = env or "base"
        conf_dir = (fake_repo_path / settings.CONF_ROOT / conf_env).resolve()
        actual_configs = list(conf_dir.glob(f"**/{PIPELINE_NAME}.yml"))
        expected_configs = [conf_dir / "parameters" / f"{PIPELINE_NAME}.yml"]
        assert actual_configs == expected_configs

        # tests
        test_dir = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        expected_files = {"__init__.py", "test_pipeline.py"}
        actual_files = {f.name for f in test_dir.iterdir()}
        assert actual_files == expected_files

    @pytest.mark.parametrize("env", [None, "local"])
    def test_create_pipeline_skip_config(self, fake_repo_path, fake_cli_invoke, env):
        """Test creation of a pipeline with no config"""

        cmd = ["pipeline", "create", "--skip-config", PIPELINE_NAME]
        cmd += ["-e", env] if env else []

        result = fake_cli_invoke(cmd)
        assert result.exit_code == 0
        assert (
            f"To be able to run the pipeline `{PIPELINE_NAME}`, you will need "
            f"to add it to `register_pipelines()`" in result.output
        )
        assert f"Creating the pipeline `{PIPELINE_NAME}`: OK" in result.output
        assert f"Pipeline `{PIPELINE_NAME}` was successfully created." in result.output

        conf_dirs = list((fake_repo_path / settings.CONF_ROOT).rglob(PIPELINE_NAME))
        assert conf_dirs == []  # no configs created for the pipeline

        test_dir = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        assert test_dir.is_dir()

    def test_catalog_and_params(
        self, fake_repo_path, fake_cli_invoke, fake_package_path
    ):
        """Test that catalog and parameter configs generated in pipeline
        sections propagate into the context"""
        pipelines_dir = fake_package_path / "pipelines"
        assert pipelines_dir.is_dir()

        cmd = ["pipeline", "create", PIPELINE_NAME]
        result = fake_cli_invoke(cmd)
        assert result.exit_code == 0

        # write pipeline catalog
        conf_dir = fake_repo_path / settings.CONF_ROOT / "base"
        catalog_dict = {
            "ds_from_pipeline": {
                "type": "pandas.CSVDataSet",
                "filepath": "data/01_raw/iris.csv",
            }
        }
        catalog_file = conf_dir / "catalog" / f"{PIPELINE_NAME}.yml"
        catalog_file.parent.mkdir()
        with catalog_file.open("w") as f:
            yaml.dump(catalog_dict, f)

        # write pipeline parameters
        params_file = conf_dir / "parameters" / f"{PIPELINE_NAME}.yml"
        assert params_file.is_file()
        params_dict = {"params_from_pipeline": {"p1": [1, 2, 3], "p2": None}}
        with params_file.open("w") as f:
            yaml.dump(params_dict, f)

        with KedroSession.create(PACKAGE_NAME) as session:
            ctx = session.load_context()
        assert isinstance(ctx.catalog._data_sets["ds_from_pipeline"], CSVDataSet)
        assert isinstance(ctx.catalog.load("ds_from_pipeline"), DataFrame)
        assert ctx.params["params_from_pipeline"] == params_dict["params_from_pipeline"]

    def test_skip_copy(self, fake_repo_path, fake_cli_invoke):
        """Test skipping the copy of conf and test files if those already exist"""
        # create catalog and parameter files
        for dirname in ("catalog", "parameters"):
            path = (
                fake_repo_path
                / settings.CONF_ROOT
                / "base"
                / dirname
                / f"{PIPELINE_NAME}.yml"
            )
            path.parent.mkdir(exist_ok=True)
            path.touch()

        # create __init__.py in tests
        tests_init = (
            fake_repo_path
            / "src"
            / "tests"
            / "pipelines"
            / PIPELINE_NAME
            / "__init__.py"
        )
        tests_init.parent.mkdir(parents=True)
        tests_init.touch()

        cmd = ["pipeline", "create", PIPELINE_NAME]
        result = fake_cli_invoke(cmd)

        assert result.exit_code == 0
        assert "__init__.py`: SKIPPED" in result.output
        assert f"parameters{os.sep}{PIPELINE_NAME}.yml`: SKIPPED" in result.output
        assert result.output.count("SKIPPED") == 2  # only 2 files skipped

    def test_failed_copy(self, fake_cli_invoke, fake_package_path, mocker):
        """Test the error if copying some file fails"""
        error = Exception("Mock exception")
        mocked_copy = mocker.patch("shutil.copyfile", side_effect=error)

        cmd = ["pipeline", "create", PIPELINE_NAME]
        result = fake_cli_invoke(cmd)
        mocked_copy.assert_called_once()
        assert result.exit_code
        assert result.output.count("FAILED") == 1
        assert result.exception is error

        # but the pipeline is created anyways
        pipelines_dir = fake_package_path / "pipelines"
        assert (pipelines_dir / PIPELINE_NAME / "pipeline.py").is_file()

    def test_no_pipeline_arg_error(self, fake_cli_invoke, fake_package_path):
        """Test the error when no pipeline name was provided"""
        pipelines_dir = fake_package_path / "pipelines"
        assert pipelines_dir.is_dir()

        result = fake_cli_invoke(["pipeline", "create"])
        assert result.exit_code
        assert "Missing argument 'NAME'" in result.output

    @pytest.mark.parametrize(
        "bad_name,error_message",
        [
            ("bad name", LETTER_ERROR),
            ("bad%name", LETTER_ERROR),
            ("1bad", FIRST_CHAR_ERROR),
            ("a", TOO_SHORT_ERROR),
        ],
    )
    def test_bad_pipeline_name(self, fake_cli_invoke, bad_name, error_message):
        """Test error message when bad pipeline name was provided"""
        result = fake_cli_invoke(["pipeline", "create", bad_name])
        assert result.exit_code
        assert error_message in result.output

    def test_duplicate_pipeline_name(self, fake_cli_invoke, fake_package_path):
        """Test error when attempting to create pipelines with duplicate names"""
        pipelines_dir = fake_package_path / "pipelines"
        assert pipelines_dir.is_dir()

        cmd = ["pipeline", "create", PIPELINE_NAME]
        first = fake_cli_invoke(cmd)
        assert first.exit_code == 0

        second = fake_cli_invoke(cmd)
        assert second.exit_code
        assert f"Creating the pipeline `{PIPELINE_NAME}`: FAILED" in second.output
        assert "directory already exists" in second.output

    def test_bad_env(self, fake_cli_invoke):
        """Test error when provided conf environment does not exist"""
        env = "no_such_env"
        cmd = ["pipeline", "create", "-e", env, PIPELINE_NAME]
        result = fake_cli_invoke(cmd)
        assert result.exit_code
        assert f"Unable to locate environment `{env}`" in result.output


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log", "make_pipelines")
class TestPipelineDeleteCommand:
    @pytest.mark.parametrize(
        "make_pipelines,env,expected_conf",
        [("base", None, "base"), ("local", "local", "local")],
        indirect=["make_pipelines"],
    )
    def test_delete_pipeline(
        self, env, expected_conf, fake_repo_path, fake_cli_invoke, fake_package_path
    ):
        options = ["--env", env] if env else []
        result = fake_cli_invoke(["pipeline", "delete", "-y", PIPELINE_NAME, *options])

        source_path = fake_package_path / "pipelines" / PIPELINE_NAME
        tests_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        params_path = (
            fake_repo_path
            / settings.CONF_ROOT
            / expected_conf
            / "parameters"
            / f"{PIPELINE_NAME}.yml"
        )

        assert f"Deleting `{source_path}`: OK" in result.output
        assert f"Deleting `{tests_path}`: OK" in result.output
        assert f"Deleting `{params_path}`: OK" in result.output

        assert f"Pipeline `{PIPELINE_NAME}` was successfully deleted." in result.output
        assert (
            f"If you added the pipeline `{PIPELINE_NAME}` to `register_pipelines()` in "
            f"`{fake_package_path / 'hooks.py'}`, you will need to remove it."
        ) in result.output

        assert not source_path.exists()
        assert not tests_path.exists()
        assert not params_path.exists()

    def test_delete_pipeline_skip(
        self, fake_repo_path, fake_cli_invoke, fake_package_path
    ):
        """Tests that delete pipeline handles missing or already deleted files gracefully"""
        source_path = fake_package_path / "pipelines" / PIPELINE_NAME

        shutil.rmtree(str(source_path))

        result = fake_cli_invoke(["pipeline", "delete", "-y", PIPELINE_NAME])
        tests_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        params_path = (
            fake_repo_path
            / settings.CONF_ROOT
            / "base"
            / "parameters"
            / f"{PIPELINE_NAME}.yml"
        )

        assert f"Deleting `{source_path}`" not in result.output
        assert f"Deleting `{tests_path}`: OK" in result.output
        assert f"Deleting `{params_path}`: OK" in result.output

        assert f"Pipeline `{PIPELINE_NAME}` was successfully deleted." in result.output
        assert (
            f"If you added the pipeline `{PIPELINE_NAME}` to `register_pipelines()` in "
            f"`{fake_package_path / 'hooks.py'}`, you will need to remove it."
        ) in result.output

        assert not source_path.exists()
        assert not tests_path.exists()
        assert not params_path.exists()

    def test_delete_pipeline_fail(self, fake_cli_invoke, fake_package_path, mocker):
        source_path = fake_package_path / "pipelines" / PIPELINE_NAME

        mocker.patch(
            "kedro.framework.cli.pipeline.shutil.rmtree",
            side_effect=PermissionError("permission"),
        )
        result = fake_cli_invoke(["pipeline", "delete", "-y", PIPELINE_NAME])

        assert result.exit_code, result.output
        assert f"Deleting `{source_path}`: FAILED" in result.output

    @pytest.mark.parametrize(
        "bad_name,error_message",
        [
            ("bad name", LETTER_ERROR),
            ("bad%name", LETTER_ERROR),
            ("1bad", FIRST_CHAR_ERROR),
            ("a", TOO_SHORT_ERROR),
        ],
    )
    def test_bad_pipeline_name(self, fake_cli_invoke, bad_name, error_message):
        """Test error message when bad pipeline name was provided."""
        result = fake_cli_invoke(["pipeline", "delete", "-y", bad_name])
        assert result.exit_code
        assert error_message in result.output

    def test_pipeline_not_found(self, fake_cli_invoke):
        result = fake_cli_invoke(["pipeline", "delete", "-y", "non_existent"])
        assert result.exit_code
        assert "Pipeline `non_existent` not found." in result.output

    def test_bad_env(self, fake_cli_invoke):
        """Test error when provided conf environment does not exist."""
        result = fake_cli_invoke(
            ["pipeline", "delete", "-y", "-e", "invalid_env", PIPELINE_NAME]
        )
        assert result.exit_code
        assert "Unable to locate environment `invalid_env`" in result.output

    @pytest.mark.parametrize("input_", ["n", "N", "random"])
    def test_pipeline_delete_confirmation(
        self, fake_repo_path, fake_cli_invoke, fake_package_path, input_
    ):
        """Test that user confirmation of deletion works"""
        result = fake_cli_invoke(["pipeline", "delete", PIPELINE_NAME], input=input_)

        source_path = fake_package_path / "pipelines" / PIPELINE_NAME
        tests_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        params_path = (
            fake_repo_path
            / settings.CONF_ROOT
            / "base"
            / "parameters"
            / f"{PIPELINE_NAME}.yml"
        )

        assert "The following paths will be removed:" in result.output
        assert str(source_path) in result.output
        assert str(tests_path) in result.output
        assert str(params_path) in result.output

        assert (
            f"Are you sure you want to delete pipeline `{PIPELINE_NAME}`"
            in result.output
        )
        assert "Deletion aborted!" in result.output

        assert source_path.is_dir()
        assert tests_path.is_dir()
        assert params_path.is_file()

    @pytest.mark.parametrize("input_", ["n", "N", "random"])
    def test_pipeline_delete_confirmation_skip(
        self, fake_repo_path, fake_cli_invoke, fake_package_path, input_
    ):
        """Test that user confirmation of deletion works when
        some of the files are missing or already deleted
        """

        source_path = fake_package_path / "pipelines" / PIPELINE_NAME
        shutil.rmtree(str(source_path))
        result = fake_cli_invoke(["pipeline", "delete", PIPELINE_NAME], input=input_)

        tests_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        params_path = (
            fake_repo_path
            / settings.CONF_ROOT
            / "base"
            / "parameters"
            / f"{PIPELINE_NAME}.yml"
        )

        assert "The following paths will be removed:" in result.output
        assert str(source_path) not in result.output
        assert str(tests_path) in result.output
        assert str(params_path) in result.output

        assert (
            f"Are you sure you want to delete pipeline `{PIPELINE_NAME}`"
            in result.output
        )
        assert "Deletion aborted!" in result.output

        assert tests_path.is_dir()
        assert params_path.is_file()


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
def test_list_pipelines(fake_cli_invoke, yaml_dump_mock, pipelines_dict):
    result = fake_cli_invoke(["pipeline", "list"])

    assert not result.exit_code
    yaml_dump_mock.assert_called_once_with(sorted(pipelines_dict.keys()))


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
class TestPipelineDescribeCommand:
    @pytest.mark.parametrize("pipeline_name", ["de", "ds", "__default__"])
    def test_describe_pipeline(
        self, fake_cli_invoke, yaml_dump_mock, pipeline_name, pipelines_dict
    ):
        result = fake_cli_invoke(["pipeline", "describe", pipeline_name])

        assert not result.exit_code
        expected_dict = {"Nodes": pipelines_dict[pipeline_name]}
        yaml_dump_mock.assert_called_once_with(expected_dict)

    def test_not_found_pipeline(self, fake_cli_invoke):
        result = fake_cli_invoke(["pipeline", "describe", "missing"])

        assert result.exit_code
        expected_output = (
            "Error: `missing` pipeline not found. Existing pipelines: "
            "[__default__, de, ds]\n"
        )
        assert expected_output in result.output

    def test_bad_env(self, fake_cli_invoke):
        """Test error when provided conf environment does not exist"""
        env = "no_such_env"
        cmd = ["pipeline", "describe", "-e", env, PIPELINE_NAME]
        result = fake_cli_invoke(cmd)
        assert result.exit_code
        assert "Unable to instantiate Kedro session" in result.output


class TestSyncDirs:
    @pytest.fixture(autouse=True)
    def mock_click(self, mocker):
        mocker.patch("click.secho")

    @pytest.fixture
    def source(self, tmp_path) -> Path:
        source_dir = Path(tmp_path) / "source"
        source_dir.mkdir()
        (source_dir / "existing").mkdir()
        (source_dir / "existing" / "source_file").touch()
        (source_dir / "existing" / "common").write_text("source")
        (source_dir / "new").mkdir()
        (source_dir / "new" / "source_file").touch()
        return source_dir

    def test_sync_target_exists(self, source, tmp_path):
        """Test _sync_dirs utility function if target exists."""
        target = Path(tmp_path) / "target"
        target.mkdir()
        (target / "existing").mkdir()
        (target / "existing" / "target_file").touch()
        (target / "existing" / "common").write_text("target")

        _sync_dirs(source, target)

        assert (source / "existing" / "source_file").is_file()
        assert (source / "existing" / "common").read_text() == "source"
        assert not (source / "existing" / "target_file").exists()
        assert (source / "new" / "source_file").is_file()

        assert (target / "existing" / "source_file").is_file()
        assert (target / "existing" / "common").read_text() == "target"
        assert (target / "existing" / "target_file").exists()
        assert (target / "new" / "source_file").is_file()

    def test_sync_no_target(self, source, tmp_path):
        """Test _sync_dirs utility function if target doesn't exist."""
        target = Path(tmp_path) / "target"

        _sync_dirs(source, target)

        assert (source / "existing" / "source_file").is_file()
        assert (source / "existing" / "common").read_text() == "source"
        assert not (source / "existing" / "target_file").exists()
        assert (source / "new" / "source_file").is_file()

        assert (target / "existing" / "source_file").is_file()
        assert (target / "existing" / "common").read_text() == "source"
        assert not (target / "existing" / "target_file").exists()
        assert (target / "new" / "source_file").is_file()
