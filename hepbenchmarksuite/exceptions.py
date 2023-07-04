"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""


class PreFlightError(Exception):
    """Couldn't pass pre-flight checks."""
    pass


class BenchmarkFailure(Exception):
    """An exception for a failed benchmark."""
    pass


class BenchmarkFullFailure(Exception):
    """An exception for when all benchmarks failed."""
    pass


class InstallHEPscoreFailure(Exception):
    """Could not install hepscore."""
    pass


class PluginAssertError(Exception):
    """An exception raised in case of an invalid state of a plugin."""
    pass


class PluginMetadataException(Exception):
    """An exception raised when plugin registration fails."""
    pass


class PluginBuilderException(Exception):
    """An exception raised when plugin building fails."""
    pass
