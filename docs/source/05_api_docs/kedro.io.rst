kedro.io
========

.. rubric:: Description

.. automodule:: kedro.io

Data Catalog
------------

.. autosummary::
    :toctree:
    :template: autosummary/class.rst

    kedro.io.DataCatalog

Data Sets
---------

.. autosummary::
    :toctree:
    :template: autosummary/class.rst

    kedro.io.CSVLocalDataSet
    kedro.io.CSVHTTPDataSet
    kedro.io.CSVS3DataSet
    kedro.io.CSVDataSet
    kedro.io.HDFDataSet
    kedro.io.HDFLocalDataSet
    kedro.io.HDFS3DataSet
    kedro.io.JSONLocalDataSet
    kedro.io.JSONDataSet
    kedro.io.LambdaDataSet
    kedro.io.MemoryDataSet
    kedro.io.ParquetDataSet
    kedro.io.ParquetLocalDataSet
    kedro.io.PartitionedDataSet
    kedro.io.PickleLocalDataSet
    kedro.io.PickleS3DataSet
    kedro.io.PickleDataSet
    kedro.io.SQLTableDataSet
    kedro.io.SQLQueryDataSet
    kedro.io.TextDataSet
    kedro.io.TextLocalDataSet
    kedro.io.ExcelDataSet
    kedro.io.ExcelLocalDataSet
    kedro.io.YAMLDataSet

Additional ``AbstractDataSet`` implementations can be found in ``kedro.contrib.io``.

Errors
------

.. autosummary::
    :toctree:
    :template: autosummary/class.rst

    kedro.io.DataSetAlreadyExistsError
    kedro.io.DataSetError
    kedro.io.DataSetNotFoundError


Base Classes
------------

.. autosummary::
    :toctree:
    :template: autosummary/class.rst

    kedro.io.AbstractDataSet
    kedro.io.AbstractVersionedDataSet
    kedro.io.AbstractTransformer
    kedro.io.Version
