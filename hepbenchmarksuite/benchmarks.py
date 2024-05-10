"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""

import logging
import os
import subprocess
import sys
import yaml

from importlib_metadata import version, PackageNotFoundError
from pkg_resources import parse_version

from hepbenchmarksuite import utils
from hepbenchmarksuite.exceptions import InstallHEPscoreFailure

_log = logging.getLogger(__name__)


def validate_spec(conf, bench):
    """Check if the configuration is valid for [hep]spec.

    Args:
      conf:  A dict containing configuration.

    Returns:
      Error code: 0 OK , 1 Not OK
    """
    _log.debug("Configuration to apply validation: %s", conf)

    # Config section to use
    if bench in ('hs06', 'spec2017'):
        spec = conf[bench]

    # Required params to perform an [hep]spec benchmark
    spec_req = ['image', 'hepspec_volume']

    try:
        # Check what is missing from the config file in the [hep]spec category
        missing_params = list(filter(lambda x: spec.get(x) is None, spec_req))

        if len(missing_params) >= 1:
            _log.error("Required parameter not found in configuration: %s", missing_params)
            return 1

    except KeyError:
        _log.error("No configuration found for %s", bench)
        return 1

    return 0


def install_hepscore(package, force=False):
    """Install hepscore.

    Args:
      package: Package to be installed.
      force: To force installation.

    Raises:
      InstallHepScoreFailure: If it fails to install
    """

    runflags = ["-m", "pip", "install", "--user"]

    if 'VIRTUAL_ENV' in os.environ:
        _log.info("Virtual environment detected: %s", os.environ['VIRTUAL_ENV'])
        _log.info("Installing hep-score in virtual environment.")
        runflags = ["-m", "pip", "install"]

    if force:
        runflags.append("--force-reinstall")

    _log.info('Attempting the installation of hep-score.')
    _log.debug('Installation flags: %s', runflags)

    try:
        subprocess.check_call([sys.executable, *runflags, package])

    except subprocess.CalledProcessError as e:
        _log.exception('Failed to install hep-score')
        raise InstallHEPscoreFailure from e

    _log.info('Installation of hep-score succeeded.')


def prep_hepscore(conf):
    """Prepare hepscore installation.

    Args:
      conf: A dict containing configuration.

    Returns:
      Error code: 0 OK , 1 Not OK
    """

    hs_key = get_hepscore_key(conf)
    req_version = conf[hs_key]['version']
    hepscore_url = f'git+https://gitlab.cern.ch/hep-benchmarks/hep-score.git@{req_version}'

    _log.info("Checking if hep-score is installed.")

    try:

        sys_version = version('hep-score')
        _log.info("Found existing installation of hep-score in the system: v%s", sys_version)

        # If the installation matches the one in the config file we can resume.
        if parse_version(req_version) == parse_version(sys_version):
            _log.info("Installation matches requested version in the config file: %s", req_version)
            return 0

        # Force the re-installation of desired version in the config
        _log.warning("Installed version (%s) differs from config file (%s) - forcing reinstall",
                     sys_version, req_version)
        try:
            install_hepscore(hepscore_url, force=True)
        except InstallHEPscoreFailure:
            return 1

    except PackageNotFoundError:
        _log.info('Installation of hep-score not found in the system.')

        try:
            install_hepscore(hepscore_url)
        except InstallHEPscoreFailure:
            return 1

    # Recursive call for the cases that we perform reinstall
    # but we want to repeat the same check sequence
    return prep_hepscore(conf)


def run_hepscore(suite_conf):
    """Import and run hepscore."""

    try:
        _log.info("Attempting to import hepscore")
        import hepscore.hepscore # pylint: disable=import-outside-toplevel
        _log.info("Successfully imported hepscore")
    except ImportError:
        _log.exception("Failed to import hepscore!")
        return -1

    # Abort if section is commented
    if 'hepscore' not in suite_conf:
        _log.error("The hepscore section was not found in configuration file.")
        sys.exit(1)

    _hsconf = suite_conf['hepscore']['config']
    _hsfinal = _hsconf
    # Use hepscore-distributed config by default
    if _hsconf  == "default" or _hsconf.startswith("builtin://"):
        _log.info("Using %s config provided by hepscore.", _hsconf)
        if _hsconf == "default":
            # config_path available in 1.5rc4+ but not available in earlier releases
            _hsfinal = os.path.join(hepscore.__path__[0], 'etc/hepscore-default.yaml')
        else:
            if 'named_conf' in dir(hepscore.hepscore):
                _hsfinal = hepscore.hepscore.named_conf(_hsconf[10:]) # pylint: disable=no-member
            else:
                _log.error("Installed version of hepscore does not support the builtin:// option")
                return -1

    elif _hsconf.startswith("http://") or _hsconf.startswith("https://"):
        _log.info("Loading config from remote: %s", _hsconf)

        # Save the remote file to the user specified rundir
        _hsfinal = os.path.join(suite_conf['global']['rundir'], "hepscore.yaml")
        # Download remote file
        if utils.download_file(_hsconf, _hsfinal) != 0:
            _log.error("Error downloading %s", _hsconf,)
            return -1

    else:
        _log.info("Loading user provided config: %s", _hsfinal)

    try:
        with open(_hsfinal, 'r', encoding='utf-8') as conf:
            hepscore_conf = yaml.full_load(conf)
    except FileNotFoundError:
        _log.error("hepscore config file not found: %s", _hsfinal)
        return -1
    except OSError:
        _log.exception("Unable to load config yaml %s.", _hsfinal)
        return -1

    hs_key = get_hepscore_key(hepscore_conf)
    # ensure same runmode as suite
    hepscore_conf[hs_key]['settings']['container_exec'] = suite_conf['global']['mode']

    # BMK-1389: ncores is now always passed to compatible hepscore versions if present
    hepscore_version = parse_version(version('hep-score'))
    ncores_version = parse_version('v1.6rc2')
    
    if 'ncores' in suite_conf['global']:        
        if hepscore_version < ncores_version:
            if int(suite_conf['global']['ncores']) != os.cpu_count():
                _log.error("The number of cores cannot be configured in the current version of hepscore: %s. Please, update \
                            hepscore to v2.0 or above, or remove this parameter from the configuration.", hepscore_version)
                return -1
            else:
                _log.info("The current version of hepscore cannot run on a number of cores different from the total. \
                          If you wish to use this feature (ncores), please update hepscore to v2.0 or above.")
        else:
            hepscore_conf[hs_key]['settings']['ncores'] = suite_conf['global']['ncores']

    if 'options' in suite_conf['hepscore'].keys():
        hepscore_conf[hs_key]['options'] = suite_conf['hepscore']['options']

    _log.debug(hepscore_conf)

    # Specify directory to output results
    hepscore_results_dir = os.path.join(suite_conf['global']['rundir'], 'HEPSCORE')

    # Initiate hepscore
    hep_score = hepscore.hepscore.HEPscore(hepscore_conf, hepscore_results_dir)

    # hepscore flavor of error propagation
    # run() returns score from last workload if successful
    _log.info("Starting hepscore")
    _log.debug("Config in use: %s", hepscore_conf)

    try:
        returncode = hep_score.run()
        if returncode >= 0:
            hep_score.gen_score()

        output_file = os.path.join(suite_conf['global']['rundir'], 'HEPSCORE/hepscore_result.json')
        hep_score.write_output("json", output_file)
    except SystemExit as e:
        _log.error("HEPScore execution failed with error code %s", e)

    return returncode


