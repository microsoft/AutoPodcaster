# !/bin/bash

# Check if the wheel file exists if not build it
if [ ! -f "../autopodcaster_model/dist/autopodcaster_model-0.1.0-py3-none-any.whl" ]; then
    echo "Building the autopodcaster_model package"
    cd ../autopodcaster_model
    source build.sh
    cd ../api_input
fi

# Check if the virtual environment is already activated
if [[ $VIRTUAL_ENV != "" ]]
then
    echo "Deactivating the current virtual environment"
    deactivate
fi

# Create a new virtual environment and install the required packages
python -m venv .venv
source .venv/bin/activate

# Install the required packages
pip install -r requirements.txt

# Install the autopodcaster_model package
pip install ../autopodcaster_model/dist/autopodcaster_model-0.1.0-py3-none-any.whl
