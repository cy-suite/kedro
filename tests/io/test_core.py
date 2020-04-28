# Copyright 2020 QuantumBlack Visual Analytics Limited
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

from pathlib import PurePosixPath

import pytest

from kedro.io.core import _parse_filepath, get_filepath_str


class TestCoreFunctions:
    def test_get_filepath_str(self):
        path = get_filepath_str(PurePosixPath("example.com/test.csv"), "http")
        assert isinstance(path, str)
        assert path == "http://example.com/test.csv"

    @pytest.mark.parametrize(
        "filepath,expected_result",
        [
            ("s3://bucket/file.txt", {"protocol": "s3", "path": "bucket/file.txt"}),
            (
                "s3://user@BUCKET/file.txt",
                {"protocol": "s3", "path": "BUCKET/file.txt"},
            ),
            ("gcs://bucket/file.txt", {"protocol": "gcs", "path": "bucket/file.txt"}),
            ("gs://bucket/file.txt", {"protocol": "gs", "path": "bucket/file.txt"}),
            ("adl://bucket/file.txt", {"protocol": "adl", "path": "bucket/file.txt"}),
            ("abfs://bucket/file.txt", {"protocol": "abfs", "path": "bucket/file.txt"}),
            (
                "hdfs://namenode:8020/file.txt",
                {"protocol": "hdfs", "path": "/file.txt"},
            ),
            ("file:///tmp/file.txt", {"protocol": "file", "path": "/tmp/file.txt"}),
            ("/tmp/file.txt", {"protocol": "file", "path": "/tmp/file.txt"}),
            (
                "C:\\Projects\\file.txt",
                {"protocol": "file", "path": "C:\\Projects\\file.txt"},
            ),
            (
                "file:///C:\\Projects\\file.txt",
                {"protocol": "file", "path": "C:\\Projects\\file.txt"},
            ),
            (
                "https://example.com/file.txt",
                {"protocol": "https", "path": "https://example.com/file.txt"},
            ),
            (
                "http://example.com/file.txt",
                {"protocol": "http", "path": "http://example.com/file.txt"},
            ),
        ],
    )
    def test_parse_filepath(self, filepath, expected_result):
        assert _parse_filepath(filepath) == expected_result
