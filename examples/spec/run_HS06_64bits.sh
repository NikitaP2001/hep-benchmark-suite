#!/bin/bash

#####################################################################
# This example script installs and runs the HEP-Benchmark-Suite
#
# The Suite configuration file
#       bmkrun_config.yml
# is included in the script itself.
#
# The configuration script sets the benchmarks to run and
# defines some meta-parameters, including tags as the SITE name.
#
# The only requirements to run are
# git python3-pip singularity
#####################################################################


while getopts ':c:k:iprs:e:wd:b:v:' OPTION; do

  case "$OPTION" in
    c)
      cert="$(realpath $OPTARG)"
      echo "Setting certificate to $cert"
      ;;

    k)
      key="$(realpath $OPTARG)"
      echo "Setting key to $key"
      ;;

    i)
      install_only=true
      echo "Install only do not run"
      ;;
    r)
      run_only=true
      echo "Run only do not install"
      ;;
    p)
      publish=true
      echo "Results will be published"
      ;;
    s)
      site="$OPTARG"
      echo "Setting site to $site"
      ;;
    e)
      executor="$OPTARG"
      echo "Setting the container executor to $executor"
      ;;
    w)
      install_from_wheels=true
      echo "Installing the suite from wheels"
      ;;
    d)
      workdir="$(realpath $OPTARG)"
      echo "Setting the working directory to $workdir"
      ;;
    b)
      plugin_keys="$OPTARG"
      echo "Requesting to enable the following plugin keys ${plugin_keys}"
      ;;
    v)
      suite_version="$OPTARG"
      echo "Using suite version ${suite_version} instead of latest"
      ;;

    ?)
      echo "
Usage: $(basename $0) [OPTIONS]

Options:
  -c path       Path to the certificate to use to authenticate to AMQ
  -k path       Path to the key of the certificate used for AMQ
  -i            Install only, don't run the suite
  -r            Run only, skip installation
  -p            Publish the results to AMQ
  -s site       Site name to tag the results with
  -e executor   Container executor to use (singularity or docker)
  -d workdir    Set the working directory to workdir
  -w            Install the suite from wheels rather than the repository"
      exit 1
      ;;
  esac

done

#--------------[Start of user editable section]----------------------
SITE="${site}"  # Replace somesite with a meaningful site name
PUBLISH="${publish:-false}"  # Set to true in order to publish results in AMQ
CERTIFKEY="${key:-PATH_TO_CERT_KEY}"
CERTIFCRT="${cert:-PATH_TO_CERT}"
INSTALL_ONLY="${install_only:-false}"
RUN_ONLY="${run_only:-false}"
EXECUTOR="${executor:-singularity}"
INSTALL_FROM_WHEELS="${install_from_wheels:-false}"
WORKDIR="${workdir:-$(pwd)/workdir}"
#--------------[End of user editable section]-------------------------

# AMQ
SERVER=dashb-mb.cern.ch
PORT=61123
TOPIC=/topic/vm.spec

SCRIPT_VERSION="3.0"
HEPSCORE_VERSION="v1.5"
SUITE_VERSION=${suite_version-latest} # Use "latest" for the latest stable release

RUNDIR=$WORKDIR/suite_results
MYENV=$WORKDIR/env_bmk        # Define the name of the python environment
LOGFILE=$WORKDIR/output.txt
SUITE_CONFIG_FILE=$WORKDIR/bmkrun_config.yml
HEPSCORE_CONFIG_FILE=$WORKDIR/hepscore_config.yml
GiB_PER_CORE=1

SUPPORTED_PY_VERSIONS=(py36 py38 py39)
DEFAULT_PY_VERSION="py36"

declare -A registries=( ["singularity"]="oras" ["docker"]="docker" )
declare -A registry_suffixes=( ["singularity"]="-sif" ["docker"]="" )
REGISTRY="${registries[$EXECUTOR]}"
REGISTRY_SUFFIX="${registry_suffixes[$EXECUTOR]}"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
ORANGE='\033[1;33m'
NC='\033[0m' # No Color

echo "Running script: $0 - version: $SCRIPT_VERSION"
cd $( dirname $0)

create_workdir(){
    if [ ! -d $WORKDIR ]; then
        echo "Creating the WORKDIR $WORKDIR"
        mkdir -p $WORKDIR
        chmod a+rw -R $WORKDIR
    fi
}

create_python_venv(){
    python3 -m venv $MYENV        # Create a directory with the virtual environment
    source $MYENV/bin/activate    # Activate the environment
}

