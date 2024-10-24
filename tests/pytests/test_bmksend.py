#!/usr/bin/env python3
"""
###############################################################################
# Copyright 2019-2020 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""

from datetime import datetime
import json
import os
import unittest
from unittest.mock import patch, mock_open, MagicMock

# from bin import bmksend


class TestBmkSend(unittest.TestCase):
    """AMQ bmksend functionality.
    test CLI interface to send_queue
    """

    # TODO: The current way we structure this repo ("binaries" in /bin) are not test-able without .py extensions...
    pass
