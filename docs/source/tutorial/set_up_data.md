# Set up the data

```{note}
Don't forget to check the [tutorial FAQ](spaceflights_tutorial_faqs.md) if you run into problems, or [ask the community for help](spaceflights_tutorial.md#get-help) if you need it!
```

In this section, we discuss the data setup phase, which is the second part of the standard development workflow. The steps are as follows:

* Add datasets to your `data` folder, according to [data engineering convention](../faq/faq.md#what-is-data-engineering-convention)
* Register the datasets with the Kedro Data Catalog in `conf/base/catalog.yml`, which is the registry of all data sources available for use by the project. This ensures that your code is reproducible when it references datasets in different locations and/or environments.

You can find further information about the [Data Catalog](../data/data_catalog.md) in specific documentation covering advanced usage.

```{note}
If you are using the tutorial created by the spaceflights starter, you can omit the copy/paste steps below, but it is worth reviewing the files described.
```

## Download datasets

The spaceflights tutorial makes use of three fictional datasets of companies shuttling customers to the Moon and back. The data comes in two different formats: `.csv` and `.xlsx`:

* `companies.csv` contains data about space travel companies, such as their location, fleet count and rating
* `reviews.csv` is a set of reviews from customers for categories, such as comfort and price
* `shuttles.xlsx` is a set of attributes for spacecraft across the fleet, such as their engine type and passenger capacity

Download and save the files to the `data/01_raw` folder of your project:

* [companies.csv](https://kedro-org.github.io/kedro/companies.csv)
* [reviews.csv](https://kedro-org.github.io/kedro/reviews.csv)
* [shuttles.xlsx](https://kedro-org.github.io/kedro/shuttles.xlsx)

## Register the datasets

You now need to register the datasets so they can be loaded by Kedro. All Kedro projects have a `conf/base/catalog.yml` file, and you register each dataset by adding a named entry into the `.yml` file that includes the following:

* File location (path)
* Parameters for the given dataset
* Type of data
* Versioning

### Register `csv` data

First, for the spaceflights data, register the two `csv` datasets by adding this snippet to the end of the `conf/base/catalog.yml` file and saving it:

```yaml
companies:
  type: pandas.CSVDataSet
  filepath: data/01_raw/companies.csv

reviews:
  type: pandas.CSVDataSet
  filepath: data/01_raw/reviews.csv
```

### Register `xlsx` data

Now register the `xlsx` dataset by adding this snippet to the end of the `conf/base/catalog.yml` file, and saving it:

```yaml
shuttles:
  type: pandas.ExcelDataSet
  filepath: data/01_raw/shuttles.xlsx
  load_args:
    engine: openpyxl # Use modern Excel engine (the default since Kedro 0.18.0)
```

This registration has an additional line: `load_args`, which is passed to the excel file read method (`pd.read_excel`) as a [keyword argument](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_excel.html). Although not specified here, the equivalent output is `save_args` and the value would be passed to [`pd.DataFrame.to_excel` method](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_excel.html).

### Test that Kedro can load the `csv` data

Open a `kedro ipython` session in your terminal from the project root directory:

```bash
kedro ipython
```

Then type the following into the IPython prompt:

```python
companies = catalog.load("companies")
companies.head()
```

* The first command creates a variable (`companies`), which is of type `pandas.DataFrame` and loads the dataset (also named `companies` as per top-level key in `catalog.yml`) from the underlying filepath `data/01_raw/companies.csv`.
* The `head` method from `pandas` displays the first five rows of the DataFrame.

```
INFO     Loading data from 'companies' (CSVDataSet)
Out[1]:
      id company_rating       company_location  total_fleet_count iata_approved
0  35029           100%                   Niue                4.0             f
1  30292            67%               Anguilla                6.0             f
2  19032            67%     Russian Federation                4.0             f
3   8238            91%               Barbados               15.0             t
4  30342            NaN  Sao Tome and Principe                2.0             t

```

### Test that Kedro can load the `xlsx` data

To test that everything works as expected, load the dataset within IPython and display its first five rows:

```python
shuttles = catalog.load("shuttles")
shuttles.head()
```

You should see output such as the following:

```
INFO     Loading data from 'shuttles' (ExcelDataSet)
Out[1]:
      id       shuttle_location shuttle_type engine_type  ... d_check_complete  moon_clearance_complete     price company_id
0  63561                   Niue      Type V5     Quantum  ...                f                        f  $1,325.0      35029
1  36260               Anguilla      Type V5     Quantum  ...                t                        f  $1,780.0      30292
2  57015     Russian Federation      Type V5     Quantum  ...                f                        f  $1,715.0      19032
3  14035               Barbados      Type V5      Plasma  ...                f                        f  $4,770.0       8238
4  10036  Sao Tome and Principe      Type V2      Plasma  ...                f                        f  $2,820.0      30342

```

When you have finished, close `ipython` session with `exit()`.

## Further information

### Custom data

[Kedro supports numerous datasets](/kedro.datasets) out of the box, but you can also add support for any proprietary data format or filesystem in your pipeline.

You can find further information about [how to add support for custom datasets](../extend_kedro/custom_datasets.md) in specific documentation covering advanced usage.

### Supported data locations

Kedro uses [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to read data from a variety of data stores including local file systems, network file systems, HDFS, and all of the widely-used cloud object stores.
