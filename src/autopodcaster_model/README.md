# AutoPodcaster Model

This is the model for the AutoPodcaster project. It contains all common classes that represents model objects like input, output, etc.

## Create the wheel

To create the wheel, run the following command in the root of the AutoPodcaster model:

1. Install the dependencies

    ```bash
    pip install -r requirements.txt
    ```

1. Create the wheel

    ```bash
    python setup.py bdist_wheel
    ```

The wheel will be created in the `dist` folder and can be installed in other projects.

## Install the wheel

To install the wheel in another project, run the following command:

```bash
pip install dist/auto_podcaster_model-<version>-py3-none-any.whl
```

Where `<version>` is the version of the wheel.

> [!NOTE]
> It needs to be installed in the same virtual environment where the agent / microservice is running.

## Usage

To use the model in another project, import the classes from the `auto_podcaster_model` package:

```python
from autopodcaster_model import Input
```
