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
#
# Python version 3.9 or higher;
# python3-pip 
# Apptainer (version 1.1.6 or higher)
# git
#
# For additional information refer to 
# https://w3.hepix.org/benchmarking/how_to_run_HS23.html
#####################################################################


# --- Extract --config early ---
CONFIG_PATH=""
PARSED_ARGS=()
while [[ $# -gt 0 ]]; do
  if [[ "$1" == "--config" ]]; then
    CONFIG_PATH="$2"
    shift 2
  else
    PARSED_ARGS+=("$1")
    shift
  fi
done

# Read config file if specified
if [ -n "$CONFIG_PATH" ] && [ -f "$CONFIG_PATH" ]; then
  echo "Using config file: $CONFIG_PATH"
  args=()
  while IFS= read -r line || [ -n "$line" ]; do
    for arg in $line; do args+=("$arg"); done
  done < "$CONFIG_PATH"
  set -- "${args[@]}" "${PARSED_ARGS[@]}"
else
  set -- "${PARSED_ARGS[@]}"
fi

# Normalize long options to short ones
TEMP_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cert) TEMP_ARGS+=("-c" "$2"); shift 2;;
    --key) TEMP_ARGS+=("-k" "$2"); shift 2;;
    --install-only) TEMP_ARGS+=("-i"); shift;;
    --run-only) TEMP_ARGS+=("-r"); shift;;
    --publish) TEMP_ARGS+=("-p"); shift;;
    --site) TEMP_ARGS+=("-s" "$2"); shift 2;;
    --executor) TEMP_ARGS+=("-e" "$2"); shift 2;;
    --workdir) TEMP_ARGS+=("-d" "$2"); shift 2;;
    --wheels) TEMP_ARGS+=("-w"); shift;;
    --plugins) TEMP_ARGS+=("-b" "$2"); shift 2;;
    --suite-version) TEMP_ARGS+=("-v" "$2"); shift 2;;
    --hepscore-version) TEMP_ARGS+=("-x" "$2"); shift 2;;
    --ncores) TEMP_ARGS+=("-n" "$2"); shift 2;;
    --threadscan) TEMP_ARGS+=("-t"); shift;;
    --help) TEMP_ARGS+=("-?"); shift;;
    --*) echo "Unknown option: $1" >&2; exit 1;;
    *) TEMP_ARGS+=("$1"); shift;;
  esac
done

# Replace original arguments with normalized ones
set -- "${TEMP_ARGS[@]}"

# -- Argument parsing --
while getopts ':c:k:iprts:e:wd:b:v:x:n:' OPTION; do
  case "$OPTION" in
    c) cert="$(realpath "$OPTARG")"; echo "Setting certificate to $cert";;
    k) key="$(realpath "$OPTARG")"; echo "Setting key to $key";;
    i) install_only=true; echo "Install only do not run";;
    r) run_only=true; echo "Run only do not install";;
    p) publish=true; echo "Results will be published";;
    s) site="$OPTARG"; echo "Setting site to $site";;
    e) executor="$OPTARG"; echo "Setting the container executor to $executor";;
    w) install_from_wheels=true; echo "Installing the suite from wheels";;
    d) workdir="$(realpath "$OPTARG")"; echo "Setting the working directory to $workdir";;
    b) plugin_keys="$OPTARG"; echo "Requesting to enable the following plugin keys ${plugin_keys}";;
    v) suite_version="$OPTARG"; echo "Using suite version ${suite_version} instead of latest";;
    x) HEPSCORE_VERSION="$OPTARG"; echo "Using HEPSCORE version ${HEPSCORE_VERSION}";;
    n) n_cores="$OPTARG"; n_flag_set=true; echo "Using ${n_cores} cores instead of all";;
    t) threadscan_flag=true; echo "Thread scan mode enabled";;
    ?)
      cat >&2 <<EOF

Usage: $(basename "$0") [OPTIONS]