validate_params(){
    validate_site
    validate_publish
    validate_container_executor
}

validate_site(){
    if [ -z "$SITE" ]; then
        echo "The site name is not set. Please use the -s SITE option or set the SITE variable in the script."
        exit 1
    fi
}

validate_publish(){
    if [ $PUBLISH == true ]; then
        if [ $CERTIFKEY == 'PATH_TO_CERT_KEY' ]; then
            echo "The certificate key is not set. Please set the CERTIFKEY variable in the script."
            exit 1
        fi

        if [ $CERTIFCRT == 'PATH_TO_CERT' ]; then
            echo "The certificate is not set. Please set the CERTIFCRT variable in the script."
            exit 1
        fi
    fi
}

validate_container_executor(){
    if [ -z "${REGISTRY}" ]; then
        echo "The executor has got to be one of: ${!registries[@]}. Wrong input value: $executor"
        exit 1
    fi
}

create_config_file(){
    # CONFIG_FILE_CREATION
    cat > $SUITE_CONFIG_FILE <<EOF2
activemq:
  server: $SERVER
  topic: $TOPIC
  port: $PORT
  ## include the certificate full path (see documentation)
  key: $CERTIFKEY
  cert: $CERTIFCRT

global:
  benchmarks:
  - hs06
  mode: $EXECUTOR
  publish: $PUBLISH
  rundir: $RUNDIR
  show: true
  tags:
    site: $SITE
  pre-stage-duration: 2
  post-stage-duration: 2
  
hs06:
  # Use the docker registry
  image: "docker://gitlab-registry.cern.ch/hep-benchmarks/hep-spec/hepspec-cc7-multiarch:v2.3"
 
  # URL to fetch the hepspec06. It will only be used if the software is  not found under hepspec_volume.
  # use file:// for local files, https:// for web url
  # url_tarball: "[file|https]://this_is_dummy_replace_me"

  # Define the location on where hepspec06 should be found
  # If hepspec06 is not present, the directory should be writeable
  # to allow the installation via the url_tarball
  hepspec_volume: "$HEPSPEC_VOLUME"

  ## Number of iterations to run the benchmark
  iterations: 3
  ## Specifies if benchmark is run on 32 or 64 bit mode
  ## Default is 64-bit
  mode: 64
  
  ## Custom compiler configuration only for studies
  ## Will invalidate the SPEC score results
  # config: a_spec_config_file_in_the_spec_repo_config
  # Default is https://gitlab.cern.ch/hep-benchmarks/hep-spec/-/blob/master/scripts/spec2k6/linux_gcc_cern.cfg  

$SUITE_PLUGINS_CONFIG
EOF2

    if [ -f $HEPSCORE_CONFIG_FILE ]; then
        cat $HEPSCORE_CONFIG_FILE
    fi
}

