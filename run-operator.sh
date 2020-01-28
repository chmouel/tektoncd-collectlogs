#!/usr/bin/env bash
set -eu

[[ -n ${TARGET_NAMESPACE} ]] && args="-n ${TARGET_NAMESPACE}"

exec kopf run ${args} ./operator/collectlogs.py