Options:
  --config file           Load arguments from file (one flag per line)
  -c, --cert path         Path to the certificate for AMQ authentication
  -k, --key path          Path to the private key for AMQ authentication
  -i, --install-only      Install only, do not run the suite
  -r, --run-only          Run only, skip installation
  -p, --publish           Publish the results to AMQ
  -s, --site site         Site name to tag the results with
  -e, --executor type     Container executor to use (singularity or docker)
  -d, --workdir path      Set the working directory
  -w, --wheels            Install from prebuilt wheels instead of repo
  -b, --plugins keys      Enable plugins using the following keys:
                          f - CPU frequency
                          l - System load
                          m - Memory usage
                          s - Memory swap
                          p - Power consumption
                          g - GPU power consumption
                          u - GPU usage
                          Default: f,l,m,s,p | Disable: -b none
                          Requires suite version >= 3.0
  -v, --suite-version ver Suite version (default: latest)
  -x, --hepscore-version  HEPSCORE version (default: v1.5)
  -n, --ncores number     Number of cores (requires HEPSCORE >= 2.0)
  -t, --threadscan        Run thread scaling tests (4, 25%, 50%, 75%, 100%)
  --help                  Show this help message
EOF
      exit 1;;
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
NCORES="${n_cores:-$(nproc)}"
THREADSCAN="${threadscan_flag:-false}"
#--------------[End of user editable section]-------------------------

# AMQ
SERVER=dashb-mb.cern.ch
PORT=61123
TOPIC=/topic/vm.spec

SCRIPT_VERSION="3.0"
SUPPORTED_HEPSCORE_VERSIONS=(v1.5 v2.0)
HEPSCORE_VERSION="${HEPSCORE_VERSION:-v1.5}"
SUITE_VERSION=${suite_version-latest} # Use "latest" for the latest stable release

RUNDIR=$WORKDIR/suite_results
MYENV=$WORKDIR/env_bmk        # Define the name of the python environment
LOGFILE=$WORKDIR/output.txt
SUITE_CONFIG_FILE=$WORKDIR/bmkrun_config.yml
HEPSCORE_CONFIG_FILE=$WORKDIR/hepscore_config.yml
GiB_PER_CORE=1

SUPPORTED_PY_VERSIONS=(py36 py38 py39 py3.11 py3.12)
DEFAULT_PY_VERSION="py39"

declare -A registries=( ["singularity"]="oras" ["docker"]="docker" )
declare -A registry_suffixes=( ["singularity"]="-sif" ["docker"]="" )
REGISTRY="${registries[$EXECUTOR]}"
# shellcheck disable=SC2034
REGISTRY_SUFFIX="${registry_suffixes[$EXECUTOR]}"

# Colors
GREEN='\033[0;32m'
#CYAN='\033[0;36m'
ORANGE='\033[1;33m'
NC='\033[0m' # No Color

echo "Running script: $0 - version: $SCRIPT_VERSION"
cd "$(dirname "$0")" || exit 1

create_workdir(){
    if [ ! -d "$WORKDIR" ]; then
        echo "Creating the WORKDIR $WORKDIR"
        mkdir -p "$WORKDIR"
        chmod a+rw -R "$WORKDIR"
    fi
}

create_python_venv(){
    python3 -m venv "$MYENV"        # Create a directory with the virtual environment
    # shellcheck source=/dev/null
    source "$MYENV/bin/activate"    # Activate the environment
}

validate_params(){
    validate_site
    validate_publish
    validate_container_executor
    validate_hepscore_version
}

validate_site(){
    if [ -z "$SITE" ]; then
        echo "The site name is not set. Please use the -s SITE option or set the SITE variable in the script."
        exit 1
    fi
}

validate_publish(){
    if [[ $PUBLISH == true ]]; then
        if [[ "$CERTIFKEY" == 'PATH_TO_CERT_KEY' ]]; then
            echo "The certificate key is not set. Please set the CERTIFKEY variable in the script."
            exit 1
        fi

        if [[ "$CERTIFCRT" == 'PATH_TO_CERT' ]]; then
            echo "The certificate is not set. Please set the CERTIFCRT variable in the script."
            exit 1
        fi
    fi
}

validate_container_executor(){
    if [ -z "${REGISTRY}" ]; then
        echo "The executor has got to be one of: ${!registries[*]}. Wrong input value: $executor"
        exit 1
    fi
}