create_plugin_configuration() {
    # Skip if version is lower than 3.0

    [[ -z $plugin_keys ]] && return

    # Allowed plugin keys
    ALLOWED_PLUGIN_KEYS="f l m s p"

    # Check if the suite version is above a given version
    if [[ ! "$SUITE_VERSION" =~ ^[3-9]\.[[:alnum:]]*$ && ! "$SUITE_VERSION" =~ ^qa$ ]]; then
      echo "Suite version ${SUITE_VERSION} is not adequate to run plugins. Exiting."
      return 1
    fi

    collect_cpu_frequency=false
    collect_load=false
    collect_memory_usage=false
    collect_swap_usage=false
    collect_power_consumption=false

    for pkey in ${ALLOWED_PLUGIN_KEYS[@]}; do
      if [[ "$plugin_keys" =~ (^|.*,)"$pkey"(,.*|$) ]]; then
        case $pkey in
          f)
            collect_cpu_frequency=true
            ;;
          l)
            collect_load=true
            ;;
          m)
            collect_memory_usage=true
            ;;
          s)
            collect_swap_usage=true
            ;;
          p)
            collect_power_consumption=true
            ;;
          *)
            echo "Unexpected plugin key $pkey. Ignoring it"
            ;;
        esac
      fi
    done

    # Print the status of each collection flag
    echo "collect_cpu_frequency: $collect_cpu_frequency"
    echo "collect_load: $collect_load"
    echo "collect_memory_usage: $collect_memory_usage"
    echo "collect_swap_usage: $collect_swap_usage"
    echo "collect_power_consumption: $collect_power_consumption"


    METRICS_CONFIG=""

    if [ "$collect_cpu_frequency" = true ]; then
      METRICS_CONFIG="$METRICS_CONFIG
      cpu-frequency:
        command: cpupower frequency-info -f
        regex: 'current CPU frequency: (?P<value>\d+).*'
        unit: kHz
        interval_mins: 1"
    fi

    if [ "$collect_load" = true ]; then
      METRICS_CONFIG="$METRICS_CONFIG
      load:
        command: uptime
        regex: 'load average: (?P<value>\d+.\d+),'
        unit: ''
        interval_mins: 1"
    fi

    if [ "$collect_memory_usage" = true ]; then
      METRICS_CONFIG="$METRICS_CONFIG
      used-memory:
        command: free -m
        regex: 'Mem: *(\d+) *(?P<value>\d+).*'
        unit: MiB
        interval_mins: 1"
    fi

    if [ "$collect_swap_usage" = true ]; then
      METRICS_CONFIG="$METRICS_CONFIG
      used-swap-memory:
        command: free -m
        regex: 'Swap: *\d+ *(?P<value>\d+).*'
        unit: MiB
        interval_mins: 1"
    fi

    if [ "$collect_power_consumption" = true ]; then
      METRICS_CONFIG="$METRICS_CONFIG
      power-consumption1:
        description: 'Retrieves power consumption of the system. Requires elevated privileges.'
        command: 'ipmitool dcmi power reading'
        regex: 'Instantaneous power reading:\\s*(?P<value>\\d+) Watts'
        interval_mins: 1
        unit: 'W'"
    fi

    #  If plugins are requested include them in the config
    if [ -n "$METRICS_CONFIG" ]; then
        SUITE_PLUGINS_CONFIG="
plugins:
  CommandExecutor:
    metrics: $METRICS_CONFIG
"
    fi
}

hepscore_install(){

    validate_params
    create_python_venv
    install_suite

}

