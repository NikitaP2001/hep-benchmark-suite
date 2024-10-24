#!/bin/bash -x

function run_script(){
    set -x
    mkdir -p $WORKDIR
    cp ${EXEC_SCRIPT} $WORKDIR/test_script.sh
    envsubst '${SUITE_VERSION}' < $WORKDIR/test_script.sh | sponge $WORKDIR/test_script.sh
    # Let's make the test faster, running hello-world
    sed -e 's@\(\s*config:\s*\)default@\1$CI_PROJECT_DIR/tests/ci/hepscore.yaml@' examples/hepscore/run_HEPscore.sh | sponge $WORKDIR/test_script.sh
    chmod u+x $WORKDIR/test_script.sh
    $WORKDIR/test_script.sh -s dummy -d $WORKDIR ${sversion} ${splugins} | tee log 
    grep "with return code 0" log
    output_json=$(find $WORKDIR -type f -name bmkrun_report.json)
    echo "Found json output file ${output_json}"
    python3 $CI_PROJECT_DIR/tests/dump_json_keys.py ${output_json} 2
    # test that plugins fields are available when version is not v2.2 or latest (that so far is v2.2)
    # FIXME when latest becomes v3.0 
    if [ "${sversion}" != "" ] && [ "${sversion}" != "-v v2.2" ]; 
        then 
        # do the test only when "-b" is passed
        if [[ "${splugins}" =~ (^| )"-b".* ]];
            then
            python3 $CI_PROJECT_DIR/tests/dump_json_keys.py ${output_json} 2 | grep -c "plugins (N keys:"
        fi
    fi
    set +x
}