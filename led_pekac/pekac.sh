#!/bin/bash

set -ex
pushd /sys/class/pwm/pwmchip0
echo 0 > export || true
echo 1 > export || true
echo 40000 > pwm0/period
echo 1 > pwm0/enable
echo 40000 > pwm1/period
echo 1 > pwm1/enable
popd
python3 -u $(dirname "$0")/pekac.py