validate_hepscore_version() {
  # Validates and adjusts the selected HEPSCORE version.
  # - If the version is not supported, it falls back to:
  #     * v2.0 if -n or THREADSCAN (-t) is set
  #     * v1.5 otherwise
  # - If the version is supported but < v2.0 and -n or -t is set,
  #   exit and inform the user about it.
  #
  # After this function:
  # - HEPSCORE_VERSION is always valid and supported

  DEFAULT_VERSION="v1.5"
  NCORES_VERSION="v2.0"

  # Normalize version: add "v" prefix if missing
  if [[ ! "$HEPSCORE_VERSION" =~ ^v ]]; then
    HEPSCORE_VERSION="v$HEPSCORE_VERSION"
  fi

  # Check if the version is supported
  if [[ ! "${SUPPORTED_HEPSCORE_VERSIONS[*]}" == *"${HEPSCORE_VERSION}"* ]]; then
    echo "Warning: HEPSCORE version '${HEPSCORE_VERSION}' is not supported."
    echo "Supported versions: ${SUPPORTED_HEPSCORE_VERSIONS[*]}"

    if [[ "$n_flag_set" == true || "$THREADSCAN" == true ]]; then
      echo "Falling back to compatible version: ${NCORES_VERSION}"
      HEPSCORE_VERSION="$NCORES_VERSION"
    else
      echo "Falling back to default version: ${DEFAULT_VERSION}"
      HEPSCORE_VERSION="$DEFAULT_VERSION"
    fi
  fi

  # If threadscan or ncores flags are set, ensure version is >= v2.0
  if [[ "$n_flag_set" == true || "$THREADSCAN" == true ]]; then
    version_number=$(echo "$HEPSCORE_VERSION" | sed 's/^v//' | cut -d. -f1,2)
    if (( $(echo "$version_number < 2.0" | bc -l) )); then
      echo "Error: The options -n (ncores) or -t (threadscan) require HEPSCORE version >= v2.0."
      echo "Current version: '${HEPSCORE_VERSION}' is not compatible."
      echo "Please specify a compatible version using the -x flag, e.g., '-x v2.0'."
      exit 1
    fi
  fi
}

create_config_file(){
    # CONFIG_FILE_CREATION
    SUITE_PLUGINS_CONFIG=""
    create_plugin_configuration

    cat > "$SUITE_CONFIG_FILE" <<EOF2
activemq:
  server: $SERVER
  topic: $TOPIC
  port: $PORT
  ## include the certificate full path (see documentation)
  key: $CERTIFKEY
  cert: $CERTIFCRT

global:
  benchmarks:
  - hepscore
  - db12
  # - hs06
  # - spec2017
  # comment/uncomment any of the above benchmarks to exclude/include them
  mode: $EXECUTOR
  publish: $PUBLISH
  rundir: $RUNDIR
  tags:
    site: $SITE
  pre-stage-duration: 2
  post-stage-duration: 2
  hw_requirements:
    min_memory_per_core: 2.0
    min_disk_per_core: 1.0
    
  sw_requirements:
    check_root_access: false
    check_selinux_disabled: false
    min_docker_version: "1.14"

hepscore:
  version: $HEPSCORE_VERSION
  config: default


hs06:
  # Use the docker registry
  image: "docker://gitlab-registry.cern.ch/hep-benchmarks/hep-spec/hepspec-cc7-multiarch:v2.3"
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

$SUITE_PLUGINS_CONFIG
EOF2

    if [ -f "$HEPSCORE_CONFIG_FILE" ]; then
        cat "$HEPSCORE_CONFIG_FILE"
    fi
}

