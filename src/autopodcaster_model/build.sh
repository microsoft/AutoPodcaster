#!/bin/bash

# Cleanup the previous build
rm -rf dist/
rm -rf build/
rm -rf autopodcaster_model.egg-info/

# Check if you are in virtual environment or run the setup
if [[ $VIRTUAL_ENV == "" ]]
then
    source setup.sh
fi

# Build the wheel
python setup.py bdist_wheel
