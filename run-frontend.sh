#!/usr/bin/env bash
set -eu

export FLASK_ENV=development
export FLASK_APP=web.py

cd frontend/
flask run
