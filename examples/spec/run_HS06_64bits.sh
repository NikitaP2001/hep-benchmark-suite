#!/bin/bash

#####################################################################
# This script of example installs and runs the HEP-Benchmark-Suite
# The Suite configuration file
#       bmkrun_config.yml
# is included in the script itself.
# The configuration script enables the benchmarks to run
# and defines some meta-parameters, including tags as the SITE name.
#
# In this example only the HS06 at 64 bits benchmark is configured to run.
# In order to run, the HS06 package needs to be available in the
# # location specified by hepspec_volume
# or a tarball needs to be passed by url_tarball
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

cat > $WORKDIR/bmkrun_config.yml <<EOF2
activemq:
  server: dashb-mb.cern.ch
  topic: /topic/vm.spec
  port: 61123  # Port used for certificate
  ## include the certificate full path (see documentation)
  key: 'userkey.pem'
  cert: 'usercert.pem'

global:
  benchmarks:
  - hs06
  mode: singularity
  publish: true
  rundir: ${WORKDIR}/suite_results
  show: true
  tags:
    site: $SITE

hepspec06:
  # Use the docker registry
  image: "docker://gitlab-registry.cern.ch/hep-benchmarks/hep-spec/hepspec-cc7-multiarch:v2.2"
 
  # URL to fetch the hepspec06. It will only be used if the software is  not found under hepspec_volume.
  # use file:// for local files, https:// for web url
  # url_tarball: "[file|https]://this_is_dummy_replace_me"

  # Define the location on where hepspec06 should be found
  # If hepspec06 is not present, the directory should be writeable
  # to allow the installation via the url_tarball
  hepspec_volume: "/tmp/SPEC"

  ## Number of iterations to run the benchmark
  iterations: 3
  ## Specifies if benchmark is run on 32 or 64 bit mode
  ## Default is 64-bit
  mode: 64
  ## Custom compiler configuration only for studies
  ## Will invalidate the SPEC score results
  # config: a_spec_config_file_in_the_spec_repo_config
EOF2

cd $WORKDIR
export MYENV="env_bmk"        # Define the name of the environment.
python3 -m venv $MYENV        # Create a directory with the virtual environment.
source $MYENV/bin/activate    # Activate the environment.
python3 -m pip install git+https://gitlab.cern.ch/hep-benchmarks/hep-benchmark-suite.git
cat bmkrun_config.yml

if [ `cat bmkrun_config.yml | grep "this_is_dummy_replace_me" | grep -c -v "#"` == 1 ];
then
  echo -e "\nERROR. You are using the url_tarball parameter. Please replace the dummy url with a real one"
  exit 1
fi
bmkrun -c bmkrun_config.yml

echo "You are in python environment $MYENV. run \`deactivate\` to exit from it"
