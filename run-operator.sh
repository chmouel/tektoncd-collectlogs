#!/usr/bin/env bash
set -eu

[[ -n ${TARGET_NAMESPACE} ]] && args="-n ${TARGET_NAMESPACE}"
[[ -e ./operator/collectlogs.py ]] && operator_path=./operator/collectlogs.py
[[ -e /src/collectlogs.py ]] && operator_path=/src/collectlogs.py


exec kopf run ${args} ${operator_path}