def run_hepspec(conf, bench):
    """Run [HEP]Spec benchmark.

    Args:
      conf:  A dict containing configuration.
      bench: A string with the benchmark to run.

    Return:
      POSIX exit code from subprocess
    """
    _log.debug("Configuration in use for benchmark %s: %s", bench, conf)

    # Config section to use
    if bench in ('hs06', 'spec2017'):
        spec = conf[bench]

    # Select run mode: docker, singularity, podman, etc
    run_mode = conf['global']['mode']

    # Possible [hep]spec arguments
    spec_args = {
        'iterations'    : f" -i {spec.get('iterations')}",
        'hepspec_volume': f" -p {spec.get('hepspec_volume')}",
        'bmk_set'       : f" -s {spec.get('bmk_set')}",
        'mode'          : f" -m {spec.get('mode')}",
        'url_tarball'   : f" -u {spec.get('url_tarball')}",
        'config'        : f" -c {spec.get('config')}"
    }
    _log.debug("spec arguments: %s", spec_args)

    # Populate CLI from the global configuration section
    _run_args = f" -b {bench}" \
                f" -w {conf['global'].get('rundir')}" \
                f" -n {conf['global'].get('ncores')}"

    # Populate CLI from the [hep]spec configuration section
    # Removing image key from this population since its specified bellow at command level
    populate_keys = [*spec.keys()]
    populate_keys.remove('image')

    for k in populate_keys:
        try:
            _run_args += spec_args[k]

        except KeyError as err:
            _log.error("Not a valid HEPSPEC06 key: %s.", err)

    # Check if docker image is properly passed
    docker_image = ''
    if run_mode == "docker":
        if spec['image'].startswith('docker://'):
            docker_image = spec['image'].replace('docker://', '')

        else:
            _log.error("Invalid docker image specified. Image should start with docker://")
            return 1

    # Set singularity cache dir
    env = os.environ.copy()
    if run_mode == "singularity":
        env["SINGULARITY_CACHEDIR"] = f"{conf['global']['parent_dir']}/singularity_cachedir"

    # Create the set of volumes to be mounted
    volumes = {conf['global']['rundir'], spec['hepspec_volume']}
    if 'extra_volumes' in conf['global']:
        volumes.update(conf['global']['extra_volumes'])

    # Command specification
    # pylint: disable=consider-using-f-string
    cmd = {
        'docker': "docker run --rm --network=host {0} {1} {2}"
            .format(format_volume_string('docker', volumes),
                    docker_image,
                    _run_args),
        'singularity': "singularity run {0} {1} {2}"
            .format(format_volume_string('singularity', volumes),
                    spec['image'],
                    _run_args)
    }

    # Start benchmark
    _log.debug(cmd[run_mode])
    return_code = utils.exec_live_output(cmd[run_mode], env)

    # Check for errors
    if return_code != 0:
        _log.error("Benchmark execution failed; returncode = %s", return_code)

    return return_code


def format_volume_string(platform, volumes):
    """Return a formatted string to attach the volumes to the platform through command line."""
    volume_formats = {
        'docker': "-v {0}:{0}:Z",
        'singularity': "-B {0}:{0}"
    }

    return ' '.join(list(map(volume_formats[platform].format, volumes)))


def get_hepscore_key(config):
    """ Returns the HEPscore key to be used for the configuration passed.
        If 'hepscore' is present, it takes precedence over the legacy 'hepscore_benchmark'.

        If none of them is present, an exception is raised instead."""

    for key in ['hepscore', 'hepscore_benchmark']:
        if key in config:
            return key

    raise ValueError("The configuration does not contain a valid HEPscore key: ", config)
