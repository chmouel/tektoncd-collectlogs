#!/usr/bin/env bash
set -eu

exec kopf run ./operator/collectlogs.py
