from pathlib import Path

from kedro.templates.project.hooks.utils import (

    setup_template_add_ons,
    sort_requirements,
)
from kedro.framework.cli.starters import _parse_add_ons_input

def main():
    current_dir = Path.cwd()
    requirements_file_path = current_dir / "requirements.txt"
    pyproject_file_path = current_dir / "pyproject.toml"

    # Get the selected add-ons from cookiecutter
    selected_add_ons = "{{ cookiecutter.add_ons }}"

    # Handle template directories and requirements according to selected add-ons
    setup_template_add_ons(selected_add_ons, requirements_file_path, pyproject_file_path)

    # Sort requirements.txt file in alphabetical order
    sort_requirements(requirements_file_path)

if __name__ == "__main__":
    main()
