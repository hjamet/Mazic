[![libera manifesto](https://img.shields.io/badge/libera-manifesto-lightgrey.svg)](https://liberamanifesto.com)

# Mazic

## Description

Mazic is a cooperative game where players take on the role of mages exploring a magical labyrinth filled with dangerous creatures to recover powerful artifacts. A terrifying legend has it that the souls of the mages who failed in their quest are trapped in the labyrinth and haunt the place, ready to do anything to prevent newcomers from escaping.

## Installation 🐼

We use Poetry for managing virtual environments & installing dependencies. 

### Prerequisites

- Python 3.9.7 (or higher)
- Poetry

### Steps

1. **Clone the repository:**
    ```sh
    git clone https://github.com/yourusername/mazic.git
    cd mazic
    ```

2. **Install Python 3.9.7:**
    - You can use **Pyenv** to install it. See [pyenv](https://github.com/pyenv/pyenv).

3. **Install dependencies:**
    ```sh
    poetry install
    ```

4. **Run the game:**
    ```sh
    poetry run python src/main.py
    ```

Alternatively, you can create a virtual environment, install the dependencies, and run the `src/main.py` file from the root of the repository:
```sh
python -m venv env
source env/bin/activate
python -m pip install -r requirements.txt
python src/main.py
```

Or you can run the Makefile with the following command:
```sh
make install
```

### You just want to play the Game...

Just go to the release tab and download the latest game version! 💃

## Do you want to get your hands dirty?

> **We are assuming you have Python 3.9.7 or higher installed on your machine.**

### Using Virtual Environment and pip

```sh
python -m venv env
source env/bin/activate
python -m pip install -r requirements.txt
python src/main.py
```

### Using Poetry

```sh
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Run the game
poetry run python src/main.py
```

## Repository Convention & Architecture 🦥

### Architecture 🦜

- The `src` directory contains the project's source code. Each Python file generally contains a class of the same name. The `main.py` file is the program's entry point. Subdirectories organize utilities by category.
- The `doc` directory contains the project's documentation. It can be generated using Pdoc3 (`make doc`).
- The `logs` directory contains the project's logs. These are generated using the `src.Logger` class and are saved in a `xxx.log` file and displayed in the console.
- The `assets` directory contains the project's assets, including images used for the graphical interface.

### Convention 🦦

- **[DOCSTRING]**: We use typed Google docstrings for all functions and methods. See [PEP 484](https://www.python.org/dev/peps/pep-0484/) and [Sphinxcontrib Napoleon](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html). Docstrings and notebooks should be written in English. Each function and class should have a brief usage example in its docstring.
- **[GIT]**: We use the commit convention described here: [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/). You should never work on the master branch but on a branch named after the feature you are working on after opening an issue to let other members know what you are working on so that you can discuss it. When you are done, you can open a pull request to merge your branch into master. We will then review your code and merge it if everything is okay. Issues and pull requests can be written in French.

> Of course, anyone who doesn't follow these rules, arbitrarily written by a tyrannical mind, is subject to judgmental looks, cookie embargoes, and denunciatory messages with angry animal emojis.

## Contributing

We welcome contributions from the community! Here are some ways you can help:

1. **Report Bugs:** If you find a bug, please report it by opening an issue.
2. **Suggest Features:** If you have an idea for a new feature, please open an issue to discuss it.
3. **Submit Pull Requests:** If you want to contribute code, please fork the repository and submit a pull request.

### How to Contribute

1. **Fork the repository:**
    ```sh
    git fork https://github.com/hjamet/Mazic.git
    ```

2. **Create a new branch:**
    ```sh
    git checkout -b feature-name
    ```

3. **Make your changes and commit them:**
    ```sh
    git commit -m "feat: add new feature"
    ```

4. **Push to the branch:**
    ```sh
    git push origin feature-name
    ```

5. **Open a pull request:**
    - Go to the repository on GitHub and click on "New Pull Request".

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to all the contributors who have helped make this project better.
- Special thanks to the open-source community for their invaluable support and contributions.