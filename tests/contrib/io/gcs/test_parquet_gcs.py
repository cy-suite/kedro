# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
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
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
from contextlib import contextmanager

import pandas as pd
import pyarrow.parquet as pq
import pytest
from pandas.util.testing import assert_frame_equal

from kedro.contrib.io.gcs.parquet_gcs import ParquetGCSDataSet
from kedro.io import DataSetError, Version
from kedro.io.core import generate_timestamp

from . import gcs_mocks

FILENAME = "test.parquet"
BUCKET_NAME = "parquetbucketkedro"
GCP_PROJECT = "parquetproject"


class MockGCSFileSystem(gcs_mocks.BasicGCSFileSystemMock):
    def __init__(self, tmp_path):
        super().__init__()
        self.tmp_path = tmp_path

    @contextmanager
    def open(self, filepath, *args, **kwargs):
        path = self.files.get(str(filepath))
        mode = kwargs.get("mode", "r")
        if path:
            with open(path, mode) as gcs_file:
                yield gcs_file
        else:
            yield


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture(params=[None])
def load_args(request):
    return request.param


@pytest.fixture(params=[None])
def save_args(request):
    return request.param


@pytest.fixture(params=[None])
def load_version(request):
    return request.param


@pytest.fixture(params=[None])
def save_version(request):
    return request.param or generate_timestamp()


@pytest.fixture
def mock_gcs_filesystem(mocker, tmp_path):
    mocked = mocker.patch("gcsfs.GCSFileSystem", autospec=True)
    mocked.return_value = MockGCSFileSystem(tmp_path)
    return mocked


@pytest.fixture
def gcs_data_set(
    load_args, save_args, mock_gcs_filesystem
):  # pylint: disable=unused-argument
    return ParquetGCSDataSet(
        filepath=FILENAME,
        bucket_name=BUCKET_NAME,
        credentials=None,
        load_args=load_args,
        save_args=save_args,
        project=GCP_PROJECT,
    )


@pytest.fixture()
def write_table_mock(mocker):
    mocked_pq = mocker.patch("kedro.contrib.io.gcs.parquet_gcs.pq")
    mocked_pq.write_table = write_table
    return mocked_pq


def write_table(table, where, filesystem, **kwargs):  # pylint: disable=unused-argument
    path = str(filesystem.tmp_path / FILENAME)
    filesystem.files[str(where)] = path
    pq.write_table(table, path)


