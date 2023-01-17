"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""


import argparse
import logging
import os
import subprocess
from subprocess import DEVNULL, STDOUT
import sys
import time
from pathlib import Path
import pem

from OpenSSL import SSL, crypto
import stomp

_log = logging.getLogger(__name__)

CA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "CA")
CERTIFICATE = "cert"
KEY = "key"


class Listener(stomp.ConnectionListener):
    """A generic STOMP protocol listener
    Args:
        stomp (stomp.ConnectionListener): a connection listener
    """

    def __init__(self, conn):
        self.conn = conn
        self.status = True
        self.message = ""

    def on_error(self, frame):
        _log.error("received error: %s", frame.body)
        self.status = False
        self.message = frame.body

    def on_message(self, frame):
        _log.error("received message: %s", frame.body)


def _check_certificate_config(connection):
    cert, key = _load_cert_and_key(connection)
    _ensure_key_matches_cert(cert, connection, key)
    _validate_certificate(cert)


def _ensure_key_matches_cert(cert, connection, key):
    context = SSL.Context(SSL.TLS_METHOD)
    context.use_privatekey(key)
    context.use_certificate(cert)
    try:
        context.check_privatekey()
    except SSL.Error:
        raise Exception(f"Certificate {connection[CERTIFICATE]} and private key {connection[KEY]} do not match")


def _validate_certificate(cert):
    """ The certificate is validated against CA certificates, and other checks are performed.
    E.g. that the certificate is not expired. """

    store = crypto.X509Store()

    for root, dirs, files in os.walk(CA_DIR):
        for file in files:
            for _ca in pem.parse_file(os.path.join(root, file)):
                crt = crypto.load_certificate(crypto.FILETYPE_PEM, _ca.as_bytes())
                store.add_cert(crt)

    store_ctx = crypto.X509StoreContext(store, cert)

    try:
        store_ctx.verify_certificate()
    except crypto.X509StoreContextError as e:
        raise ValueError(f"An error occurred while validating your certificate: {e}")


def _load_cert_and_key(connection):
    # TODO: Check for other file types
    try:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(connection[CERTIFICATE], 'rb').read())
    except crypto.Error as e:
        raise Exception(f"Error while loading the certificate {connection[CERTIFICATE]}: {e}")

    try:
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, open(connection[KEY]).read())
    except crypto.Error as e:
        raise Exception(f"Error while loading the private key {connection[KEY]}: {e}")

    return cert, key


def send_message(filepath, connection):
    """expects a filepath string, and a dict of args"""

    if not Path(filepath).is_file():
        raise FileNotFoundError("{} is not a valid filepath!".format(filepath))

    with open(filepath, "r", encoding="utf-8") as f:
        message_contents = f.read()

    conn = stomp.Connection(
        host_and_ports=[(connection["server"], int(connection["port"]))]
    )
    conn.set_listener("mylistener", Listener(conn))

    if KEY in connection and CERTIFICATE in connection:
        if is_key_password_protected(connection[KEY]):
            _log.warning("The private key is password protected, please enter the password or the execution will stall")

        _check_certificate_config(connection)
        conn.set_ssl(
            for_hosts=[(connection["server"], int(connection["port"]))],
            cert_file=connection[CERTIFICATE],
            key_file=connection[KEY],
            ssl_version=5,
        )  # <_SSLMethod.PROTOCOL_TLSv1_2: 5>
        conn.connect(wait=True)
        _log.info("AMQ SSL: certificate based authentication")
    elif "username" in connection and "password" in connection:
        conn.connect(connection["username"], connection["password"], wait=True)
        _log.info("AMQ Plain: user-password based authentication")
    else:
        raise IOError(
            "The input arguments do not include a valid pair of authentication"
            "(certificate, key) or (user,password)"
        )

    _log.info("Sending results to AMQ topic")
    time.sleep(5)
    _log.debug("Attempting send of message %s", message_contents)
    conn.send(connection["topic"], message_contents, "application/json")

    time.sleep(5)

    if conn.get_listener("mylistener").status is False:
        raise Exception("ERROR: {}".format(conn.get_listener("mylistener").message))
    conn.disconnect()

    _log.info("Results sent to AMQ topic")


def is_key_password_protected(key):
    os.chmod(key, 0o600)
    return_code = subprocess.run(["ssh-keygen", "-y", "-P", "''", "-f", key], stdout=DEVNULL, stderr=STDOUT).returncode
    return return_code != 0


def parse_args(args):
    """Parse passed list of args"""
    parser = argparse.ArgumentParser(
        description="This sends a file.json to an AMQ broker via STOMP."
        "Default STOMP port is 61613, if not overridden"
    )
    parser.add_argument("-p", "--port", default=61613, type=int, help="Queue port")
    parser.add_argument("-s", "--server", required=True, help="Queue host")
    parser.add_argument(
        "-u", "--username", nargs="?", default=None, help="Queue username"
    )
    parser.add_argument(
        "-w", "--password", nargs="?", default=None, help="Queue password"
    )
    parser.add_argument("-t", "--topic", required=True, help="Queue name")
    parser.add_argument(
        "-k", "--key", nargs="?", default=None, help="AMQ authentication key"
    )
    parser.add_argument(
        "-c", "--cert", nargs="?", default=None, help="AMQ authentication certificate"
    )
    parser.add_argument("-f", "--file", required=True, help="File to send")
    return parser.parse_args(args)


def main():
    """CLI entrypoint"""
    args = parse_args(sys.argv[1:])

    # Get non-None cli arguments
    non_empty = {k: v for k, v in vars(args).items() if v is not None}

    # Populate active config with cli override
    connection_details = {}
    for i in non_empty.keys():
        connection_details[i] = non_empty[i]

    connection_details.pop("file", None)
    send_message(args.file, connection_details)


if __name__ == "__main__":
    main()
