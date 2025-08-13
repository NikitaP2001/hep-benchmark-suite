#!/bin/bash -x

function run_script(){
    set -x
    mkdir -p $WORKDIR
    cp ${EXEC_SCRIPT} $WORKDIR/test_script.sh
    
    envsubst '${SUITE_VERSION}' < $WORKDIR/test_script.sh | sponge $WORKDIR/test_script.sh

    # Use test config and reduce memory requirements
    sed -e 's@\(\s*config:\s*\)default@\1$CI_PROJECT_DIR/tests/ci/hepscore.yaml@' -e 's@min_memory_per_core: .*@min_memory_per_core: 1.0@' examples/hepscore/run_HEPscore.sh | sponge $WORKDIR/test_script.sh
    
    chmod u+x $WORKDIR/test_script.sh

    # Extract -t if present in splugins and remove it from splugins
    if [[ "$splugins" == *"-t"* ]]; then
        tflag="-t"
        splugins="$(echo "$splugins" | sed 's/ *-t//g')"
    else
        tflag=""
    fi
    
    if [[ -n "$config_mode" ]]; then
        $WORKDIR/test_script.sh -d $WORKDIR --config "$CI_PROJECT_DIR/$config_mode" | tee log
    else
        $WORKDIR/test_script.sh -s dummy -d $WORKDIR ${sversion} ${splugins} ${tflag} | tee log
    fi    

    grep "with return code 0" log
    
    output_json=$(find $WORKDIR -type f -name bmkrun_report.json)
    echo "Found json output file ${output_json}"
    
    python3 $CI_PROJECT_DIR/tests/dump_json_keys.py ${output_json} 2
    
    # Only check for plugin keys if plugins were enabled *and* version is not v2.2
    if [[ "${splugins}" == "-t" && "${sversion}" != "-v v2.2" ]]; then
        python3 "$CI_PROJECT_DIR/tests/dump_json_keys.py" "${output_json}" 2 | grep -c "plugins (N keys:"
    fi

    # Check for threadscan if applicable
    if [[ "${tflag}" == "-t" ]]; then
        python3 "$CI_PROJECT_DIR/tests/dump_json_keys.py" "${output_json}" 3 | grep -c "threadscan (No subkeys)"
    fi

    set +x
}