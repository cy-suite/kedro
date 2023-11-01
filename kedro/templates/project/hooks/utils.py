from pathlib import Path
import shutil
import toml

current_dir = Path.cwd()

lint_requirements = "black~=22.0\nruff~=0.0.290\n"
lint_pyproject_requirements = ["tool.ruff"]

test_requirements = "pytest-cov~=3.0\npytest-mock>=1.7.1, <2.0\npytest~=7.2"
test_pyproject_requirements = ["tool.pytest.ini_options", "tool.coverage.report"]

docs_pyproject_requirements = ["project.optional-dependencies"]


# Helper Functions
def remove_from_file(file_path, content_to_remove):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Split the content to remove into lines and remove trailing whitespaces/newlines
    content_to_remove_lines = [line.strip() for line in content_to_remove.split('\n')]

    # Keep lines that are not in content_to_remove
    lines = [line for line in lines if line.strip() not in content_to_remove_lines]

    with open(file_path, 'w') as file:
        file.writelines(lines)


def remove_nested_section(data, nested_key):
    keys = nested_key.split('.')
    d = data
    for key in keys[:-1]:
        if key in d:
            d = d[key]
        else:
            return  # Parent section not found, nothing to remove

    # Remove the nested section and any empty parent sections
    d.pop(keys[-1], None)
    for key in reversed(keys[:-1]):
        parent = data
        for k in keys[:keys.index(key)]:
            parent = parent[k]
        if not d:  # If the section is empty, remove it
            parent.pop(key, None)
            d = parent
        else:
            break  # If the section is not empty, stop removing


def remove_from_toml(file_path, sections_to_remove):
    # Load the TOML file
    with open(file_path, 'r') as file:
        data = toml.load(file)

    # Remove the specified sections
    for section in sections_to_remove:
        remove_nested_section(data, section)

    with open(file_path, 'w') as file:
        toml.dump(data, file)


def remove_dir(path):
    if path.exists():
        shutil.rmtree(str(path))


def remove_file(path):
    if path.exists():
        path.unlink()


def handle_starter_setup(selected_add_ons_list, python_package_name):
    # Remove all .csv and .xlsx files from data/01_raw/
    raw_data_path = current_dir / "data/01_raw/"
    for file_path in raw_data_path.glob("*.*"):
        if file_path.suffix in [".csv", ".xlsx"]:
            file_path.unlink()

    # Empty the contents of conf/base/catalog.yml
    catalog_yml_path = current_dir / "conf/base/catalog.yml"
    if catalog_yml_path.exists():
        catalog_yml_path.write_text('')
    # Remove parameter/reporting files from conf/base
    conf_base_path = current_dir / "conf/base/"
    if "Kedro Viz" in selected_add_ons_list:
        param_to_remove = ["parameters_data_processing.yml", "parameters_data_science.yml", "parameters_reporting.yml", "reporting.yml"]
    else:
        param_to_remove = ["parameters_data_processing.yml", "parameters_data_science.yml"]
    for param_file in param_to_remove:
        remove_file(conf_base_path / param_file)

    # Remove the pipelines subdirectories
    if "Kedro Viz" in selected_add_ons_list:
        pipelines_to_remove = ["data_science", "data_processing", "reporting"]
    else:
        pipelines_to_remove = ["data_science", "data_processing"]

    pipelines_path = current_dir / f"src/{python_package_name}/pipelines/"
    for pipeline_subdir in pipelines_to_remove:
        remove_dir(pipelines_path / pipeline_subdir)

    # Remove all test files from tests/pipelines/
    test_pipeline_path = current_dir / "tests/pipelines/test_data_science.py"
    remove_file(test_pipeline_path)


def setup_template_add_ons(selected_add_ons_list, requirements_file_path, pyproject_file_path, python_package_name):
    if "Linting" not in selected_add_ons_list:
        remove_from_file(requirements_file_path, lint_requirements)
        remove_from_toml(pyproject_file_path, lint_pyproject_requirements)

    if "Testing" not in selected_add_ons_list:
        remove_from_file(requirements_file_path, test_requirements)
        remove_from_toml(pyproject_file_path, test_pyproject_requirements)
        remove_dir(current_dir / "tests")

    if "Logging" not in selected_add_ons_list:
        remove_file(current_dir / "conf/logging.yml")

    if "Documentation" not in selected_add_ons_list:
        remove_from_toml(pyproject_file_path, docs_pyproject_requirements)
        remove_dir(current_dir / "docs")

    if "Data Structure" not in selected_add_ons_list:
        remove_dir(current_dir / "data")

    if "Pyspark" in selected_add_ons_list:
        handle_starter_setup(selected_add_ons_list, python_package_name)

    if "Kedro Viz" in selected_add_ons_list:
        handle_starter_setup(selected_add_ons_list, python_package_name)


def sort_requirements(requirements_file_path):
    """Sort the requirements.txt file in alphabetical order.

    Args:
        requirements_file_path: the path to the requirements.txt file.
    """
    with open(requirements_file_path, 'r') as requirements:
        lines = requirements.readlines()

    lines = [line.strip() for line in lines]
    lines.sort()
    sorted_content = '\n'.join(lines)

    with open(requirements_file_path, 'w') as requirements:
        requirements.write(sorted_content)
