"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""

import argparse
import logging
import stomp
import sys
import time
import pem
import requests
import tarfile

import os
from os import listdir, makedirs
from os.path import join, isfile, dirname, realpath, exists, normpath

import subprocess
from subprocess import DEVNULL, STDOUT

from OpenSSL import SSL, crypto
from bs4 import BeautifulSoup
from pathlib import Path


_log = logging.getLogger(__name__)

CA_DIR = join(dirname(realpath(__file__)), "CA")
CA_URL = "https://repository.egi.eu/sw/production/cas/1/current/tgz/"  # CAs included in ca-policy-egi-core
CA_EXTRA = {"geant_personal_ca_4.pem": "https://services.renater.fr/_media/tcs/geant_personal_ca_4.pem",  # Extra CAs
            "USERTrust_RSA_Certification_Authority.pem": "https://crt.sh/?d=1199354"}

# Parameters
PORT = "port"
SERVER = "server"
USERNAME = "username"
PASSWORD = "password"
TOPIC = "topic"
CERTIFICATE = "cert"
KEY = "key"
VERIFY_CERT = "verify_cert"
FILE = "file"


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

    verify = connection.get(VERIFY_CERT, False)
    _validate_certificate(cert, verify)


def _ensure_key_matches_cert(cert, connection, key):
    context = SSL.Context(SSL.TLS_METHOD)
    context.use_privatekey(key)
    context.use_certificate(cert)
    try:
        context.check_privatekey()
    except SSL.Error:
        raise Exception(f"Certificate {connection[CERTIFICATE]} and private key {connection[KEY]} do not match")


def download_ca_certificates():
    if not exists(CA_DIR):
        makedirs(CA_DIR)

    # Download ca-policy-egi-core compressed CA certificates
    data = requests.get(CA_URL, timeout=60)
    html = BeautifulSoup(data.text, "html.parser")

    for link in html.find_all("a"):
        if link.get("href").endswith(".tar.gz"):
            data = requests.get(CA_URL + link["href"], timeout=60)

            with open(join(CA_DIR, link["href"]), "wb") as f:
                f.write(data.content)

    # Extract all tar.gz files
    compressed_files = [join(CA_DIR, f) for f in listdir(CA_DIR) if isfile(join(CA_DIR, f)) and f.endswith(".tar.gz")]
    for file in compressed_files:
        tar = tarfile.open(file, "r:gz")

        for member in tar.getmembers():
            if member.isreg():
                tar.extract(member, CA_DIR)

        tar.close()
        os.remove(file)

    # Download extra CAs
    for name, url in CA_EXTRA.items():
        data = requests.get(url, timeout=60)
        with open(join(CA_DIR, name), "wb") as f:
            f.write(data.content)


def _validate_certificate(cert, verify=False):
    """ The certificate is validated against CA certificates, and other checks are performed.
    E.g. that the certificate is not expired. """

    store = crypto.X509Store()

    if verify:
        _log.info("Validating certificate's signature against CA certificates")
        download_ca_certificates()

        certificates = [join(CA_DIR, f) for f in listdir(CA_DIR) if isfile(join(CA_DIR, f)) and f.endswith(".pem")]
        for file in certificates:
            for _ca in pem.parse_file(join(CA_DIR, file)):
                crt = crypto.load_certificate(crypto.FILETYPE_PEM, _ca.as_bytes())
                store.add_cert(crt)

    store_ctx = crypto.X509StoreContext(store, cert)

    try:
        store_ctx.verify_certificate()
    except crypto.X509StoreContextError as e:
        if "unable to get local issuer certificate" in str(e):
            if verify:
                raise ValueError("The certificate used is not signed by a trusted CA")
        else:
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


def is_key_password_protected(key):
    # If the path is not absolute, make it absolute relative to the parent dir
    if not os.path.isabs(key):
        key = normpath(join(dirname(os.getcwd()), key))

    os.chmod(key, 0o600)
    return_code = subprocess.run(["ssh-keygen", "-y", "-P", "''", "-f", key], stdout=DEVNULL, stderr=STDOUT).returncode
    return return_code != 0


def send_message(filepath, connection):
    """Expects a filepath string, and a dict of args"""

    if not Path(filepath).is_file():
        raise FileNotFoundError(f"{filepath} is not a valid filepath!")

    if not connection.get(PORT) or not connection.get(SERVER) or not connection.get(TOPIC):
        raise ValueError(f"The following parameters are mandatory: {PORT}, {SERVER}, {TOPIC}")

    with open(filepath, "r", encoding="utf-8") as f:
        message_contents = f.read()

    conn = stomp.Connection(host_and_ports=[(connection[SERVER], int(connection[PORT]))])
    conn.set_listener("mylistener", Listener(conn))

    if KEY in connection and CERTIFICATE in connection:
        if is_key_password_protected(connection[KEY]):
            _log.warning("The key is password protected, remember to enter the password or the execution will stall")

        _check_certificate_config(connection)
        conn.set_ssl(
            for_hosts=[(connection[SERVER], int(connection[PORT]))],
            cert_file=connection[CERTIFICATE],
            key_file=connection[KEY],
            ssl_version=5,
        )  # <_SSLMethod.PROTOCOL_TLSv1_2: 5>
        conn.connect(wait=True)
        _log.info("AMQ SSL: certificate based authentication")
    elif USERNAME in connection and PASSWORD in connection:
        conn.connect(connection[USERNAME], connection[PASSWORD], wait=True)
        _log.info("AMQ Plain: user-password based authentication")
    else:
        raise IOError(
            "The input arguments do not include a valid pair of authentication (certificate, key) or (user, password)"
        )

    _log.info("Sending results to AMQ topic")
    time.sleep(5)
    _log.debug("Attempting send of message %s", message_contents)
    conn.send(connection[TOPIC], message_contents, "application/json")

    time.sleep(5)

    if conn.get_listener("mylistener").status is False:
        raise Exception("ERROR: {}".format(conn.get_listener("mylistener").message))
    conn.disconnect()

    _log.info("Results sent to AMQ topic")


def parse_args(args):
    """Parse passed list of args"""
    parser = argparse.ArgumentParser(
        description="Sends a JSON file to an AMQ broker via STOMP. Default STOMP port is 61613, if not overridden"
    )
    parser.add_argument("-p", f"--{PORT}", default=61613, type=int, help="Queue port")
    parser.add_argument("-s", f"--{SERVER}", required=True, help="Queue host")
    parser.add_argument("-u", f"--{USERNAME}", nargs="?", default=None, help="Queue username")
    parser.add_argument("-w", f"--{PASSWORD}", nargs="?", default=None, help="Queue password")
    parser.add_argument("-t", f"--{TOPIC}", required=True, help="Queue name")
    parser.add_argument("-k", f"--{KEY}", nargs="?", default=None, help="AMQ authentication key")
    parser.add_argument("-c", f"--{CERTIFICATE}", nargs="?", default=None, help="AMQ authentication certificate")
    parser.add_argument('-v', f"--{VERIFY_CERT}", action='store_true')
    parser.add_argument("-f", f"--{FILE}", required=True, help="File to send")
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

    connection_details.pop(FILE, None)
    send_message(args.file, connection_details)


if __name__ == "__main__":
    main()