class TestParquetGCSDataSet:
    def test_credentials_propagated(self, mocker):
        """Test propagating credentials for connecting to GCS"""
        mock_gcs = mocker.patch("gcsfs.GCSFileSystem")
        credentials = {"client_email": "a@b.com", "whatever": "useless"}

        ParquetGCSDataSet(
            filepath=FILENAME,
            bucket_name=BUCKET_NAME,
            project=GCP_PROJECT,
            credentials=credentials,
        )

        mock_gcs.assert_called_once_with(project=GCP_PROJECT, token=credentials)

    @pytest.mark.usefixtures("mock_gcs_filesystem")
    def test_non_existent_bucket(self):
        """Test non-existent bucket"""
        pattern = r"Failed while loading data from data set ParquetGCSDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            ParquetGCSDataSet(
                filepath=FILENAME,
                bucket_name="not-existing-bucket",
                project=GCP_PROJECT,
                credentials=None,
            ).load()

    @pytest.mark.usefixtures("mock_gcs_filesystem", "write_table_mock")
    def test_save_load_data(self, gcs_data_set, dummy_dataframe):
        assert not gcs_data_set.exists()
        gcs_data_set.save(dummy_dataframe)
        loaded_data = gcs_data_set.load()
        assert_frame_equal(dummy_dataframe, loaded_data)

    @pytest.mark.usefixtures("mock_gcs_filesystem", "write_table_mock")
    def test_save_and_load_with_protocol(self, dummy_dataframe, load_args, save_args):
        """Test loading the data from GCS using full path."""
        gcs_data_set = ParquetGCSDataSet(
            filepath="gcs://{}/{}".format(BUCKET_NAME, FILENAME),
            credentials=None,
            load_args=load_args,
            save_args=save_args,
            project=GCP_PROJECT,
        )
        assert not gcs_data_set.exists()
        gcs_data_set.save(dummy_dataframe)
        loaded_data = gcs_data_set.load()
        assert_frame_equal(loaded_data, dummy_dataframe)
        assert str(gcs_data_set._filepath) == "{}/{}".format(BUCKET_NAME, FILENAME)

    @pytest.mark.usefixtures("write_table_mock")
    def test_exists(self, gcs_data_set, dummy_dataframe):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not gcs_data_set.exists()
        gcs_data_set.save(dummy_dataframe)
        assert gcs_data_set.exists()

    @pytest.mark.parametrize(
        "load_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_load_extra_params(self, gcs_data_set, load_args):
        """Test overriding the default load arguments."""
        for key, value in load_args.items():
            assert gcs_data_set._load_args[key] == value

    @pytest.mark.parametrize(
        "save_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_save_extra_params(self, gcs_data_set, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert gcs_data_set._save_args[key] == value

    @pytest.mark.parametrize("save_args", [{"option": "value"}], indirect=True)
    def test_str_representation(self, gcs_data_set, save_args):
        """Test string representation of the data set instance."""
        str_repr = str(gcs_data_set)
        assert "ParquetGCSDataSet" in str_repr
        for k in save_args.keys():
            assert k in str_repr

    @pytest.mark.parametrize("load_args", [{"custom": 42}], indirect=True)
    def test_load_args_propagated(self, gcs_data_set, load_args, mocker):
        mock_read_parquet = mocker.patch(
            "kedro.contrib.io.gcs.parquet_gcs.pd.read_parquet"
        )
        gcs_data_set.load()
        assert mock_read_parquet.call_args_list[0][1] == load_args

    @pytest.mark.parametrize("save_args", [{"custom": 45}], indirect=True)
    def test_save_args_propagated(
        self, gcs_data_set, save_args, dummy_dataframe, mocker
    ):
        mock_pa = mocker.patch("kedro.contrib.io.gcs.parquet_gcs.pa")
        mock_pa.Table.from_pandas.return_value = "table"
        mock_pq = mocker.patch("kedro.contrib.io.gcs.parquet_gcs.pq")
        gcs_data_set.save(dummy_dataframe)
        mock_pq.write_table.assert_called_once_with(
            table="table",
            where=gcs_data_set._filepath,
            filesystem=gcs_data_set._gcs,
            **save_args,
        )


@pytest.fixture
def versioned_gcs_data_set(
    load_version,
    save_version,
    load_args,
    save_args,
    mock_gcs_filesystem,  # pylint: disable=unused-argument
):
    return ParquetGCSDataSet(
        bucket_name=BUCKET_NAME,
        filepath=FILENAME,
        credentials=None,
        load_args=load_args,
        save_args=save_args,
        version=Version(load_version, save_version),
        project=GCP_PROJECT,
    )


class TestParquetGCSDataSetVersioned:
    def test_no_versions(self, versioned_gcs_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for ParquetGCSDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_gcs_data_set.load()

    @pytest.mark.usefixtures("write_table_mock")
    def test_save_and_load(self, versioned_gcs_data_set, dummy_dataframe):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_gcs_data_set.save(dummy_dataframe)
        reloaded_df = versioned_gcs_data_set.load()
        assert_frame_equal(dummy_dataframe, reloaded_df)

    @pytest.mark.usefixtures("write_table_mock")
    def test_prevent_override(self, versioned_gcs_data_set, dummy_dataframe):
        """Check the error when attempting to override the data set if the
        corresponding dataframe object for a given save version already exists in GCS."""
        versioned_gcs_data_set.save(dummy_dataframe)
        pattern = (
            r"Save path \`.+\` for ParquetGCSDataSet\(.+\) must not exist "
            r"if versioning is enabled"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_gcs_data_set.save(dummy_dataframe)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    @pytest.mark.usefixtures("write_table_mock")
    def test_save_version_warning(
        self, versioned_gcs_data_set, load_version, save_version, dummy_dataframe
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save version `{0}` did not match load version `{1}` "
            r"for ParquetGCSDataSet\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_gcs_data_set.save(dummy_dataframe)

    def test_version_str_repr(self, save_version, gcs_data_set, versioned_gcs_data_set):
        """Test that version is in string representation of the class instance
        when applicable."""
        assert FILENAME in str(gcs_data_set)
        assert "version" not in str(gcs_data_set)

        assert FILENAME in str(versioned_gcs_data_set)
        ver_str = "version=Version(load={}, save='{}')".format(None, save_version)
        assert ver_str in str(versioned_gcs_data_set)

        assert BUCKET_NAME in str(gcs_data_set)
        assert BUCKET_NAME in str(versioned_gcs_data_set)

    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    @pytest.mark.usefixtures("write_table_mock")
    def test_exists_versioned(
        self,
        versioned_gcs_data_set,
        dummy_dataframe,
        save_version,  # pylint: disable=unused-argument
    ):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_gcs_data_set.exists()
        versioned_gcs_data_set.save(dummy_dataframe)
        assert versioned_gcs_data_set.exists()
