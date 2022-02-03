#!/usr/bin/env bash
# A simple script to pull workload images before launching parallel jobs
#
# This script will set $SINGULARITY_CACHEDIR, and pull the workloads enabled
# in the default config, or any other config passed to it.
#
# TODO: verify images in cache. Requires semantic mapping to hash 
# (currently unsupported in Singularity)
# USE:
# $ . populate_image_cache.sh [config.yml]
#
# if no config.yml is supplied, the default provided by the suite will be used


# Set to a directory that will be mounted in the same location on worker nodes
if [[ ! -v SINGULARITY_CACHEDIR ]]; then
  export SINGULARITY_CACHEDIR=$HOME/.singularity
  echo "SINGULARITY_CACHEDIR is not set. Setting to '$SINGULARITY_CACHEDIR'"
else
  echo "SINGULARITY_CACHEDIR set to '$SINGULARITY_CACHEDIR'"
fi

# If no config.yml provided, use latest
if [ "$#" -ne 1 ]; then
  echo "No config provided, using default config from latest release"
  #bmkrun -c default -s | awk '{if(/image: /) print $2}'
  HS06_IMG=$(curl -s https://gitlab.cern.ch/hep-benchmarks/hep-benchmark-suite/-/raw/master/hepbenchmarksuite/config/benchmarks.yml | awk '{if(/image: /) print $2}')
  HS_VERSION=$(curl -s https://gitlab.cern.ch/hep-benchmarks/hep-score/-/raw/master/hepscore/etc/hepscore-default.yaml)
  curl -s https://gitlab.cern.ch/hep-benchmarks/hep-score/-/raw/master/hepscore/etc/$HS_VERSION > tmp.yml
  HS_REGISTRY=$(cat tmp.yml | awk '{if(/registry: /) print $2}')
  HS_WL_NAME=$(cat tmp.yml | awk '/.*-bmk/')
  HS_WL_TAG=$(cat tmp.yml | awk '{if(/version: /) print $2}')
fi
echo ""
echo "HS06: $HS06_IMG"
echo ""
echo "HEPSCORE_VERSION: $HS_VERSION"
echo ""
echo "HS_REGISTRY: $HS_REGISTRY"
echo ""
echo "HS_WL_NAME: $HS_WL_NAME"
echo ""
echo "HS_WL_TAG: $HS_WL_TAG"

rm tmp.yml