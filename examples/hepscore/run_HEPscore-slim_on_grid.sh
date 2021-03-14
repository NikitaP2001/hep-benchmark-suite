#!/bin/bash

#####################################################################
# This script of example installs and runs the HEP-Benchmark-Suite
# The Suite configuration file 
#       bmkrun_config_job.yml 
# is included in the script itself.
# The configuration script enables the benchmarks to run
# and defines some meta-parameters, including tags as the SITE name.  
# 
# In this example only the HEP-score benchmark is configured to run.
# It runs with a slim configuration hepscore_slim.yml ideal to run
# in grid jobs (average duration: 40 min) 
#
# The only requirements to run are
# git python3-pip singularity 
#####################################################################

#----------------------------------------------
# Replace somesite with a meaningful site name
SITE=somesite
#----------------------------------------------


echo "Running script: $0"
cd $( dirname $0)

WORKDIR=`pwd`/workdir

mkdir -p $WORKDIR
chmod a+rw -R $WORKDIR

cat > $WORKDIR/hepscore_slim.yml <<'EOF' 
hepscore_benchmark:
  benchmarks:
    cms-gen-sim-bmk:
      ref_scores:
        gen-sim: 0.726
      weight: 1.0
      version: v2.1
      args:
        threads: 4
        events: 20
    cms-digi-bmk:
      ref_scores:
        digi: 3.58
      weight: 1.0
      version: v2.1
      args:
        threads: 4
        events: 50
    cms-reco-bmk:
      ref_scores:
        reco: 2.196
      weight: 1.0
      version: v2.1
      args:
        threads: 4
        events: 50
  settings:
    name: HEPscoreSlim20
    reference_machine: "CPU Intel(R) Xeon(R) CPU E5-2630 v3 @ 2.40GHz"
    registry: dir:///cvmfs/unpacked.cern.ch/gitlab-registry.cern.ch/hep-benchmarks/hep-workloads
    method: geometric_mean
    repetitions: 1
    retries: 1
    scaling: 355
    container_exec: singularity
EOF

cat > $WORKDIR/bmkrun_config_job.yml <<EOF2 
activemq:
  server: dashb-mb.cern.ch
  topic: /topic/vm.spec
  port: 61123  # Port used for certificate
  ## include the certificate full path (see documentation)
  key: 'userkey.pem'
  cert: 'usercert.pem'

global:
  benchmarks:
  - hepscore
  mode: singularity
  publish: false
  rundir: $WORKDIR/suite_results
  show: true
  tags:
    site: $SITE

hepscore:
  config: hepscore_slim.yml
  version: v1.0
  options:
      userns: True
      clean: True
EOF2

cd $WORKDIR
export MYENV="env_bmk"        # Define the name of the environment.
python3 -m venv $MYENV        # Create a directory with the virtual environment.
source $MYENV/bin/activate    # Activate the environment.
python3 -m pip install git+https://gitlab.cern.ch/hep-benchmarks/hep-benchmark-suite.git@v2.0
cat bmkrun_config_job.yml
bmkrun -c bmkrun_config_job.yml

echo "You are in python environment $MYENV. run \`deactivate\` to exit from it"
