import logging
import re
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
from kedro_datasets.pandas import CSVDataset, ParquetDataset
from pandas.testing import assert_frame_equal

from kedro.io import (
    DatasetAlreadyExistsError,
    DatasetError,
    DatasetNotFoundError,
    KedroDataCatalog,
    LambdaDataset,
    MemoryDataset,
)
from kedro.io.core import (
    _DEFAULT_PACKAGES,
    VERSION_FORMAT,
    generate_timestamp,
    parse_dataset_definition,
)


@pytest.fixture
def data_catalog(dataset):
    return KedroDataCatalog(datasets={"test": dataset})


@pytest.fixture
def memory_catalog():
    ds1 = MemoryDataset({"data": 42})
    ds2 = MemoryDataset([1, 2, 3, 4, 5])
    return KedroDataCatalog({"ds1": ds1, "ds2": ds2})


@pytest.fixture
def conflicting_feed_dict():
    return {"ds1": 0, "ds3": 1}


@pytest.fixture
def multi_catalog():
    csv = CSVDataset(filepath="abc.csv")
    parq = ParquetDataset(filepath="xyz.parq")
    return KedroDataCatalog({"abc": csv, "xyz": parq})


@pytest.fixture
def data_catalog_from_config(correct_config):
    return KedroDataCatalog.from_config(**correct_config)