create_plugin_configuration() {
    # This function sets up plugin configuration for system metrics collection.
    # It determines which plugins (CPU frequency, load, memory, power, GPU stats, etc.) should be enabled
    # based on the provided plugin keys and the selected suite version.
    # The function generates corresponding YAML configuration for each enabled metric plugin,
    # which will be included in the final suite configuration file.

    # Allowed plugin keys
    ALLOWED_PLUGIN_KEYS=(f l m s p g u)

    # Skip if version is lower than 3.0
    # Check if the suite version is above a given version or BMK* branch
    if [[ ! "$SUITE_VERSION" =~ ^[3-9]\.[[:alnum:]]*$ && \
          ! "$SUITE_VERSION" =~ ^qa$ && \
          ! "$SUITE_VERSION" =~ ^latest$ && \
          ! "$SUITE_VERSION" =~ ^BMK ]]; then
      echo "[create_plugin_configuration] Suite version ${SUITE_VERSION} is not adequate to run plugins. Exiting."
      return 1
    fi

    if [[ "$plugin_keys" == "none" ]]; then
        echo "[create_plugin_configuration] Plugins are disabled"
        return 0
    fi 

    if [[ "$plugin_keys" == "all" ]]; then
        plugin_keys=$(IFS=,; echo "${ALLOWED_PLUGIN_KEYS[*]}")
        echo "[create_plugin_configuration]: All ($plugin_keys) plugins are enabled"
    fi 
     
    if [[ -z $plugin_keys ]]; then
        plugin_keys='f,l,m,s,p'
        echo "[create_plugin_configuration] using default plugin keys ${plugin_keys}"
    else
        echo "[create_plugin_configuration] Requested to enable the following plugin keys ${plugin_keys}"
    fi

    collect_cpu_frequency=false
    collect_load=false
    collect_memory_usage=false
    collect_swap_usage=false
    collect_power_consumption=false
    collect_gpu_power_consumption=false
    collect_gpu_usage=false

    for pkey in "${ALLOWED_PLUGIN_KEYS[@]}"; do
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
          g)
            collect_gpu_power_consumption=true
            ;;
          u)
            collect_gpu_usage=true
            ;;
          *)
            echo "Unexpected plugin key $pkey. Ignoring it"
            ;;
        esac
      fi
    done

    # Print the status of each collection flag 
    echo "[create_plugin_configuration] collect_cpu_frequency: $collect_cpu_frequency"
    echo "[create_plugin_configuration] collect_load: $collect_load"
    echo "[create_plugin_configuration] collect_memory_usage: $collect_memory_usage"
    echo "[create_plugin_configuration] collect_swap_usage: $collect_swap_usage"
    echo "[create_plugin_configuration] collect_power_consumption: $collect_power_consumption"
    echo "[create_plugin_configuration] collect_gpu_power_consumption: $collect_gpu_power_consumption"
    echo "[create_plugin_configuration] collect_gpu_usage: $collect_gpu_usage"


    METRICS_CONFIG=""

    if [ "$collect_cpu_frequency" = true ]; then
      METRICS_CONFIG="$METRICS_CONFIG
      cpu-frequency:
        command: cpupower -c all frequency-info -f | grep 'current CPU frequency:' | grep -o '[0-9]\{7,\}' | awk '{s+=\$1; c++} END {print (s/c)/1000}'
        regex: '(?P<value>\d+.\d+).*'
        unit: 'MHz'
        interval_mins: 1"
    fi

    if [ "$collect_load" = true ]; then
      METRICS_CONFIG="$METRICS_CONFIG
      load:
        command: 'uptime'
        regex: 'load average: (?P<value>\d+.\d+),'
        unit: ''
        interval_mins: 1"
    fi

    if [ "$collect_memory_usage" = true ]; then
      METRICS_CONFIG="$METRICS_CONFIG
      used-memory:
        command: 'free -m'
        regex: 'Mem: *(\d+) *(?P<value>\d+).*'
        unit: 'MiB'
        interval_mins: 1"
    fi

    if [ "$collect_swap_usage" = true ]; then
      METRICS_CONFIG="$METRICS_CONFIG
      used-swap-memory:
        command: 'free -m'
        regex: 'Swap: *\d+ *(?P<value>\d+).*'
        unit: 'MiB'
        interval_mins: 1"
    fi

    if [ "$collect_power_consumption" = true ]; then
      METRICS_CONFIG="$METRICS_CONFIG
      power-consumption:
        command: 'ipmitool dcmi power reading'
        description: 'Retrieves power consumption of the system. Requires elevated privileges.'
        regex: 'Instantaneous power reading:\s*(?P<value>\d+) Watts'
        unit: 'W'
        interval_mins: 1"
    fi

    if [ "$collect_gpu_power_consumption" = true ]; then
      METRICS_CONFIG="$METRICS_CONFIG
      gpu-power-consumption:
        command: 'nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits -i 0'
        description: 'Retrieves gpu power consumption.'
        regex: '(?P<value>\d+(.\d+)?).*'
        unit: 'W'
        interval_mins: 0.1"
    fi

    if [ "$collect_gpu_usage" = true ]; then
      METRICS_CONFIG="$METRICS_CONFIG
      gpu-usage:
        command: 'nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits -i 0'
        description: 'Retrieves gpu usage.'
        regex: '(?P<value>\d+(.\d+)?).*'
        unit: ''
        interval_mins: 0.1"
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

