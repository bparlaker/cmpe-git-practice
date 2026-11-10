#!/usr/bin/env bash
# Render runs this script every time I push to GitHub.
# "set -o errexit" stops the build if any command fails.
set -o errexit

pip install -r requirements.txt

# Collect the CSS and JS files into one folder for WhiteNoise.
python manage.py collectstatic --no-input

# Create or update the database tables.
python manage.py migrate

# Add the categories, colors and predefined craft types (safe to run again).
python manage.py load_initial_data