install_suite(){
    if [ $SUITE_VERSION = "latest" ];  then
        SUITE_VERSION=$(curl --silent https://hep-benchmarks.web.cern.ch/hep-benchmark-suite/releases/latest)
        echo "Latest suite release selected: ${SUITE_VERSION}"
    fi
    
    if [ $INSTALL_FROM_WHEELS == true ]; then
        install_suite_from_wheels
    else
        install_suite_from_repo
    fi
}

install_suite_from_repo(){
    pip3 install --upgrade pip
    pip3 install git+https://gitlab.cern.ch/hep-benchmarks/hep-score.git@$HEPSCORE_VERSION
    pip3 install git+https://gitlab.cern.ch/hep-benchmarks/hep-benchmark-suite.git@$SUITE_VERSION
}

install_suite_from_wheels() {
    # Try to get system's default python3 and see if it's one of the supported version; fallback to the default otherwise
    PY_VERSION=$(python3 -V | awk '{split($2, version, "."); print "py"version[1] version[2]}')

    if [[ ! "$PY_VERSION" =~ ^py3[0-9]{1,2}$ ]] || [[ ! " ${SUPPORTED_PY_VERSIONS[*]} " =~ " ${PY_VERSION} " ]]; then
        echo "Your default python3 version (${PY_VERSION}) isn't supported. Falling back to ${DEFAULT_PY_VERSION}."
        PY_VERSION=$DEFAULT_PY_VERSION
    fi

    # Get appropriate wheels
    ARCH=$(uname -m)
    GLIBC=$(ldd --version | awk 'NR==1 {gsub(/\./,"_",$NF); print $NF}')

    if [[ $SUITE_VERSION =~ ^v ]];  then
        wheels_version="hep-benchmark-suite-wheels-${PY_VERSION}-${ARCH}-${SUITE_VERSION}.tar"  # Old format < 3.0
    else
        wheels_version="hep-benchmark-suite-wheels-${SUITE_VERSION}-${PY_VERSION}-none-linux_${GLIBC}_${ARCH}.tar" # New format >= 3.0
    fi

    # Find dev versions too
    wheels_path=""
    if ! [[ $SUITE_VERSION =~ ^[0-9v] ]]; then
        wheels_path="dev/"
    fi
    
    # Download and extract the wheels
    echo -e "-> Downloading wheel: $wheels_version \n"    
    curl -O "https://hep-benchmarks.web.cern.ch/hep-benchmark-suite/releases/${wheels_path}${SUITE_VERSION}/${wheels_version}"
    tar xvf ${wheels_version}

    # Update pip before installing any other wheel
    if ls suite_wheels*/pip* 1> /dev/null 2>&1; then
        python3 -m pip install suite_wheels*/pip*.whl
    fi

    python3 -m pip install suite_wheels*/*.whl
    rm -rf suite_wheels*
}

ensure_suite_is_not_running() {
    PS_AUX_BMKRUN=$(ps aux | grep -c bmkrun)
    if (( PS_AUX_BMKRUN > 1 )); then
        echo -e "${ORANGE}Another instance of the HEP Benchmark Suite is already running. Please wait for it to finish before running the suite again.${NC}"
        exit 1
    fi
}

create_tarball() {
    # Create tarball to be sent to the admins if the suite failed but still produced data
    if [ $SUITE_SUCCESSFUL -ne 0 ] && [ $RUNDIR_DATE ] ;
    then
        LOG_TAR="${SITE}_${RUNDIR_DATE}.tar"
        find $RUNDIR/$RUNDIR_DATE/ \( -name archive_processes_logs.tgz -o -name hep-benchmark-suite.log -o -name HEPscore*.log \) -exec tar -rf $LOG_TAR {} &>/dev/null \;
            echo -e "${ORANGE}\nThe suite has run into errors. If you need help from the administrators, please contact them by email and attach ${WORKDIR}/${LOG_TAR} to it ${NC}"
    fi
}

print_amq_send_command() {
    # Print command to send results if they were produced but not sent
    if [ $RESULTS ] && { [ $PUBLISH == false ] || [ $AMQ_SUCCESSFUL -ne 0 ] ; }; then
        echo -e "${GREEN}\nThe results were not sent to AMQ. In order to send them, you can run (--dryrun option available):"
        echo -e "${MYENV}/bin/bmksend -c ${SUITE_CONFIG_FILE} ${RUNDIR} ${NC}"
    fi
}

check_memory_difference() {
    # Print warning message in case of memory increase
    MEM_DIFF=$(($MEM_AFTER - $MEM_BEFORE))
    if (( MEM_DIFF > 1048576 )); then
      echo -e "${ORANGE}The memory usage has increased by more than 1 GiB since the start of the script. Please check there are no zombie processes in the machine before running the script again.${NC}"
    fi
}

check_workdir_space() {
    # Check if there is enough space in the workdir
    workdir_space=$(df -k $WORKDIR | awk 'NR==2 {print $4}')
    minimum_space=$((GiB_PER_CORE * 1024 * 1024 * $(nproc)))
    if (( workdir_space < minimum_space )); then
        echo -e "${ORANGE}There is less than $((minimum_space/1024/1024))GiB of space left in the workdir ($((workdir_space/1024/1024))GiB). Please free some space before running the script again.${NC}"
        exit 1
    fi
}

hepscore_run(){

    if [[ -d $WORKDIR && -f $MYENV/bin/activate ]]; then 
	    source $MYENV/bin/activate
    else
	    echo "The suite installation cannot be found; please run $0 to install and run it or $0 -i to install it only"
        exit 1
    fi

    ensure_suite_is_not_running
    check_workdir_space

    MEM_BEFORE=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
    bmkrun -c $SUITE_CONFIG_FILE | tee -i $LOGFILE
    MEM_AFTER=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)

    RESULTS=$(awk '/Full results can be found in.*/ {print $(NF-1)}' $LOGFILE)
    RUNDIR_DATE=$(perl -n -e'/^.*(run_2[0-9]{3}-[0-9]{2}-[0-9]{2}_[0-9]{4}).*$/ && print $1; last if $1' $LOGFILE)
    SUITE_SUCCESSFUL=$(! grep -q ERROR $LOGFILE; echo $?)
    AMQ_SUCCESSFUL=$(grep -q "Results sent to AMQ topic" $LOGFILE; echo $?)
    rm -f $LOGFILE

    create_tarball
    print_amq_send_command
    check_memory_difference
}


# Always done so options are taken into account
create_workdir
cd $WORKDIR
create_config_file

if [[ $INSTALL_ONLY == false && $RUN_ONLY == false ]] ; then

    hepscore_install
    hepscore_run

elif [[ $INSTALL_ONLY == true  && $RUN_ONLY == false ]] ; then
    hepscore_install

elif [[ $RUN_ONLY == true && $INSTALL_ONLY == false ]] ; then 
    hepscore_run

else 
    echo "You can't use -i and -r together."

fi