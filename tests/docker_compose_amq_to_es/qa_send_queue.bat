#!/usr/bin/env bats

TESTDIR=$BATS_TEST_DIRNAME
INPUTFILE=${BATS_TEST_DIRNAME}/../data/result_profile_sample.json
QUEUE_HOST=srv_activemq
QUEUE_PORT=61613
QUEUE_USERNAME=producer_login
QUEUE_PASSWD=producer_password
QUEUE_NAME="/queue/bmkqueue"

CODE_DIR=/opt/hep-benchmark-suite/


@test "Test: use right AMQ connection credentials" {
    run python ${CODE_DIR}/send_queue.py --port=$QUEUE_PORT \
        --server=$QUEUE_HOST --topic=$QUEUE_NAME  --username=$QUEUE_USERNAME \
        --password=$QUEUE_PASSWD --file=$INPUTFILE
    echo -e "$output"
    [ "$status" -eq 0 ]
}


@test "Test: wrong AMQ credentials username-password" { 
    run python ${CODE_DIR}/send_queue.py --port=$QUEUE_PORT \
        --server=$QUEUE_HOST --topic=$QUEUE_NAME  --username=$QUEUE_USERNAME \
        --file=$INPUTFILE 
    echo -e "$output" 
    [ "$status" -ne 0 ]
}   


@test "Test: missing AMQ topic parameter" {
    run python ${CODE_DIR}/send_queue.py --port=$QUEUE_PORT \
        --server=$QUEUE_HOST --username=$QUEUE_USERNAME --password=$QUEUE_PASSWD \
        --file=$INPUTFILE 
    echo -e "$output"
    [ "$status" -ne 0 ]
}


@test "Test: wrong AMQ topic name" {
    run python ${CODE_DIR}/send_queue.py --port=$QUEUE_PORT --server=$QUEUE_HOST \
        --topic=foo  --username=$QUEUE_USERNAME --password=$QUEUE_PASSWD \
        --file=$INPUTFILE
    echo -e "$output"
    [ "$status" -ne 0 ]
}



@test "Generate result profile for certificate tests" {
    skip
    run genData "test amq certificate"
    echo -e "$output"
    [ "$status" -eq 0 ]
}


@test "Test wrong configuration certificate" {
    skip # Needs a certificate to be tested
    
    run python ${CODE_DIR}/send_queue.py --port=$QUEUE_PORT --server=$QUEUE_HOST \
        --topic=$QUEUE_NAME --cert_file=$CERT_FILE  --file=$INPUTFILE
    echo -e "$output"
    [ "$status" -ne 0 ]
}


@test "Test both certificate and password connection" {
    skip # Needs a certificate to be tested

    run python ${CODE_DIR}/send_queue.py --port=$QUEUE_PORT --server=$QUEUE_HOST \
        --topic=$QUEUE_NAME --cert_file=$CERT_FILE --key_file=$KEY_FILE --username=$QUEUE_USERNAME \
        --password=$QUEUE_PASSWD --file=$INPUTFILE
    echo -e "$output"
    [ "$status" -ne 0 ]
}


@test "Test successful connection" {
    skip # Needs a certificate to be tested
    
    run python ${CODE_DIR}/send_queue.py --port=$QUEUE_PORT --server=$QUEUE_HOST \
        --topic=$QUEUE_NAME --cert_file=$CERT_FILE --key_file=$KEY_FILE \
        --file=$INPUTFILE
    echo -e "$output"
    [ "$status" -eq 0 ]
}


