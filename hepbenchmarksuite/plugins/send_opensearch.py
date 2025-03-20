"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""
import json
import logging
from pathlib import Path
from opensearchpy import OpenSearch

_log = logging.getLogger(__name__)

# Parameters
PORT = "port"
SERVER = "server"
USERNAME = "username"
PASSWORD = "password"
INDEX = "index"


class Elastic():
    def __init__(self, conf):
        conn = {"hosts": [{"host": conf[SERVER], "port": conf[PORT]}]}
        use_ssl = False

        if conf.get(USERNAME) and conf.get(PASSWORD):
            _log.info("Connecting to cluster using (user, password)")
            conn = {**conn, "http_auth": (conf[USERNAME], conf[PASSWORD])}
            use_ssl = True

        self.opensearch = OpenSearch(
                **conn,
                use_ssl=use_ssl,
                verify_certs=False,
                ssl_assert_hostname=False,
            )

    def send(self, index, msg):
        """Sends dict `msg` to OpenSearch index `index`"""

        timestamp = msg["_timestamp"]
        _id = msg["_id"]

        msg = {"message": msg, "@timestamp": timestamp}
        _log.info("document after formatting: %s", msg)

        response = self.opensearch.index(index=index, body=msg, refresh=True, id=_id)
        _log.debug(response)
        return response

    def search(self, index):
        """ Search index `index`"""

        request = {"query": {"bool": {"filter": [{"match_all": {}}], "should": [], "must": [{"range": {"@timestamp": {"lte": "now", "format": "strict_date_optional_time"}}}]}}, "size": 1}

        response = self.opensearch.search(index=index, body=request)
        _log.debug(response)
        return response


def send_message(filepath, connection):
    """Expects a filepath string, and a dict of args"""

    if not Path(filepath).is_file():
        raise FileNotFoundError(f"{filepath} is not a valid filepath!")

    with open(filepath, "r", encoding="utf-8") as msg_file:
        message = json.load(msg_file)

    if not connection.get(INDEX) or not connection.get(PORT) or not connection.get(SERVER):
        raise ValueError(f"The following parameters are mandatory: {PORT}, {SERVER}, {INDEX}")

    index = connection.pop(INDEX)
    _log.debug("Using index %s", index)
    try:
        _log.debug("Attempting send of message %s", message)
        res = Elastic(connection).send(index, message)
    except Exception as e:
        raise Exception(f"An error occured while sending a message to index {index}: {e}") from e

    _log.info(res)
    if res["_shards"]["successful"]:
        _log.info("Results sent to OpenSearch index")
    else:
        _log.critical("Results with id %s were not properly sent to OpenSearch", res["_id"])
        _log.critical(res)


def retrieve_document(connection):
    """Expects a dict of args"""

    if not connection.get(INDEX) or not connection.get(PORT) or not connection.get(SERVER):
        raise ValueError(f"The following parameters are mandatory: {PORT}, {SERVER}, {INDEX}")

    index = connection.pop(INDEX)
    _log.debug("Using index %s", index)
    try:
        res = Elastic(connection).search(index)
        _log.debug("Query result: %s", res)
    except Exception as e:
        raise Exception(f"An error occured while querying OpenSearch index {index}: {e}") from e

    if res["hits"]["total"]["value"]:
        _log.info("Got some results for the query")
        return res
    else:
        _log.critical(res)
        raise ValueError(f"Unable to retrieve document from cluster")
