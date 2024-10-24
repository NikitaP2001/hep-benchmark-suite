#!/usr/bin/env python3
"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
################################################################################
"""

import logging
import sys
from hepbenchmarksuite.plugins.extractor import Extractor

def main():
# Configure logging
    logger         = logging.getLogger()
    LOG_FORMAT     = logging.Formatter('%(levelname)s  %(asctime)s [%(name)s]  %(message)s',  datefmt='%Y-%m-%d %H:%M:%S')
    LOG_HANDLER    = logging.StreamHandler(stream=sys.stdout)
    LOG_LEVEL      = logging.DEBUG

    # Add handlers for logging
    logger.setLevel(LOG_LEVEL)
    LOG_HANDLER.setFormatter(LOG_FORMAT)
    logger.addHandler(LOG_HANDLER)

    # Collect data
    hw = Extractor(extra={'mode':''})
    hw.collect()

    # Print the output to stdout and save metadata to json file
    hw.dump(stdout=True)

    # hw.export() returns a dict which can be used for other python integrations.
    print(hw.export())


if __name__ == "__main__":
    main()