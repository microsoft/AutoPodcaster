# !/bin/bash

# Check if you are in virtual environment or run the setup
if [[ $VIRTUAL_ENV == "" ]]
then
    source setup.sh
fi

# Run the image indexer
python image_indexer.py