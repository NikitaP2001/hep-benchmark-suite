"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""


import argparse
import logging
from pathlib import Path
import sys
import time
import stomp

_log = logging.getLogger(__name__)


class Listener(stomp.ConnectionListener):
    """A generic STOMP protocol listner
    Args:
        stomp (stomp.ConnectionListner): a connection listner
    """

    def __init__(self, conn):
        self.conn = conn
        self.status = True
        self.message = ""

    def on_error(self, headers, body):
        _log.error("received error: %s", body)
        self.status = False
        self.message = body

    def on_message(self, headers, body):
        _log.info("received message: %s", body)


def send_message(filepath, connection):
    """expects a filepath string, and a dict of args"""

    if not Path(filepath).is_file():
        raise IOError("{} is not a valid filepath!".format(filepath))

    with open(filepath, "r") as f:
        message_contents = f.read()

    conn = stomp.Connection(
        host_and_ports=[(connection["server"], int(connection["port"]))]
    )
    conn.set_listener("mylistener", Listener(conn))

    if "key" in connection and "cert" in connection:
        conn.set_ssl(
            for_hosts=[(connection["server"], int(connection["port"]))],
            cert_file=connection["cert"],
            key_file=connection["key"],
            # TODO: verify SSL support
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
    connection_details = dict()
    for i in non_empty.keys():
        connection_details[i] = non_empty[i]

    connection_details.pop("file", None)
    send_message(args.file, connection_details)


if __name__ == "__main__":
    main()
