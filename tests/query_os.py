import argparse
from dictdiffer import diff
from pathlib import Path
import logging
import sys
import yaml
from hepbenchmarksuite.plugins import send_opensearch

# Parameters
PORT = "port"
SERVER = "server"
USERNAME = "username"
PASSWORD = "password"
INDEX = "index"

_log = logging.getLogger(__name__)

def differ(doc1, doc2, ignore_set=[]):
        result = list(diff(doc1, doc2, ignore=ignore_set))

        for entry in result:
                if len(entry[2]) == 1:
                        print('\n\t %s :\n\t\t %s\t%s' % entry)
                else:
                        print('\n\t %s :\n\t\t %s\n\t\t\t%s\n\t\t\t%s' %
                              (entry[0], entry[1], entry[2][0], entry[2][1]))
        return(len(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_file", required=True, help="connection details for opensearch cluster")
    parser.add_argument("ref_file", help="Path to reference file")

    args = parser.parse_args()

    if not Path(args.ref_file).is_file() or not Path(args.config_file).is_file():
        raise FileNotFoundError(f"Could not find reference and/or config file")

    with Path(args.config_file).open() as config_file:
        config = yaml.full_load(config_file)["opensearch"]

    with Path(args.ref_file).open() as ref_file:
        ref_json = yaml.full_load(ref_file)

    _log.info("opensearch configuration loaded: %s", config)

    result = send_opensearch.retrieve_document(config)
    body = result['hits']['hits'][0]["_source"]["message"]

    differ_out = differ(ref_json, body)

    if differ_out == 0:
        print("\n@@@@@ SUCCESS @@@@@\n all the attributes saved correctly")
    else:
        print("\n@@@@@ FAILURE @@@@@\n")
    exit(differ_out)
