#!/bin/bash

#####################################################################
# This example script installs and runs the HEP-Benchmark-Suite
#
# The Suite configuration file
#       bmkrun_config.yml
# is included in the script itself.
# The configuration script enables the benchmarks to run
# and defines some meta-parameters, including tags as the SITE name.
#
# In this example only the HS06 at 32 bits benchmark is configured to run.
# ****** IMPORTANT ********
# In order to run, the HS06 package needs to be available in the
# location assigned to the hepspec_volume parameter.
# As an alternative a tarball needs to be passed to the suite by 
# the parameter url_tarball
#
# Requirements 
#    - Install: python3-pip singularity
#    - Define values for the parameters SITE and PURPOSE 
#    - Make available the x509 key/cert files for the publication 
#
#
# Example:
# > yum install -y python3-pip singularity
# > curl -O https://gitlab.cern.ch/hep-benchmarks/hep-benchmark-suite/-/raw/master/examples/spec/run_HS06_32bits.sh
# > chmod u+x run_HS06_32bits.sh
# - EDIT SITE and PURPOSE and location of key/cern
# > ./run_HS06_32bits.sh
#####################################################################

#----------------------------------------------
# Replace somesite with a meaningful site name
SITE=somesite
PURPOSE="a test"
#----------------------------------------------


echo "Running script: $0"
cd $( dirname $0)

WORKDIR=`pwd`/workdir
echo "Creating the WORKDIR $WORKDIR"
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
  image: "docker://gitlab-registry.cern.ch/hep-benchmarks/hep-spec/hepspec-cc7-multiarch:v2.3"

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
  mode: 32

  ## Custom compiler configuration only for studies
  ## Will invalidate the SPEC score results
  # config: a_spec_config_file_in_the_spec_repo_config
  # Default is https://gitlab.cern.ch/hep-benchmarks/hep-spec/-/blob/master/scripts/spec2k6/linux_gcc_cern.cfg
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
