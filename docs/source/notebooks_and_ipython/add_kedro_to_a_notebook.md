---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.15.2
  kernelspec:
    display_name: Python 3 (ipykernel)
    language: python
    name: python3
---

# Add Kedro features to a notebook

This page describes how to add Kedro features incrementally to a notebook. 

It starts with a version of the spaceflights example with does NOT use Kedro that you can run inside a notebook. The example converts portions of the code to use Kedro features while remaining runnable from within a notebook.


## Spaceflights in a notebook

If you are unfamiliar with the spaceflights example, it is used to introduce the basics of Kedro in a tutorial that runs exclusively as a Kedro project, that is, as a set of `.py` files rather than in a notebook. The premise is as follows:

_It is 2160, and the space tourism industry is booming. Globally, thousands of space shuttle companies take tourists to the Moon and back. You have been able to source data that lists the amenities offered in each space shuttle, customer reviews, and company information._

_Project: You want to construct a model that predicts the price for each trip to the Moon and the corresponding return flight._



### The notebook example
The full example code is given below. In a real notebook example, it would most likely be split across multiple cells with various additional code added to inspect and explore the data.

```python
import pandas as pd

# This code needs the data folder set up and three files downloaded. 
# Is there a way to do this in code from the notebook to save the reader the manual task?
# Either download the file or use an OS data fabricator to make 3 files?

companies = pd.read_csv('data/companies.csv')
reviews = pd.read_csv('data/reviews.csv')
shuttles = pd.read_excel('data/shuttles.xlsx', engine='openpyxl')

# Data processing
companies["iata_approved"] = companies["iata_approved"] == "t"
companies["company_rating"] = companies["company_rating"].str.replace("%", "").astype(float)
shuttles["d_check_complete"] = shuttles["d_check_complete"] == "t"
shuttles["moon_clearance_complete"] = shuttles["moon_clearance_complete"] == "t"
shuttles["price"] = shuttles["price"].str.replace("$", "").str.replace(",", "").astype(float)
rated_shuttles = shuttles.merge(reviews, left_on="id", right_on="shuttle_id")
model_input_table = rated_shuttles.merge(companies, left_on="company_id", right_on="id")
model_input_table = model_input_table.dropna()
model_input_table.head()

# Model evaluation

from sklearn.model_selection import train_test_split

X = model_input_table[[
    "engines",
    "passenger_capacity",
    "crew",
    "d_check_complete",
    "moon_clearance_complete",
    "iata_approved",
    "company_rating",
    "review_scores_rating",
]]
y = model_input_table["price"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=3)

from sklearn.linear_model import LinearRegression
model = LinearRegression()
model.fit(X_train, y_train)
model.predict(X_test)
from sklearn.metrics import r2_score
y_pred = model.predict(X_test)
r2_score(y_test, y_pred)
```

## Use Kedro for data processing
Even if you’re not ready for a full Kedro project, you can still take advantage of its data handling solution in your existing project from within a notebook. This section shows you how.

