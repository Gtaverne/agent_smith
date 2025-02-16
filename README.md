# To test the backend

## First check if python is installed
`python -version`

## Create a separate env in python using venv or conda
python3 -m venv name_of_your_environment

## Activate this environment
Then activate `source name_of_your_environment/bin/activate`

## Install the dependencies
Go to the root of the repo (not client or pipeline) and use `pip install -r requirements.txt`

## Get the Anthropic & firewrawl api keys in your .env
create a .env at the root of pipeline folder
get and add your keys in the .envEXEMPLE and turn it into a .env

## Lauch the server
Launch the server using python pipeline/app.py