class TestKedroDataCatalog:
    def test_save_and_load(self, data_catalog, dummy_dataframe):
        """Test saving and reloading the dataset"""
        data_catalog.save("test", dummy_dataframe)
        reloaded_df = data_catalog.load("test")

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_add_save_and_load(self, dataset, dummy_dataframe):
        """Test adding and then saving and reloading the dataset"""
        catalog = KedroDataCatalog(datasets={})
        catalog.add("test", dataset)
        catalog.save("test", dummy_dataframe)
        reloaded_df = catalog.load("test")

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_load_error(self, data_catalog):
        """Check the error when attempting to load a dataset
        from nonexistent source"""
        pattern = r"Failed while loading data from data set CSVDataset"
        with pytest.raises(DatasetError, match=pattern):
            data_catalog.load("test")

    def test_add_dataset_twice(self, data_catalog, dataset):
        """Check the error when attempting to add the dataset twice"""
        pattern = r"Dataset 'test' has already been registered"
        with pytest.raises(DatasetAlreadyExistsError, match=pattern):
            data_catalog.add("test", dataset)

    def test_load_from_unregistered(self):
        """Check the error when attempting to load unregistered dataset"""
        catalog = KedroDataCatalog(datasets={})
        pattern = r"Dataset 'test' not found in the catalog"
        with pytest.raises(DatasetNotFoundError, match=pattern):
            catalog.load("test")

    def test_save_to_unregistered(self, dummy_dataframe):
        """Check the error when attempting to save to unregistered dataset"""
        catalog = KedroDataCatalog(datasets={})
        pattern = r"Dataset 'test' not found in the catalog"
        with pytest.raises(DatasetNotFoundError, match=pattern):
            catalog.save("test", dummy_dataframe)

    def test_feed_dict(self, memory_catalog, conflicting_feed_dict):
        """Test feed dict overriding some of the datasets"""
        assert "data" in memory_catalog.load("ds1")
        memory_catalog.add_feed_dict(conflicting_feed_dict, replace=True)
        assert memory_catalog.load("ds1") == 0
        assert isinstance(memory_catalog.load("ds2"), list)
        assert memory_catalog.load("ds3") == 1

    def test_exists(self, data_catalog, dummy_dataframe):
        """Test `exists` method invocation"""
        assert not data_catalog.exists("test")
        data_catalog.save("test", dummy_dataframe)
        assert data_catalog.exists("test")

    def test_exists_not_implemented(self, caplog):
        """Test calling `exists` on the dataset, which didn't implement it"""
        catalog = KedroDataCatalog(datasets={"test": LambdaDataset(None, None)})
        result = catalog.exists("test")

        log_record = caplog.records[0]
        assert log_record.levelname == "WARNING"
        assert (
            "'exists()' not implemented for 'LambdaDataset'. "
            "Assuming output does not exist." in log_record.message
        )
        assert result is False

    def test_exists_invalid(self, data_catalog):
        """Check the error when calling `exists` on invalid dataset"""
        assert not data_catalog.exists("wrong_key")

    def test_release_unregistered(self, data_catalog):
        """Check the error when calling `release` on unregistered dataset"""
        pattern = r"Dataset \'wrong_key\' not found in the catalog"
        with pytest.raises(DatasetNotFoundError, match=pattern) as e:
            data_catalog.release("wrong_key")
        assert "did you mean" not in str(e.value)

    def test_release_unregistered_typo(self, data_catalog):
        """Check the error when calling `release` on mistyped dataset"""
        pattern = (
            "Dataset 'text' not found in the catalog"
            " - did you mean one of these instead: test"
        )
        with pytest.raises(DatasetNotFoundError, match=re.escape(pattern)):
            data_catalog.release("text")

    def test_multi_catalog_list(self, multi_catalog):
        """Test data catalog which contains multiple datasets"""
        entries = multi_catalog.list()
        assert "abc" in entries
        assert "xyz" in entries

    @pytest.mark.parametrize(
        "pattern,expected",
        [
            ("^a", ["abc"]),
            ("a|x", ["abc", "xyz"]),
            ("^(?!(a|x))", []),
            ("def", []),
            ("", []),
        ],
    )
    def test_multi_catalog_list_regex(self, multi_catalog, pattern, expected):
        """Test that regex patterns filter datasets accordingly"""
        assert multi_catalog.list(regex_search=pattern) == expected

    def test_multi_catalog_list_bad_regex(self, multi_catalog):
        """Test that bad regex is caught accordingly"""
        escaped_regex = r"\(\("
        pattern = f"Invalid regular expression provided: '{escaped_regex}'"
        with pytest.raises(SyntaxError, match=pattern):
            multi_catalog.list("((")

    def test_eq(self, multi_catalog, data_catalog):
        assert multi_catalog == multi_catalog.shallow_copy()
        assert multi_catalog != data_catalog

    def test_datasets_on_init(self, data_catalog_from_config):
        """Check datasets are loaded correctly on construction"""
        assert isinstance(data_catalog_from_config.datasets["boats"], CSVDataset)
        assert isinstance(data_catalog_from_config.datasets["cars"], CSVDataset)

    def test_datasets_on_add(self, data_catalog_from_config):
        """Check datasets are updated correctly after adding"""
        data_catalog_from_config.add("new_dataset", CSVDataset(filepath="some_path"))
        assert isinstance(data_catalog_from_config.datasets["new_dataset"], CSVDataset)
        assert isinstance(data_catalog_from_config.datasets["boats"], CSVDataset)

    def test_adding_datasets_not_allowed(self, data_catalog_from_config):
        """Check error if user tries to update the datasets attribute"""
        pattern = r"Operation not allowed. Please use KedroDataCatalog.add\(\) instead."
        with pytest.raises(AttributeError, match=pattern):
            data_catalog_from_config.datasets = None

    def test_confirm(self, mocker, caplog):
        """Confirm the dataset"""
        with caplog.at_level(logging.INFO):
            mock_ds = mocker.Mock()
            data_catalog = KedroDataCatalog(datasets={"mocked": mock_ds})
            data_catalog.confirm("mocked")
            mock_ds.confirm.assert_called_once_with()
            assert caplog.record_tuples == [
                (
                    "kedro.io.kedro_data_catalog",
                    logging.INFO,
                    "Confirming dataset 'mocked'",
                )
            ]

    @pytest.mark.parametrize(
        "dataset_name,error_pattern",
        [
            ("missing", "Dataset 'missing' not found in the catalog"),
            ("test", "Dataset 'test' does not have 'confirm' method"),
        ],
    )
    def test_bad_confirm(self, data_catalog, dataset_name, error_pattern):
        """Test confirming a non-existent dataset or one that
        does not have `confirm` method"""
        with pytest.raises(DatasetError, match=re.escape(error_pattern)):
            data_catalog.confirm(dataset_name)

    def test_shallow_copy_returns_correct_class_type(
        self,
    ):
        class MyDataCatalog(KedroDataCatalog):
            pass

        data_catalog = MyDataCatalog()
        copy = data_catalog.shallow_copy()
        assert isinstance(copy, MyDataCatalog)

    @pytest.mark.parametrize(
        "runtime_patterns,sorted_keys_expected",
        [
            (
                {
                    "{default}": {"type": "MemoryDataset"},
                    "{another}#csv": {
                        "type": "pandas.CSVDataset",
                        "filepath": "data/{another}.csv",
                    },
                },
                ["{another}#csv", "{default}"],
            )
        ],
    )
    def test_shallow_copy_adds_patterns(
        self, data_catalog, runtime_patterns, sorted_keys_expected
    ):
        assert not data_catalog.config_resolver.list_patterns()
        data_catalog = data_catalog.shallow_copy(runtime_patterns)
        assert data_catalog.config_resolver.list_patterns() == sorted_keys_expected

    def test_init_with_raw_data(self, dummy_dataframe, dataset):
        """Test catalog initialisation with raw data"""
        catalog = KedroDataCatalog(
            datasets={"ds": dataset}, raw_data={"df": dummy_dataframe}
        )
        assert "ds" in catalog
        assert "df" in catalog
        assert isinstance(catalog.datasets["ds"], CSVDataset)
        assert isinstance(catalog.datasets["df"], MemoryDataset)

    def test_repr(self, data_catalog):
        assert data_catalog.__repr__() == str(data_catalog)

    def test_missing_keys_from_load_versions(self, correct_config):
        """Test load versions include keys missing in the catalog"""
        pattern = "'load_versions' keys [version] are not found in the catalog."
        with pytest.raises(DatasetNotFoundError, match=re.escape(pattern)):
            KedroDataCatalog.from_config(
                **correct_config, load_versions={"version": "test_version"}
            )

    def test_get_dataset_matching_pattern(self, data_catalog):
        """Test get_dataset() when dataset is not in the catalog but pattern matches"""
        match_pattern_ds = "match_pattern_ds"
        assert match_pattern_ds not in data_catalog
        data_catalog.config_resolver.add_runtime_patterns(
            {"{default}": {"type": "MemoryDataset"}}
        )
        ds = data_catalog.get_dataset(match_pattern_ds)
        assert isinstance(ds, MemoryDataset)

    def test_release(self, data_catalog):
        """Test release is called without errors"""
        data_catalog.release("test")

    class TestKedroDataCatalogFromConfig:
        def test_from_correct_config(self, data_catalog_from_config, dummy_dataframe):
            """Test populating the data catalog from config"""
            data_catalog_from_config.save("boats", dummy_dataframe)
            reloaded_df = data_catalog_from_config.load("boats")
            assert_frame_equal(reloaded_df, dummy_dataframe)

        def test_config_missing_type(self, correct_config):
            """Check the error if type attribute is missing for some dataset(s)
            in the config"""
            del correct_config["catalog"]["boats"]["type"]
            pattern = (
                "An exception occurred when parsing config for dataset 'boats':\n"
                "'type' is missing from dataset catalog configuration"
            )
            with pytest.raises(DatasetError, match=re.escape(pattern)):
                KedroDataCatalog.from_config(**correct_config)

        def test_config_invalid_module(self, correct_config):
            """Check the error if the type points to nonexistent module"""
            correct_config["catalog"]["boats"]["type"] = (
                "kedro.invalid_module_name.io.CSVDataset"
            )

            error_msg = "Class 'kedro.invalid_module_name.io.CSVDataset' not found"
            with pytest.raises(DatasetError, match=re.escape(error_msg)):
                KedroDataCatalog.from_config(**correct_config)

        def test_config_relative_import(self, correct_config):
            """Check the error if the type points to a relative import"""
            correct_config["catalog"]["boats"]["type"] = ".CSVDatasetInvalid"

            pattern = "'type' class path does not support relative paths"
            with pytest.raises(DatasetError, match=re.escape(pattern)):
                KedroDataCatalog.from_config(**correct_config)

        def test_config_import_kedro_datasets(self, correct_config, mocker):
            """Test kedro_datasets default path to the dataset class"""
            # Spy _load_obj because kedro_datasets is not installed and we can't import it.

            import kedro.io.core

            spy = mocker.spy(kedro.io.core, "_load_obj")
            parse_dataset_definition(correct_config["catalog"]["boats"])
            for prefix, call_args in zip(_DEFAULT_PACKAGES, spy.call_args_list):
                assert call_args.args[0] == f"{prefix}pandas.CSVDataset"

        def test_config_missing_class(self, correct_config):
            """Check the error if the type points to nonexistent class"""
            correct_config["catalog"]["boats"]["type"] = "kedro.io.CSVDatasetInvalid"

            pattern = (
                "An exception occurred when parsing config for dataset 'boats':\n"
                "Class 'kedro.io.CSVDatasetInvalid' not found, is this a typo?"
            )
            with pytest.raises(DatasetError, match=re.escape(pattern)):
                KedroDataCatalog.from_config(**correct_config)

        @pytest.mark.skipif(
            sys.version_info < (3, 9),
            reason="for python 3.8 kedro-datasets version 1.8 is used which has the old spelling",
        )
        def test_config_incorrect_spelling(self, correct_config):
            """Check hint if the type uses the old DataSet spelling"""
            correct_config["catalog"]["boats"]["type"] = "pandas.CSVDataSet"

            pattern = (
                "An exception occurred when parsing config for dataset 'boats':\n"
                "Class 'pandas.CSVDataSet' not found, is this a typo?"
                "\nHint: If you are trying to use a dataset from `kedro-datasets`>=2.0.0,"
                " make sure that the dataset name uses the `Dataset` spelling instead of `DataSet`."
            )
            with pytest.raises(DatasetError, match=re.escape(pattern)):
                KedroDataCatalog.from_config(**correct_config)

        def test_config_invalid_dataset(self, correct_config):
            """Check the error if the type points to invalid class"""
            correct_config["catalog"]["boats"]["type"] = "KedroDataCatalog"
            pattern = (
                "An exception occurred when parsing config for dataset 'boats':\n"
                "Dataset type 'kedro.io.kedro_data_catalog.KedroDataCatalog' is invalid: "
                "all data set types must extend 'AbstractDataset'"
            )
            with pytest.raises(DatasetError, match=re.escape(pattern)):
                KedroDataCatalog.from_config(**correct_config)

        def test_config_invalid_arguments(self, correct_config):
            """Check the error if the dataset config contains invalid arguments"""
            correct_config["catalog"]["boats"]["save_and_load_args"] = False
            pattern = (
                r"Dataset 'boats' must only contain arguments valid for "
                r"the constructor of '.*CSVDataset'"
            )
            with pytest.raises(DatasetError, match=pattern):
                KedroDataCatalog.from_config(**correct_config)

        def test_config_invalid_dataset_config(self, correct_config):
            correct_config["catalog"]["invalid_entry"] = "some string"
            pattern = (
                "Catalog entry 'invalid_entry' is not a valid dataset configuration. "
                "\nHint: If this catalog entry is intended for variable interpolation, "
                "make sure that the key is preceded by an underscore."
            )
            with pytest.raises(DatasetError, match=pattern):
                KedroDataCatalog.from_config(**correct_config)

        def test_empty_config(self):
            """Test empty config"""
            assert KedroDataCatalog.from_config(None)

        def test_missing_credentials(self, correct_config):
            """Check the error if credentials can't be located"""
            correct_config["catalog"]["cars"]["credentials"] = "missing"
            with pytest.raises(
                KeyError, match=r"Unable to find credentials \'missing\'"
            ):
                KedroDataCatalog.from_config(**correct_config)

        def test_link_credentials(self, correct_config, mocker):
            """Test credentials being linked to the relevant dataset"""
            mock_client = mocker.patch("kedro_datasets.pandas.csv_dataset.fsspec")
            config = deepcopy(correct_config)
            del config["catalog"]["boats"]

            KedroDataCatalog.from_config(**config)

            expected_client_kwargs = correct_config["credentials"]["s3_credentials"]
            mock_client.filesystem.assert_called_with("s3", **expected_client_kwargs)

        def test_nested_credentials(self, correct_config_with_nested_creds, mocker):
            mock_client = mocker.patch("kedro_datasets.pandas.csv_dataset.fsspec")
            config = deepcopy(correct_config_with_nested_creds)
            del config["catalog"]["boats"]
            KedroDataCatalog.from_config(**config)

            expected_client_kwargs = {
                "client_kwargs": {
                    "credentials": {
                        "client_kwargs": {
                            "aws_access_key_id": "OTHER_FAKE_ACCESS_KEY",
                            "aws_secret_access_key": "OTHER_FAKE_SECRET_KEY",
                        }
                    }
                },
                "key": "secret",
            }
            mock_client.filesystem.assert_called_once_with(
                "s3", **expected_client_kwargs
            )

        def test_missing_nested_credentials(self, correct_config_with_nested_creds):
            del correct_config_with_nested_creds["credentials"]["other_credentials"]
            pattern = "Unable to find credentials 'other_credentials'"
            with pytest.raises(KeyError, match=pattern):
                KedroDataCatalog.from_config(**correct_config_with_nested_creds)

        def test_missing_dependency(self, correct_config, mocker):
            """Test that dependency is missing."""
            pattern = "dependency issue"

            def dummy_load(obj_path, *args, **kwargs):
                if obj_path == "kedro_datasets.pandas.CSVDataset":
                    raise AttributeError(pattern)
                if obj_path == "kedro_datasets.pandas.__all__":
                    return ["CSVDataset"]

            mocker.patch("kedro.io.core.load_obj", side_effect=dummy_load)
            with pytest.raises(DatasetError, match=pattern):
                KedroDataCatalog.from_config(**correct_config)

        def test_idempotent_catalog(self, correct_config):
            """Test that data catalog instantiations are idempotent"""
            _ = KedroDataCatalog.from_config(**correct_config)
            catalog = KedroDataCatalog.from_config(**correct_config)
            assert catalog

        def test_error_dataset_init(self, bad_config):
            """Check the error when trying to instantiate erroneous dataset"""
            pattern = r"Failed to instantiate dataset \'bad\' of type '.*BadDataset'"
            with pytest.raises(DatasetError, match=pattern):
                KedroDataCatalog.from_config(bad_config, None)

        def test_validate_dataset_config(self):
            """Test _validate_dataset_config raises error when wrong dataset config type is passed"""
            pattern = (
                "Catalog entry 'bad' is not a valid dataset configuration. \n"
                "Hint: If this catalog entry is intended for variable interpolation, make sure that the key is preceded by an underscore."
            )
            with pytest.raises(DatasetError, match=pattern):
                KedroDataCatalog._validate_dataset_config(
                    ds_name="bad", ds_config="not_dict"
                )

        def test_confirm(self, tmp_path, caplog, mocker):
            """Confirm the dataset"""
            with caplog.at_level(logging.INFO):
                mock_confirm = mocker.patch(
                    "kedro_datasets.partitions.incremental_dataset.IncrementalDataset.confirm"
                )
                catalog = {
                    "ds_to_confirm": {
                        "type": "kedro_datasets.partitions.incremental_dataset.IncrementalDataset",
                        "dataset": "pandas.CSVDataset",
                        "path": str(tmp_path),
                    }
                }
                data_catalog = KedroDataCatalog.from_config(catalog=catalog)
                data_catalog.confirm("ds_to_confirm")
                assert caplog.record_tuples == [
                    (
                        "kedro.io.kedro_data_catalog",
                        logging.INFO,
                        "Confirming dataset 'ds_to_confirm'",
                    )
                ]
                mock_confirm.assert_called_once_with()

        @pytest.mark.parametrize(
            "dataset_name,pattern",
            [
                ("missing", "Dataset 'missing' not found in the catalog"),
                ("boats", "Dataset 'boats' does not have 'confirm' method"),
            ],
        )
        def test_bad_confirm(self, correct_config, dataset_name, pattern):
            """Test confirming non existent dataset or the one that
            does not have `confirm` method"""
            data_catalog = KedroDataCatalog.from_config(**correct_config)
            with pytest.raises(DatasetError, match=re.escape(pattern)):
                data_catalog.confirm(dataset_name)

    class TestDataCatalogVersioned:
        def test_from_correct_config_versioned(self, correct_config, dummy_dataframe):
            """Test load and save of versioned datasets from config"""
            correct_config["catalog"]["boats"]["versioned"] = True

            # Decompose `generate_timestamp` to keep `current_ts` reference.
            current_ts = datetime.now(tz=timezone.utc)
            fmt = (
                "{d.year:04d}-{d.month:02d}-{d.day:02d}T{d.hour:02d}"
                ".{d.minute:02d}.{d.second:02d}.{ms:03d}Z"
            )
            version = fmt.format(d=current_ts, ms=current_ts.microsecond // 1000)

            catalog = KedroDataCatalog.from_config(
                **correct_config,
                load_versions={"boats": version},
                save_version=version,
            )

            catalog.save("boats", dummy_dataframe)
            path = Path(correct_config["catalog"]["boats"]["filepath"])
            path = path / version / path.name
            assert path.is_file()

            reloaded_df = catalog.load("boats")
            assert_frame_equal(reloaded_df, dummy_dataframe)

            reloaded_df_version = catalog.load("boats", version=version)
            assert_frame_equal(reloaded_df_version, dummy_dataframe)

            # Verify that `VERSION_FORMAT` can help regenerate `current_ts`.
            actual_timestamp = datetime.strptime(
                catalog.datasets["boats"].resolve_load_version(),
                VERSION_FORMAT,
            )
            expected_timestamp = current_ts.replace(
                microsecond=current_ts.microsecond // 1000 * 1000, tzinfo=None
            )
            assert actual_timestamp == expected_timestamp

        @pytest.mark.parametrize("versioned", [True, False])
        def test_from_correct_config_versioned_warn(
            self, caplog, correct_config, versioned
        ):
            """Check the warning if `version` attribute was added
            to the dataset config"""
            correct_config["catalog"]["boats"]["versioned"] = versioned
            correct_config["catalog"]["boats"]["version"] = True
            KedroDataCatalog.from_config(**correct_config)
            log_record = caplog.records[0]
            expected_log_message = (
                "'version' attribute removed from data set configuration since it "
                "is a reserved word and cannot be directly specified"
            )
            assert log_record.levelname == "WARNING"
            assert expected_log_message in log_record.message

        def test_from_correct_config_load_versions_warn(self, correct_config):
            correct_config["catalog"]["boats"]["versioned"] = True
            version = generate_timestamp()
            load_version = {"non-boat": version}
            pattern = (
                r"\'load_versions\' keys \[non-boat\] are not found in the catalog\."
            )
            with pytest.raises(DatasetNotFoundError, match=pattern):
                KedroDataCatalog.from_config(
                    **correct_config, load_versions=load_version
                )

        def test_compare_tracking_and_other_dataset_versioned(
            self, correct_config_with_tracking_ds, dummy_dataframe
        ):
            """Test saving of tracking datasets from config results in the same
            save version as other versioned datasets."""

            catalog = KedroDataCatalog.from_config(**correct_config_with_tracking_ds)

            catalog.save("boats", dummy_dataframe)
            dummy_data = {"col1": 1, "col2": 2, "col3": 3}
            catalog.save("planes", dummy_data)

            # Verify that saved version on tracking dataset is the same as on the CSV dataset
            csv_timestamp = datetime.strptime(
                catalog.datasets["boats"].resolve_save_version(),
                VERSION_FORMAT,
            )
            tracking_timestamp = datetime.strptime(
                catalog.datasets["planes"].resolve_save_version(),
                VERSION_FORMAT,
            )

            assert tracking_timestamp == csv_timestamp

        def test_load_version(self, correct_config, dummy_dataframe, mocker):
            """Test load versioned datasets from config"""
            new_dataframe = pd.DataFrame(
                {"col1": [0, 0], "col2": [0, 0], "col3": [0, 0]}
            )
            correct_config["catalog"]["boats"]["versioned"] = True
            mocker.patch(
                "kedro.io.kedro_data_catalog.generate_timestamp",
                side_effect=["first", "second"],
            )

            # save first version of the dataset
            catalog = KedroDataCatalog.from_config(**correct_config)
            catalog.save("boats", dummy_dataframe)

            # save second version of the dataset
            catalog = KedroDataCatalog.from_config(**correct_config)
            catalog.save("boats", new_dataframe)

            assert_frame_equal(catalog.load("boats", version="first"), dummy_dataframe)
            assert_frame_equal(catalog.load("boats", version="second"), new_dataframe)
            assert_frame_equal(catalog.load("boats"), new_dataframe)

        def test_load_version_on_unversioned_dataset(
            self, correct_config, dummy_dataframe, mocker
        ):
            mocker.patch(
                "kedro.io.kedro_data_catalog.generate_timestamp", return_value="first"
            )

            catalog = KedroDataCatalog.from_config(**correct_config)
            catalog.save("boats", dummy_dataframe)

            with pytest.raises(DatasetError):
                catalog.load("boats", version="first")