add_tag_to_suite_config() {
    # This function adds a key-value tag to the 'tags:' section of the SUITE_CONFIG_FILE.
    # If the tag already exists, it skips modification. If the 'tags:' section is missing,
    # it raises an error. This helps dynamically annotate the benchmark configuration with context
    # like thread count or test type (e.g., threadscan, core_fraction).

    local tag_key="$1"
    local tag_value="$2"

    if grep -q "^\s*${tag_key}:" "$SUITE_CONFIG_FILE"; then
        echo "[add_tag_to_suite_config] Tag '$tag_key' already exists. Skipping."
    else
        echo "[add_tag_to_suite_config] Adding '$tag_key: $tag_value' to 'tags:' section in $SUITE_CONFIG_FILE"

        awk -v key="$tag_key" -v val="$tag_value" '
            BEGIN { tag_indent=""; done=0 }
            /^\s+tags:/ {
                tag_indent = gensub(/( *)(tags:)/, "\\1", 1)
                print
                print tag_indent "  " key ": " val
                done=1
                next
            }
            { print }
            END {
                if (!done) {
                    print "[ERROR] tags: section not found!" > "/dev/stderr"
                    exit 1
                }
            }
        ' "$SUITE_CONFIG_FILE" > "${SUITE_CONFIG_FILE}.tmp" && mv "${SUITE_CONFIG_FILE}.tmp" "$SUITE_CONFIG_FILE"
    fi
}

run_threadscan() {
  # Performs a thread scaling benchmark by running the suite multiple times
  # using varying numbers of CPU cores.
    echo "[run_threadscan] Preparing thread scan run..."

    add_tag_to_suite_config "threadscan" "true"

    total_cores=$(nproc)
    declare -a raw_counts=("4" "$((total_cores / 4))" "$((total_cores / 2))" "$(((3 * total_cores) / 4))" "$total_cores")
    declare -a labels=("minimum" "25%" "50%" "75%" "maximum")
    declare -A seen=()

    valid_core_counts=()
    valid_labels=()

    for i in "${!raw_counts[@]}"; do
        cores="${raw_counts[$i]}"
        label="${labels[$i]}"

        # Round up to next multiple of 4, maxing out at total_cores
        if (( cores % 4 != 0 )); then
            cores=$(( ((cores + 3) / 4) * 4 ))
        fi
        if (( cores > total_cores )); then
            cores=$total_cores
        fi

        # Avoid duplicates
        if [[ -z "${seen[$cores]}" ]]; then
            seen[$cores]=1
            valid_core_counts+=("$cores")
            valid_labels+=("$label")
        fi
    done

    for i in "${!valid_core_counts[@]}"; do
        cores="${valid_core_counts[$i]}"
        label="${valid_labels[$i]}"

        echo -e "\n[run_threadscan] Running benchmark with $cores cores ($label)..."

        add_tag_to_suite_config "core_fraction" "$cores"

        NCORES="$cores"
        n_flag_set=true

        hepscore_run

        sed -i '/core_fraction:/d' "$SUITE_CONFIG_FILE"
    done
}


hepscore_install(){

    create_python_venv
    install_suite

}

