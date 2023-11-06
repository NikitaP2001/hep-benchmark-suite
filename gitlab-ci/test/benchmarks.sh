#!/bin/bash

set -x

yum install -y apptainer
yum install -y -q gettext moreutils git python3-pip
envsubst < $config | sponge $config   # Replace env variables in the config file
cat $config
export PATH=$PATH:$HOME/.local/bin    # $PATH cannot be modified in the variables section
python3 -m pip install -U pip wheel
# Script
python3 -m pip install --user .
bmkrun --mode=$executor --config=$config --rundir=$bmk_volume --benchmarks=$benchmark --ncores=$ncores | tee log
grep "with return code 0" log