Kedro’s Data Catalog is a registry of all data sources available for use by the project, and offers a separate place to declare details of the datasets your projects use. Kedro provides [built-in datasets for numerous file types and file systems](https://docs.kedro.org/en/stable/kedro_datasets.html), so you don’t have to write any of the logic for reading or writing data. 

Kedro offers a range of datasets, including CSV, Excel, Parquet, Feather, HDF5, JSON, Pickle, SQL Tables, SQL Queries, Spark DataFrames and more. They are supported with the APIs of pandas, spark, networkx, matplotlib, yaml and more. It relies on `[fsspec](https://filesystem-spec.readthedocs.io/en/latest/)` to read and save data from a variety of data stores including local file systems, network file systems, cloud object stores, and Hadoop. You can pass arguments in to load and save operations, and use versioning and credentials for data access.

To start using the Data Catalog, create a `catalog.yml` in the same folder as your notebook to define datasets that can be used when writing your functions. For example:


<!--This code needs the user to create a yaml file with this contents. Is there a piece of code we could offer that creates and writes one for them into the appropriate directory to save the reader the manual task? -->

```yml
companies:
  type: pandas.CSVDataSet
  filepath: data/companies.csv

reviews:
  type: pandas.CSVDataSet
  filepath: data/reviews.csv

shuttles:
  type: pandas.ExcelDataSet
  filepath: data/shuttles.xlsx
```

Then by using Kedro to load the `catalog.yml` file, you can reference the Data Catalog in your notebook as you load the data for data processing.

```python
# Using Kedro's DataCatalog

from kedro.io import DataCatalog

import yaml
# load the configuration file 
with open("catalog.yml") as f:
    conf_catalog = yaml.safe_load(f)

# Create the DataCatalog instance from the configuration
catalog = DataCatalog.from_config(conf_catalog)

# Load the datasets
companies = catalog.load("companies")
reviews = catalog.load("reviews")
shuttles = catalog.load("shuttles")
```

The rest of the spaceflights notebook code for data processing and model evaluation from above can now run as previously. 

<!-- #region -->
## Use a YAML configuration file

### Use a configuration file just for "magic numbers"
When writing exploratory code, it’s tempting to hard code values to save time, but it makes code harder to maintain in the longer-term. The example code for model evaluation above calls `sklearn.model_selection.train_test_split()`, passing in a model input table and outputs the test and train datasets. There are hard-code values supplied to `test_size` and `random_state`.

```python
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=3)
```

[Good software engineering practice](https://towardsdatascience.com/five-software-engineering-principles-for-collaborative-data-science-ab26667a311) suggests that we extract *‘magic numbers’* into named constants, sometimes defined at the top of a file, or outside in a utility file, storing it in a format such as yaml. 

<!--This code needs the user to create a yaml file with this contents. Is there a piece of code we could offer that creates and writes one for them into the appropriate directory to save the reader the manual task? -->

```yml
# params.yml

model_options:
  test_size: 0.3
  random_state: 3
```  

By loading `params.yml`, you can reference the values with the notebook code. 


<!-- #endregion -->

```python
import yaml

with open("params.yml", encoding="utf-8") as yaml_file:
    params=yaml.safe_load(yaml_file)
    
```

```python
test_size = params["model_options"]["test_size"]
random_state = params["model_options"]["random_state"]
```

```python
features = [
    "engines",
    "passenger_capacity",
    "crew",
    "d_check_complete",
    "moon_clearance_complete",
    "iata_approved",
    "company_rating",
    "review_scores_rating",
]
                                                                                                                                                                                                                               
```

```python
X = model_input_table[features]
y = model_input_table["price"]
```

```python
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)   
```

The rest of the model evaluation code can now run as previously. 

```python
from sklearn.linear_model import LinearRegression
model = LinearRegression()
model.fit(X_train, y_train)
model.predict(X_test)
from sklearn.metrics import r2_score
y_pred = model.predict(X_test)
r2_score(y_test, y_pred)
```

### Use a configuration file for all "magic values"
If we extend the concept of magic numbers to encompass magic values in general, we might also see that the variable features also seems like it might be reusable elsewhere. Extracting it from code into `parameters.yml` leads to the following:

<!--This code needs the user to create a yaml file with this contents. Is there a piece of code we could offer that creates and writes one for them into the appropriate directory to save the reader the manual task? -->

```yml
# parameters.yml 

model_options:
  test_size: 0.3
  random_state: 3
  features:
    - engines
    - passenger_capacity
    - crew
    - d_check_complete
    - moon_clearance_complete
    - iata_approved
    - company_rating
    - review_scores_rating
```

The code now looks as follows:

```python
import yaml 

with open("parameters.yaml", encoding="utf-8") as yaml_file:
    parameters = yaml.safe_load(yaml_file)

test_size = parameters["model_options"]["test_size"]
random_state = parameters["model_options"]["random_state"]
```

```python
X = model_input_table[parameters["model_options"]["features"]]
y = model_input_table["price"]
```

```python
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)   
```

The rest of the model evaluation code can now run as previously. 

```python
from sklearn.linear_model import LinearRegression
model = LinearRegression()
model.fit(X_train, y_train)
model.predict(X_test)
from sklearn.metrics import r2_score
y_pred = model.predict(X_test)
r2_score(y_test, y_pred)
```

## Use Kedro configuration
Kedro offers a [configuration loader](https://docs.kedro.org/en/stable/kedro.config.ConfigLoader.html) to abstract loading values from a yaml file. You can use Kedro configuration loading without a full Kedro project and this approach replaces the need to load the configuration file with `yaml.safe_load`.

### Use Kedro's configuration loader to load "magic values"
There is some setup to get this working initially:

1. In your notebook folder, create a subfolder called `conf`. 
2. Within the `conf` subfolder, create a subfolder called `base`. 
3. Copy `parameters.yml` into `conf/base/` so you have a file with the path `conf/base/parameters.yml`.
4. Within the `conf` subfolder, create another subfolder called `local`. 

After this setup, you can use Kedro's `OmegaConfigLoader` in code as follows:

```python
from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings

conf_loader = OmegaConfigLoader("conf")
```

```python
conf_params=conf_loader["parameters"]
test_size = conf_params["model_options"]["test_size"]
random_state = conf_params["model_options"]["random_state"]
X = model_input_table[conf_params["model_options"]["features"]]
y = model_input_table["price"]
```

```python
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=test_size, random_state=random_state)
 
```

```python
The rest of the model evaluation code can now run as previously. 
```

```python
from sklearn.linear_model import LinearRegression
model = LinearRegression()
model.fit(X_train, y_train)
model.predict(X_test)
from sklearn.metrics import r2_score
y_pred = model.predict(X_test)
r2_score(y_test, y_pred)
```

<!-- #region -->
### Use Kedro's configuration loader to load the Data Catalog
We have seen how to use Kedro's Data Catalog to load a `yaml` file, with `safe_load` and pass it to the `DataCatalog` class. 

```python
# Using Kedro's DataCatalog

from kedro.io import DataCatalog

import yaml
# load the configuration file 
with open("catalog.yml") as f:
    conf_catalog = yaml.safe_load(f)

# Create the DataCatalog instance from the configuration
catalog = DataCatalog.from_config(conf_catalog)

# Load the datasets
...
```
<!-- #endregion -->

It's also possible to use the configuration loader to initialise the Data Catalog. As we saw from loading parameter values, there is some initial setup because of the Kedro project structure:

1. If you haven't already, in your notebook folder, create a subfolder called `conf`. 
2. Within the `conf` subfolder, create a subfolder called `base`. 
3. Copy your `catalog.yml` into `conf/base/` so you have a file with the path `conf/base/catalog.yml`.
4. Within the `conf` subfolder, if you haven't already, create a subfolder called `local`. 

After this setup, you can use Kedro's `OmegaConfigLoader` in code as follows:

```python
# Now we are using Kedro's ConfigLoader alongside the DataCatalog

from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings
from kedro.io import DataCatalog

conf_loader = OmegaConfigLoader("conf")
conf_catalog=conf_loader["catalog"]

# Create the DataCatalog instance from the configuration
catalog = DataCatalog.from_config(conf_catalog)

# Load the datasets
companies = catalog.load("companies")
reviews = catalog.load("reviews")
shuttles = catalog.load("shuttles")
```

## Where next?
At this point in the notebook, we've introduced Kedro data management (using the Data Catalog) and configuration loader. TO DO -- ADD SOME REASONING FOR WHY KEDRO ENCOURAGES THIS AND LINK TO BEST PRACTICES. You have now "Kedro-ised" the notebook code to make it more reusable in future. However, you can go further if your ultimate goal is to migrate code out of the notebook and use it in a full-blown Kedro project. 

## Refactor your code into functions
Code in a Kedro project runs in one or more pipelines, where a pipeline is a series of nodes, which wrap discrete functions. If your ultimate goal is to create a Kedro project and use it to run your notebook code, you'll need to take the code that processes the data, and the code that calls the data science model, and make it into one or more nodes. 

One option is to simply put everything into a single function. Let's try this.

```python
# Use Kedro for data management and configuration

from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings
from kedro.io import DataCatalog

conf_loader = OmegaConfigLoader("conf")
conf_catalog=conf_loader["catalog"]
conf_params=conf_loader["parameters"]

# Create the DataCatalog instance from the configuration
catalog = DataCatalog.from_config(conf_catalog)

# Load the datasets
companies = catalog.load("companies")
reviews = catalog.load("reviews")
shuttles = catalog.load("shuttles")

# Load the configuration data
test_size = conf_params["model_options"]["test_size"]
random_state = conf_params["model_options"]["random_state"]

```

```python
def big_function():
    
    ####################
    # Data processing  #
    ####################
    companies["iata_approved"] = companies["iata_approved"] == "t"
    companies["company_rating"] = companies["company_rating"].str.replace("%", "").astype(float)
    shuttles["d_check_complete"] = shuttles["d_check_complete"] == "t"
    shuttles["moon_clearance_complete"] = shuttles["moon_clearance_complete"] == "t"
    shuttles["price"] = shuttles["price"].str.replace("$", "").str.replace(",", "").astype(float)
    rated_shuttles = shuttles.merge(reviews, left_on="id", right_on="shuttle_id")
    model_input_table = rated_shuttles.merge(companies, left_on="company_id", right_on="id")
    model_input_table = model_input_table.dropna()
    model_input_table.head()

    X = model_input_table[conf_params["model_options"]["features"]]
    y = model_input_table["price"]

    ####################
    # Model evaluation  #
    ####################  
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state)
 
    from sklearn.linear_model import LinearRegression

    model = LinearRegression()
    model.fit(X_train, y_train)
    model.predict(X_test)
    from sklearn.metrics import r2_score
    y_pred = model.predict(X_test)
    print(r2_score(y_test, y_pred))
```

```python
# Call the one big function
big_function()
```

In truth, this code is not much more maintainable than if it were spread throughout multiple notebook cells. Maybe we could do better with a series of smaller functions, which would map more clearly to the Kedro vision of a pipeline that comprises a series of nodes, each of which behave consistently, repeatably and predictably, so that a given input  to a node always returns the same output. For those in the know, this is the definition of a pure function (LINK) and, as per software engineering best practice for readable code (LINK AGAIN), nodes/pure functions should be small single responsibility functions that perform a single specific task.  

Let's try this with our code. We'll split it into a set of functions to process the data, which are based on the code in `big_function` but where each function has a single responsibility. Then we'll add a set of model evaluation functions which similarly use the code we've written previously but split into three separate functions.

```python
####################
# Data processing  #
####################
import pandas as pd

def _is_true(x: pd.Series) -> pd.Series:
    return x == "t"


def _parse_percentage(x: pd.Series) -> pd.Series:
    x = x.str.replace("%", "")
    x = x.astype(float) / 100
    return x


def _parse_money(x: pd.Series) -> pd.Series:
    x = x.str.replace("$", "").str.replace(",", "")
    x = x.astype(float)
    return x


def preprocess_companies(companies: pd.DataFrame) -> pd.DataFrame:

    companies["iata_approved"] = _is_true(companies["iata_approved"])
    companies["company_rating"] = _parse_percentage(companies["company_rating"])
    return companies


def preprocess_shuttles(shuttles: pd.DataFrame) -> pd.DataFrame:

    shuttles["d_check_complete"] = _is_true(shuttles["d_check_complete"])
    shuttles["moon_clearance_complete"] = _is_true(shuttles["moon_clearance_complete"])
    shuttles["price"] = _parse_money(shuttles["price"])
    return shuttles

def create_model_input_table(
    shuttles: pd.DataFrame, companies: pd.DataFrame, reviews: pd.DataFrame
) -> pd.DataFrame:

    rated_shuttles = shuttles.merge(reviews, left_on="id", right_on="shuttle_id")
    model_input_table = rated_shuttles.merge(
        companies, left_on="company_id", right_on="id"
    )
    model_input_table = model_input_table.dropna()
    return model_input_table


####################
# Model evaluation #
####################

from typing import Dict, Tuple
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

def split_data(data: pd.DataFrame, parameters: Dict) -> Tuple:
    X = data[parameters["features"]]
    y = data["price"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=parameters["test_size"], random_state=parameters["random_state"]
    )
    return X_train, X_test, y_train, y_test


def train_model(X_train: pd.DataFrame, y_train: pd.Series) -> LinearRegression:
    regressor = LinearRegression()
    regressor.fit(X_train, y_train)
    return regressor


def evaluate_model(
    regressor: LinearRegression, X_test: pd.DataFrame, y_test: pd.Series
):
    y_pred = regressor.predict(X_test)
    print(r2_score(y_test, y_pred))
    
```

```python
# Call data processing functions
preprocessed_companies = preprocess_companies(companies)
preprocessed_shuttles = preprocess_shuttles(shuttles)
model_input_table = create_model_input_table(preprocessed_shuttles, preprocessed_companies, reviews)

# Call model evaluation functions
X_train, X_test, y_train, y_test = split_data(model_input_table, conf_params["model_options"])
regressor = train_model(X_train, y_train)
evaluate_model(regressor, X_test, y_test)

```

And that's it. The notebook code has been refactored into a series of functions that use some Kedro setup code to read in configuration values and data. Let's reproduce it all in one big notebook cell for reference so you can see how it looks in comparison to the first cell of the notebook that was the start of this example.

```python
# Kedro setup for data management and configuration
from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings
from kedro.io import DataCatalog

conf_loader = OmegaConfigLoader("conf")
conf_catalog=conf_loader["catalog"]
conf_params=conf_loader["parameters"]

# Create the DataCatalog instance from the configuration
catalog = DataCatalog.from_config(conf_catalog)

# Load the datasets
companies = catalog.load("companies")
reviews = catalog.load("reviews")
shuttles = catalog.load("shuttles")

# Load the configuration data
test_size = conf_params["model_options"]["test_size"]
random_state = conf_params["model_options"]["random_state"]


####################
# Data processing  #
####################
import pandas as pd

def _is_true(x: pd.Series) -> pd.Series:
    return x == "t"


def _parse_percentage(x: pd.Series) -> pd.Series:
    x = x.str.replace("%", "")
    x = x.astype(float) / 100
    return x


def _parse_money(x: pd.Series) -> pd.Series:
    x = x.str.replace("$", "").str.replace(",", "")
    x = x.astype(float)
    return x


def preprocess_companies(companies: pd.DataFrame) -> pd.DataFrame:

    companies["iata_approved"] = _is_true(companies["iata_approved"])
    companies["company_rating"] = _parse_percentage(companies["company_rating"])
    return companies


def preprocess_shuttles(shuttles: pd.DataFrame) -> pd.DataFrame:

    shuttles["d_check_complete"] = _is_true(shuttles["d_check_complete"])
    shuttles["moon_clearance_complete"] = _is_true(shuttles["moon_clearance_complete"])
    shuttles["price"] = _parse_money(shuttles["price"])
    return shuttles

def create_model_input_table(
    shuttles: pd.DataFrame, companies: pd.DataFrame, reviews: pd.DataFrame
) -> pd.DataFrame:

    rated_shuttles = shuttles.merge(reviews, left_on="id", right_on="shuttle_id")
    model_input_table = rated_shuttles.merge(
        companies, left_on="company_id", right_on="id"
    )
    model_input_table = model_input_table.dropna()
    return model_input_table


####################
# Model evaluation #
####################

from typing import Dict, Tuple
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

def split_data(data: pd.DataFrame, parameters: Dict) -> Tuple:
    X = data[parameters["features"]]
    y = data["price"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=parameters["test_size"], random_state=parameters["random_state"]
    )
    return X_train, X_test, y_train, y_test


def train_model(X_train: pd.DataFrame, y_train: pd.Series) -> LinearRegression:
    regressor = LinearRegression()
    regressor.fit(X_train, y_train)
    return regressor


def evaluate_model(
    regressor: LinearRegression, X_test: pd.DataFrame, y_test: pd.Series
):
    y_pred = regressor.predict(X_test)
    print(r2_score(y_test, y_pred))

    
# Call data processing functions
preprocessed_companies = preprocess_companies(companies)
preprocessed_shuttles = preprocess_shuttles(shuttles)
model_input_table = create_model_input_table(preprocessed_shuttles, preprocessed_companies, reviews)

# Call model evaluation functions
X_train, X_test, y_train, y_test = split_data(model_input_table, conf_params["model_options"])
regressor = train_model(X_train, y_train)
evaluate_model(regressor, X_test, y_test)    
```

```python

```
