# Common use cases

## Use Hooks to extend a node's behaviour

You can use the [`before_node_run` and `after_node_run` Hooks](/kedro.framework.hooks.specs.NodeSpecs) to add extra behavior before and after a node's execution. Furthermore, you can apply extra behavior to not only an individual node or an entire Kedro pipeline, but also to a _subset_ of nodes, based on their tags or namespaces: for example, suppose we want to add the following extra behavior to a node:

```python
from kedro.pipeline.node import Node


def say_hello(node: Node):
    """An extra behaviour for a node to say hello before running."""
    print(f"Hello from {node.name}")
```

Then you can either add it to a single node based on the node's name:

```python
# src/<package_name>/hooks.py

from kedro.framework.hooks import hook_impl
from kedro.pipeline.node import Node


class ProjectHooks:
    @hook_impl
    def before_node_run(self, node: Node):
        # adding extra behaviour to a single node
        if node.name == "hello":
            say_hello(node)
```

Or add it to a group of nodes based on their tags:


```python
# src/<package_name>/hooks.py

from kedro.framework.hooks import hook_impl
from kedro.pipeline.node import Node


class ProjectHooks:
    @hook_impl
    def before_node_run(self, node: Node):
        if "hello" in node.tags:
            say_hello(node)
```

Or add it to all nodes in the entire pipeline:

```python
# src/<package_name>/hooks.py

from kedro.framework.hooks import hook_impl
from kedro.pipeline.node import Node


class ProjectHooks:
    @hook_impl
    def before_node_run(self, node: Node):
        # adding extra behaviour to all nodes in the pipeline
        say_hello(node)
```

If your use case takes advantage of a decorator, for example to retry a node's execution using a library such as [tenacity](https://tenacity.readthedocs.io/en/latest/), you can still decorate the node's function directly:

```python
from tenacity import retry


@retry
def my_flaky_node_function():
    ...
```

Or applying it in the `before_node_run` Hook as follows:

```python
# src/<package_name>/hooks.py
from tenacity import retry

from kedro.framework.hooks import hook_impl
from kedro.pipeline.node import Node


class ProjectHooks:
    @hook_impl
    def before_node_run(self, node: Node):
        # adding retrying behaviour to nodes tagged as flaky
        if "flaky" in node.tags:
            node.func = retry(node.func)
```
## Use Hooks to customise the dataset load and save methods
We recommend using the `before_dataset_loaded`/`after_dataset_loaded` and `before_dataset_saved`/`after_dataset_saved` Hooks to customise the dataset `load` and `save` methods where appropriate.

For example, you can add logging about the dataset load runtime as follows:

```python
@property
def _logger(self):
    return logging.getLogger(self.__class__.__name__)


@hook_impl
def before_dataset_loaded(self, dataset_name: str) -> None:
    start = time.time()
    self._logger.info("Loading dataset %s started at %0.3f", dataset_name, start)


@hook_impl
def after_dataset_loaded(self, dataset_name: str, data: Any) -> None:
    end = time.time()
    self._logger.info("Loading dataset %s ended at %0.3f", dataset_name, end)
```
