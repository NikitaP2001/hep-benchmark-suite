#!/bin/bash

#####################################################################
# This example script installs and runs the HEP-Benchmark-Suite
# The Suite configuration file
#       bmkrun_config.yml
# is included in the script itself.
# The configuration script enables the benchmarks to run
# and defines some meta-parameters, including tags as the SITE name.
#
# In this example all the supported benchmarks are configured to run
#
# The only requirements to run are
# python3-pip singularity 
#####################################################################

#----------------------------------------------
# Replace somesite with a meaningful site name
SITE=somesite
#----------------------------------------------


echo "Running script: $0"
cd $( dirname $0)

WORKDIR=$(pwd)/workdir

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
  - hepscore
  - db12
  # - hs06
  # - spec2017
  # comment/uncomment any of the above benchmarks to exclude/include them
  mode: singularity
  publish: true
  rundir: /tmp/suite_results
  tags:
    site: $SITE

hepscore:
  version: v1.1
  config: default

hepspec06:
  # Use the docker registry
  image: "docker://gitlab-registry.cern.ch/hep-benchmarks/hep-spec/hepspec-cc7-multiarch:v2.2"
  # URL to fetch the hepspec06. It will only be used if the software
  # is  not found under hepspec_volume.

  # url_tarball: "_include_path_to_HS06_tarball_if_not_unpacked_already_in_hepspec_volume_"

  # Define the location on where hepspec06 should be found
  # If hepspec06 is not present, the directory should be writeable
  # to allow the installation via the url_tarball
  hepspec_volume: "/tmp/SPEC"

  ## Number of iterations to run the benchmark
  iterations: 3
  ## Specifies if benchmark is run on 32 or 64 bit mode
  ## Default is 64-bit
  # mode: 32

spec2017:
  # Use the docker registry
  image: "docker://gitlab-registry.cern.ch/hep-benchmarks/hep-spec/hepspec-cc7-multiarch:v2.2"
  # URL to fetch the spec cpu 2017. It will only be used if the software
  # is  not found under hepspec_volume.

  # url_tarball: "_include_path_to_spec2017_tarball_if_not_unpacked_already_in_hepspec_volume_"

  # Define the location on where spec cpu 2017 should be found
  # If spec cpu 2017 is not present, the directory should be writeable
  # to allow the installation via the url_tarball
  hepspec_volume: "/tmp/SPEC"

  ## Number of iterations to run the benchmark
  iterations: 3

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
