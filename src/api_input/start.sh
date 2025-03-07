# !/bin/bash

# Check if you are in virtual environment or run the setup
if [[ $VIRTUAL_ENV == "" ]]
then
    source setup.sh
fi

# Run the API
fastapi run api_input.py --port 8081