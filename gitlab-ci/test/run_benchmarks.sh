#!/bin/bash 

function before_script(){
    set -x
    yum install -y -q gettext moreutils git python3-pip lzo jq
    python3 -m pip install -U pip wheel
    python3 -m pip install -r requirements.txt
    # Translate 'latest' or 'latest_rc' to the actual HS versions
    declare -A version_regex=( ["latest"]="[0-9]+.([0-9]+.?)+$" ["latest_rc"]="rc[0-9]+$" ["default"]="v1.5")
    export HEPSCORE_VER=$(curl --header "PRIVATE-TOKEN: ${CI_API_TOKEN}" "https://gitlab.cern.ch/api/v4/projects/72493/releases" | jq -r --arg regex ${version_regex[${hepscore_ver:-default}]} 'first(.[].name | select(. | test($regex)))')
    # Environment variables
    envsubst < $suite_config | sponge $suite_config   # Replace env variables in the config file
    export PATH=$PATH:$HOME/.local/bin    # $PATH cannot be modified in the variables section
    set +x
}

function run_script(){
    set -x
    python3 -m pip install --user .
    bmkrun --mode=$executor --config=$suite_config --rundir=$bmk_volume --benchmarks=$benchmark --ncores=$ncores | tee log
    grep "with return code 0" log
    output_json=$(find $bmk_volume -type f -name bmkrun_report.json)
    echo "Found json output file ${output_json}"
    python3 $CI_PROJECT_DIR/tests/dump_json_keys.py ${output_json} 2
    # test that plugins fields are available
    python3 $CI_PROJECT_DIR/tests/dump_json_keys.py ${output_json} 2 | grep -c "plugins (N keys:"
    set +x
}