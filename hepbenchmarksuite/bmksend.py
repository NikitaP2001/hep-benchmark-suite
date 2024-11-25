#!/usr/bin/env python3
"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
################################################################################
"""
import argparse
import logging
from pathlib import Path
import sys
import yaml
from hepbenchmarksuite.plugins import send_queue
from hepbenchmarksuite.plugins import send_opensearch


logging.basicConfig(
    format="%(asctime)s, %(name)s:%(funcName)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("bmksend")

# suite report filename, as hard-coded in `bmkrun`.
# this global is used to limit uploading of renamed result json
REPORT = "bmkrun_report.json"


def main():
    """CLI entrypoint for batch AMQ uploading"""
    parser = argparse.ArgumentParser(
        description="Utility for sending 'bmkrun_report.json' to an AMQ broker via STOMP. "
        "Connection details from your custom config.yaml are used for credentials."
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        required=True,
        help="yaml containing connection credentials.",
    )
    parser.add_argument(
        "-d", "--dryrun", action="store_true", help="Dry Run (nothing sent)"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose printing")
    parser.add_argument(
        "-f", "--force", action="store_true", help="override check of report name"
    )
    parser.add_argument(
        "report_path", nargs="+", type=Path, help="Path(s) to bmkrun_report.json"
    )
    args = parser.parse_args()

    # Configure logging
    logger.setLevel(logging.DEBUG) if args.verbose else logger.setLevel(logging.INFO)
    logger.debug(args)

    # Load configuration file
    try:
        with args.config.resolve().open() as yam:
            active_config = yaml.full_load(yam)
            logger.debug("Found config %s", args.config)
    except FileNotFoundError:
        print("Failed to load configuration file: {}".format(args.config.resolve()))
        sys.exit(1)

    # Build upload list
    reportlist = []
    forcelist = []
    for path in args.report_path:
        if path.is_file() and path.suffix == ".json":
            if path.name == REPORT:
                reportlist.append(path.resolve())
                logger.debug("%s added to reports", path)
            else:
                if args.force:
                    forcelist.append(path.resolve())
                    logger.debug("%s JSON added by force", path)
                else:
                    logger.warning(
                        "%s passed, but does not match pattern '%s'. Use '--force' to send.",
                        path,
                        REPORT,
                    )
        elif path.is_dir():
            logger.debug("Traversing %s for reports", path)
            for file in path.rglob("*.json"):
                if file.name == REPORT:
                    reportlist.append(file.resolve())
                    logger.debug("%s added to reports", file)
                elif args.force:
                    forcelist.append(file.resolve())
                    logger.debug("%s JSON added by force", file)
                else:
                    logger.debug("Skipping %s without force flag.", file)
        else:
            logger.warning("skipping %s, not a JSON or dir.", path)

    sendlist = reportlist
    if args.force:
        sendlist = reportlist + forcelist
        print(
            "FORCE: Found {} additional json. {} will be transmitted!".format(
                len(forcelist), len(forcelist + reportlist)
            )
        )

    # send
    sentcount = 0
    for file in sendlist:
        if args.dryrun:
            pass
        else:
            try:
                if active_config.get("activemq", False):
                    connection = active_config["activemq"]
                    send_queue.send_message(file, connection)
                elif active_config.get("opensearch", False):
                    connection = active_config["opensearch"]
                    send_opensearch.send_message(file, connection)
                else:
                    raise Exception("No publisher configuration was found.")
                print("Sent {}".format(file))
                sentcount += 1
            except Exception as err:
                logger.error("Something went wrong attempting to report via AMQ/OpenSearch.")
                logger.error("Results may not have been correctly transmitted.")
                logger.exception(err)

    if args.dryrun:
        print("DRYRUN: Found {} matching reports:".format(len(reportlist)))
        for report in reportlist:
            print(report)
        if args.force:
            print("DRYRUN: Found {} additional JSON:".format(len(forcelist)))
            for report in forcelist:
                print(report)
        print("DRYRUN: Would have transmitted {} JSON".format(len(sendlist)))
        print("DRYRUN: may be repeated with '--force' arg to see other JSON.")
        print("DRYRUN: No files have been sent.")
    elif sentcount != len(sendlist):
        print("Sent {} files out of {} requested.".format(sentcount, len(sendlist)))
        print("Please verify connection credentials!")


if __name__ == "__main__":
    main()
