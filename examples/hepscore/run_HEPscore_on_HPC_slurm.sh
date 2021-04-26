#!/bin/bash

# A simple slurm submission script showing off
# how to run the suite as a slurm batch job.
# This script runs the default configuration hepbenchmarksuite/config/benchmarks.yml
# on an array of 5 nodes.
# Each of the nodes is requested for exclusive use
# (to ensure no other users are running on the same node) with hyperthreading enabled.

# The script clears all slurm modules, and loads the minimal required set:
# python3 and singularity3.5.3+.
#!!!!! You may need to change these depending on what versions your site exposes (via `module avail`) !!!!!
# The batch job notifies on error or success (to the provided email),
# and outputs a tar archive of the resulting json and log files.

#SBATCH --exclusive --hint=multithread
#SBATCH --job-name=HEP-Benchmark-suite
#SBATCH --output=HEP-result-%A-%j.out
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=<your-notfication-address@domain>
#SBATCH --array=1-5

## allocate & run the below script once on each of 5 allocated nodes.
## nodes are requested in exclusive mode use with multithreading enabled.

module purge
# HEP suite requires singularity 3.5.3+, python3.
module load gcc singularity/3.5.3 python3/3.7.3

export RUNDIR=/tmp/HEP
export SUITE_BRANCH="master"

# example tag 'site':"my HPC..."
export BMKSUITE_TAG_SITE="my HPC site string to be included in JSON"

echo "Running HEP Benchmark Suite on $SLURM_CPUS_ON_NODE Cores"
# install suite as a module
mkdir -p "$RUNDIR"
python3 -m pip install --upgrade git+https://gitlab.cern.ch/hep-benchmarks/hep-benchmark-suite.git@${SUITE_BRANCH}

# run
"$HOME"/.local/bin/bmkrun --config default --tags --rundir "$RUNDIR"

# Copy local results to $HOME if not reporting via AMQ cp /tmp/HEP/result_profile.json $HOME/${SLURM_JOB_ID}_result.json
find ${RUNDIR} \( -name \*.json -o -name \*.log \) -exec tar -rvf "$HOME"/results-"${SLURM_JOB_ID}"-"${SLURM_ARRAY_JOB_ID}".tar {} +