install_suite(){
    if [ "$SUITE_VERSION" = "latest" ];  then
        SUITE_VERSION=$(curl --silent https://hep-benchmarks.web.cern.ch/hep-benchmark-suite/releases/latest)
        echo "Latest suite release selected: ${SUITE_VERSION}"
    fi
    
    if [[ $INSTALL_FROM_WHEELS == true ]]; then
        install_suite_from_wheels
    else
        install_suite_from_repo
    fi
}

install_suite_from_repo(){
    pip3 install --upgrade pip
    pip3 install "git+https://gitlab.cern.ch/hep-benchmarks/hep-score.git@$HEPSCORE_VERSION"
    pip3 install "git+https://gitlab.cern.ch/hep-benchmarks/hep-benchmark-suite.git@$SUITE_VERSION"
}

install_suite_from_wheels() {
    # Try to get system's default python3 and see if it's one of the supported version; fallback to the default otherwise
    PY_VERSION=$(python3 -V | awk '{split($2, version, "."); print "py"version[1] version[2]}')

    if [[ ! "${SUPPORTED_PY_VERSIONS[*]}" == *"${PY_VERSION}"* ]]; then
        echo "Your default python3 version (${PY_VERSION}) isn't supported. Falling back to ${DEFAULT_PY_VERSION}."
        PY_VERSION=$DEFAULT_PY_VERSION
    fi

    # Get appropriate wheels
    ARCH=$(uname -m)
    GLIBC=$(ldd --version | awk 'NR==1 {gsub(/\./,"_",$NF); print $NF}')

    # Find dev versions too
    wheels_path=""
    if ! [[ $SUITE_VERSION =~ ^[0-9v] ]]; then
        wheels_path="dev/"
    fi
    
    if [[ $SUITE_VERSION =~ ^v ]];  then
        wheels_version="hep-benchmark-suite-wheels-${PY_VERSION}-${ARCH}-${SUITE_VERSION}.tar"  # Old format < 3.0
    else
        # get list of available wheel version filtered on PY_Version, ARCH, and SUITE_VERSION
        wheels_url="https://hep-benchmarks.web.cern.ch/hep-benchmark-suite/releases/${wheels_path}${SUITE_VERSION}/"
        curl_output=$(curl -s "${wheels_url}"  | grep -oE "hep-benchmark-suite-wheels-${SUITE_VERSION}-${PY_VERSION}-none-linux_[0-9]{1,}_[0-9]{1,}_${ARCH}.tar" | uniq | grep -oE "none-linux_[0-9]{1,}_[0-9]{1,}" | grep -oE "[0-9]{1,}_[0-9]{1,}" )
        exit_status=$?
        if [ $exit_status -ne 0 ]; then
            echo  echo -e "${ORANGE}Could not reach ${wheels_url} to check for available wheels.${NC}"
        fi
        # split string of versions into array of version
        mapfile -t glibc_releases <<< "${curl_output}"
        # helper function: check if version is lower
        version_lt() {
            [ "$1" = "$2" ] || [  "$1" = "$(echo -e "$1\n$2" | sort -V | head -n1)" ]
        }
        latest_glibc_version=${glibc_releases[0]}
        for version in "${glibc_releases[@]}"; do
            # check if version is lower or equal to GLIBC version
            if version_lt "${version}" "${GLIBC}"; then
                latest_glibc_version=${version}
            fi
        done
        wheels_version="hep-benchmark-suite-wheels-${SUITE_VERSION}-${PY_VERSION}-none-linux_${latest_glibc_version}_${ARCH}.tar" # New format >= 3.0
    fi

    # Download and extract the wheels
    echo -e "-> Downloading wheel: $wheels_version \n"    
    curl -O "https://hep-benchmarks.web.cern.ch/hep-benchmark-suite/releases/${wheels_path}${SUITE_VERSION}/${wheels_version}"
    tar xvf "${wheels_version}"

    # Update pip before installing any other wheel
    if ls suite_wheels*/pip* 1> /dev/null 2>&1; then
        python3 -m pip install suite_wheels*/pip*.whl
    fi

    python3 -m pip install suite_wheels*/*.whl
    rm -rf suite_wheels*
}

ensure_suite_is_not_running() {
    PS_AUX_BMKRUN=$(pgrep bmkrun)
    if (( PS_AUX_BMKRUN > 1 )); then
        echo -e "${ORANGE}Another instance of the HEP Benchmark Suite is already running. Please wait for it to finish before running the suite again.${NC}"
        exit 1
    fi
}

create_tarball() {
    # Create tarball to be sent to the admins if the suite failed but still produced data
    if [[ $SUITE_SUCCESSFUL -ne 0 ]] && [[ $RUNDIR_DATE ]] ;
    then
        LOG_TAR="${SITE}_${RUNDIR_DATE}.tar"
        find "$RUNDIR/$RUNDIR_DATE/" \( -name archive_processes_logs.tgz -o -name hep-benchmark-suite.log -o -name 'HEPscore*.log' \) -exec tar -rf "$LOG_TAR" {} \; &>/dev/null 
        echo -e "${ORANGE}\nThe suite has run into errors. If you need help from the administrators, please contact them by email and attach ${WORKDIR}/${LOG_TAR} to it ${NC}"
    fi
}

print_amq_send_command() {
    # Print command to send results if they were produced but not sent
    if [[ $RESULTS ]] && { [[ $PUBLISH == false ]] || [[ $AMQ_SUCCESSFUL -ne 0 ]] ; }; then
        echo -e "${GREEN}\nThe results were not sent to AMQ. In order to send them, you can run (--dryrun option available):"
        echo -e "${MYENV}/bin/bmksend -c ${SUITE_CONFIG_FILE} ${RUNDIR} ${NC}"
    fi
}

check_memory_difference() {
    # Print warning message in case of memory increase
    MEM_DIFF=$((MEM_AFTER - MEM_BEFORE))
    if (( MEM_DIFF > 1048576 )); then
      echo -e "${ORANGE}The memory usage has increased by more than 1 GiB since the start of the script. Please check there are no zombie processes in the machine before running the script again.${NC}"
    fi
}

check_workdir_space() {
    # Check if there is enough space in the workdir
    workdir_space=$(df -k "$WORKDIR" | awk 'NR==2 {print $4}')
    minimum_space=$((GiB_PER_CORE * 1024 * 1024 * $(nproc)))
    if (( workdir_space < minimum_space )); then
        echo -e "${ORANGE}There is less than $((minimum_space/1024/1024))GiB of space left in the workdir ($((workdir_space/1024/1024))GiB). Please free some space before running the script again.${NC}"
        exit 1
    fi
}

hepscore_run(){

    if [[ -d "$WORKDIR" && -f "$MYENV/bin/activate" ]]; then 
        # shellcheck source=/dev/null
        source "$MYENV/bin/activate"
    else
        echo "The suite installation cannot be found; please run $0 to install and run it or $0 -i to install it only"
        exit 1
    fi

    ensure_suite_is_not_running
    check_workdir_space

    MEM_BEFORE=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
    if [[ "$n_flag_set" == true ]]; then
        bmkrun -c "$SUITE_CONFIG_FILE" -n "$NCORES" | tee -i "$LOGFILE"
    else
        bmkrun -c "$SUITE_CONFIG_FILE" | tee -i "$LOGFILE"
    fi
    MEM_AFTER=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)

    RESULTS=$(awk '/Full results can be found in.*/ {print $(NF-1)}' "$LOGFILE")
    RUNDIR_DATE=$(perl -n -e'/^.*(run_2[0-9]{3}-[0-9]{2}-[0-9]{2}_[0-9]{4}).*$/ && print $1; last if $1' "$LOGFILE")
    SUITE_SUCCESSFUL=$(! grep -q ERROR "$LOGFILE"; echo $?)
    AMQ_SUCCESSFUL=$(grep -q "Results sent to AMQ topic" "$LOGFILE"; echo $?)
    rm -f "$LOGFILE"

    create_tarball
    print_amq_send_command
    check_memory_difference
}


# Always done so options are taken into account
create_workdir
cd "$WORKDIR" || exit 1
create_config_file

# Always validate parameters
validate_params

# Ensure -n and -t are not used together
if [[ "$n_flag_set" == true && "$THREADSCAN" == true ]]; then
    echo "Error: The options -n (number of cores) and -t (threadscan) cannot be used together."
    exit 1
fi

# Run threadscan if requested and skip everything else
if [[ "$THREADSCAN" == true ]]; then
    hepscore_install
    run_threadscan
    exit 0
fi

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
