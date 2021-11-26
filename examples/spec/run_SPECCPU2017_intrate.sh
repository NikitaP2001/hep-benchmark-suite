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
# In this example only the SPEC CPU 2017 Int Rate is configured to run.
# ****** IMPORTANT ********
# In order to run, the SPEC CPU 2017 package needs to be available in the
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
# > curl -O https://gitlab.cern.ch/hep-benchmarks/hep-benchmark-suite/-/raw/master/examples/spec/run_SPECCPU2017_intrate.sh
# > chmod u+x run_SPECCPU2017_intrate.sh
# - MANDATORY: EDIT the user editable section
# > ./run_SPECCPU2017_intrate.sh
#####################################################################

#--------------[Start of user editable section]---------------------- 
SITE=somesite  # Replace somesite with a meaningful site name
PURPOSE="a test"
PUBLISH=false  # Replace false with true in order to publish results in AMQ
CERTIFKEY=path_to_user_key_pem  
CERTIFCRT=path_to_user_cert_pem
HEPSPEC_VOLUME=path_to_SPEC_installation # Make sure this directory is writable
#--------------[End of user editable section]------------------------- 


echo "Running script: $0"
cd $( dirname $0)

WORKDIR=$(pwd)/workdir
echo "Creating the WORKDIR $WORKDIR"
mkdir -p $WORKDIR
chmod a+rw -R $WORKDIR

cat > $WORKDIR/bmkrun_config.yml <<EOF2 
activemq:
  server: dashb-mb.cern.ch
  topic: /topic/vm.spec
  port: 61123  # Port used for certificate
  ## include the certificate full path (see documentation)
  key: $CERTIFKEY
  cert: $CERTIFCRT

global:
  benchmarks:
  - spec2017
  mode: singularity
  publish: $PUBLISH
  rundir: /tmp/suite_results
  tags:
    site: $SITE
    purpose: "$PURPOSE"

spec2017:
  # Use the docker registry
  image: "docker://gitlab-registry.cern.ch/hep-benchmarks/hep-spec/hepspec-cc7-multiarch:v2.3"
  
  # URL to fetch the spec cpu 2017. It will only be used if the software is not found under hepspec_volume.
  # use file:// for local files, https:// for web url
  # url_tarball: "[file|https]://_include_path_to_spec2017_tarball_if_not_unpacked_already_in_hepspec_volume_"

  # Define the location on where spec cpu 2017 should be found
  # If spec cpu 2017 is not present, the directory should be writeable
  # to allow the installation via the url_tarball
  hepspec_volume: "$HEPSPEC_VOLUME"

  ## Number of iterations to run the benchmark
  iterations: 3

  # Run the bset named "Int Rate" defined in 
  # https://gitlab.cern.ch/hep-benchmarks/hep-spec/-/blob/master/scripts/spec2017/intrate.bset
  # for any other bset to run, change this parameter accordingly and make sure the bset file
  # is stored in the location expected by specrun /benchspec/CPU/
  bmk_set: 'intrate'
  #bmk_set: '511.povray_r'

  ## Custom compiler configuration only for studies
  # config: a_spec_config_file_in_the_spec_repo_config
  # Default is https://gitlab.cern.ch/hep-benchmarks/hep-spec/-/blob/master/scripts/spec2017/cern-gcc-linux-x86.cfg
  # config: cern-gcc-linux-x86.cfg
EOF2

cd "$WORKDIR"
export MYENV="env_bmk"        # Define the name of the environment.
python3 -m venv $MYENV        # Create a directory with the virtual environment.
source $MYENV/bin/activate    # Activate the environment.

# Select Suite wheel version
PKG_VERSION="latest"          # The latest points always to latest stable release

# Select Python3 version (py37, py38)
PY_VERSION="py37"

if [ $PKG_VERSION = "latest" ];
then
  echo "Latest release selected."
  PKG_VERSION=$(curl --silent https://hep-benchmarks.web.cern.ch/hep-benchmark-suite/releases/latest)
fi

wheels_version="hep-benchmark-suite-wheels-${PY_VERSION}-${PKG_VERSION}.tar"
echo -e "-> Downloading wheel: $wheels_version \n"

curl -O "https://hep-benchmarks.web.cern.ch/hep-benchmark-suite/releases/${PKG_VERSION}/${wheels_version}"
tar xvf ${wheels_version}
python3 -m pip install suite_wheels/*.whl
cat bmkrun_config.yml
bmkrun -c bmkrun_config.yml

echo "You are in python environment $MYENV. run \`deactivate\` to exit from it"


