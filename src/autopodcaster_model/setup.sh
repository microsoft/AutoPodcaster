# !/bin/bash

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
