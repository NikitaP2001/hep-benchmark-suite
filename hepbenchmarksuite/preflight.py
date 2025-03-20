""" Preflight checks """

import logging
import shutil
import subprocess
import platform

from os import makedirs, path, cpu_count, sysconf
from hepbenchmarksuite import benchmarks, utils
from hepbenchmarksuite.plugins.send_queue import is_key_password_protected

_log = logging.getLogger(__name__)


class Preflight:
    """ Contains several suite-requirement checks that are performed over a given config """

    def __init__(self, config):
        self.benchmarks_to_run = config['global']['benchmarks']
        self.global_config = config['global']
        self.full_config = config
        self.failed_checks = []

        try:
            self.hw_config = config['global']['hw_requirements']
            _log.info("Hardware requirements configuration found")
        except KeyError:
            _log.info(
                "No hardware requirements configuration specified, skipping")

        try:
            self.sw_config = config['global']['sw_requirements']
            _log.info("Software requirements configuration found")
        except KeyError:
            _log.info(
                "No software requirements configuration specified, skipping")

    def check(self):
        """Perform pre-flight checks."""

        _log.info("Running pre-flight checks")

        self.check_deprecation()
        self.check_run_mode()
        self.check_working_directories()
        self.validate_spec_config()

        if 'hw_requirements' in self.global_config:
            self.check_disk_space()
            self.check_mem_per_core()

        if 'sw_requirements' in self.global_config:
            self.check_selinux_disabled()
            self.check_root_access()

        # Check if any pre-flight check failed
        if any(self.failed_checks):
            return False
        else:
            return True

    def check_deprecation(self):
        """ Warn the user if any deprecated option has been used.
            The execution will continue whenever possible.
        """

        if 'hs06' in self.benchmarks_to_run:
            if 'hepspec06' in self.full_config:
                _log.warning("Your 'hs06' configuration is under the legacy key 'hepspec06'. "
                             "Please change it to 'hs06'.")
                self.full_config['hs06'] = self.full_config['hepspec06']

    def validate_amq_config(self):
        """ Check if the private key used for AMQ is password protected and warn the user if so """
        if self.global_config.get('publish') and 'activemq' in self.full_config:
            _log.info(" - Checking AMQ configuration for key protection")
            amq_cfg = self.full_config['activemq']
            if "key" in amq_cfg and is_key_password_protected(amq_cfg['key']):
                _log.warning("The private key is password protected. After the benchmark execution "
                             "the execution will stall until the password is introduced.")
                _log.warning("Alternatively, you may set the publish variable to false and send "
                             "the results afterwards using bmksend, which is included in the suite")

    def check_disk_space(self):
        """ Check if the rundir has enough free space """
        _log.info(" - Checking if rundir has enough space...")
        _log.info(" - Getting cpu core count from configuration")
        cpus = self.get_ncores()
        if not cpus:
            self.failed_checks.append(1)
            return
        _log.info(" - core count: %i", int(cpus))

        disk_stats = shutil.disk_usage(self.global_config['rundir'])
        disk_space_gb = round(disk_stats.free * (10 ** -9), 2)
        disk_space_per_core = disk_space_gb/int(cpus)
        _log.info("Calculated disk space: %s GB, GB per core: %s",
                  *(disk_space_gb, disk_space_per_core))

        if 'min_disk_per_core' not in self.hw_config:
            # _log.warning("Hardware requirement configuration missing: 'min_disk_per_core'")
            _log.error(
                "Hardware requirement configuration missing: 'min_disk_per_core'")
            # either set a default so it runs or return an error
            # for now we'll fail the check
            self.failed_checks.append(1)

        running_only_db12 = len(
            self.benchmarks_to_run) == 1 and 'db12' in self.benchmarks_to_run
        if disk_space_per_core <= self.hw_config.get('min_disk_per_core') and not running_only_db12:
            _log.error("Not enough disk space on %s, free: %s GB per core, required: %s GB/core",
                       self.global_config['rundir'], disk_space_per_core, self.hw_config.get('min_disk_per_core'))

            # Flag for a failed check
            self.failed_checks.append(1)

    def check_mem_per_core(self):
        """ Check if the system has enough memory based on config requirements """
        _log.info(" - Checking if system has enough memory")
        _log.info(" - Getting cpu core count from configuration")
        cpus = self.get_ncores()
        if not cpus:
            _log.info(" - Unable to get CPU core count, exiting")
            self.failed_checks.append("check_mem_per_core/get_ncores")
            return

        try:
            cpus = float(cpus)
        except ValueError:
            _log.info(" - Unable to parse CPU core count, exiting")
            self.failed_checks.append("check_mem_per_core/get_ncores")
            return

        if platform.system() == "Linux":
            _log.info(" - Getting installed system memory from OS")
            free_cmd_result = subprocess.getoutput("free -b")
            free_cmd_lines = free_cmd_result.splitlines()
            mem_total = 0
            swap_total = 0
            for line in free_cmd_lines:
                if line.startswith("Mem:"):
                    mem_total = int(line.split()[1])
                elif line.startswith("Swap:"):
                    swap_total = int(line.split()[1])
            system_memory = (mem_total + swap_total) / (1024.**3)
        else:
            _log.info(" - OS is not Linux, cannot check for RAM, skipping check")
            return

        if 'min_memory_per_core' not in self.hw_config:
            _log.error(
                "Hardware requirement configuration missing: 'min_memory_per_core'")
            # either set a default so it runs or return an error
            # for now we'll fail the check

            # Flag a failed check if config property does not exist
            self.failed_checks.append(
                "check_mem_per_core/missing_config_property")
            return

        mem_per_core = system_memory / cpus
        _log.info("Reported system memory: %s GB, GB per core: %s",
                  system_memory, mem_per_core)

        if mem_per_core < self.hw_config.get('min_memory_per_core'):
            _log.error("Not enough system memory per core (%s GB reported, %s GB required).",
                       mem_per_core, self.hw_config.get('min_memory_per_core'))
            _log.error("Consider adding some swap.")
            # Flag a failed check if there is not enough memory per core
            self.failed_checks.append("check_mem_per_core/insufficient_memory")

    def check_selinux_disabled(self):
        if 'check_selinux_disabled' not in self.sw_config:
            _log.error(
                "Hardware requirement configuration missing: 'check_selinux_disabled'")
            # Flag a failed check if config property does not exist
            self.failed_checks.append(
                "check_selinux_disabled/missing_config_property")

        if not self.sw_config.get('check_selinux_disabled'):
            return

        selinux_status = subprocess.getoutput("sestatus")
        if "enabled" in selinux_status.lower():
            # Flag a failed check if SELinux is enabled
            _log.error(
                "Software requirement 'check_selinux_disabled' failed, please disable SELinux")
            self.failed_checks.append("check_selinux/enabled")
        return

    def check_root_access(self):
        if 'check_root_access' not in self.sw_config:
            _log.error(
                "Software requirement configuration missing: 'check_root_access'")
            # Flag a failed check if config property does not exist
            self.failed_checks.append(
                "check_root_access/missing_config_property")

        if not self.sw_config.get('check_root_access'):
            return

        current_user = subprocess.getoutput("whoami")
        if "root" not in current_user.lower():
            # Flag a failed check if user is not root
            _log.error(
                "Software requirement 'check_root_access' failed, please execute as root")
            self.failed_checks.append("check_root_access/not_root")
        return

    def check_docker_version(self, docker_version):
        if 'min_docker_version' in self.sw_config:
            if utils.versiontuple(docker_version) < utils.versiontuple(self.sw_config.get('min_docker_version')):
                _log.error("Software requirement docker_version > %s failed (current version: %s). Please upgrade docker.",
                           self.sw_config.get('min_docker_version'), docker_version)
                # Flag a failed check if version is below minimum
                self.failed_checks.append("check_docker_version/bad_version")

    def validate_spec_config(self):
        """ Validate [HEP]Spec configuration """
        _log.info(" - Checking for a valid configuration...")
        for bench in self.benchmarks_to_run:
            if bench in ('hs06', 'spec2017'):
                self.failed_checks.append(
                    benchmarks.validate_spec(self.full_config, bench))

    def check_working_directories(self):
        """ Ensure the specified working directories exist """

        _log.info(" - Checking provided work dirs exist...")
        makedirs(self.global_config['rundir'], exist_ok=True)

        if 'hs06' in self.benchmarks_to_run:
            makedirs(self.full_config['hs06']['hepspec_volume'], exist_ok=True)

        if 'spec2017' in self.benchmarks_to_run:
            makedirs(self.full_config['spec2017']
                     ['hepspec_volume'], exist_ok=True)

        if 'hepscore' in self.benchmarks_to_run:
            makedirs(
                path.join(self.global_config['rundir'], "HEPSCORE"), exist_ok=True)

    def check_run_mode(self):
        """ Check whether the selected executor is installed in the system """

        _log.info(" - Checking if selected run mode exists...")
        mode = self.global_config['mode']

        # Avoid executing commands if they are not valid run modes.
        # This avoids injections through the configuration file.
        if mode in ('docker', 'singularity'):
            # Search if run mode is installed
            system_run_mode = shutil.which(mode)

            if system_run_mode is not None:
                _log.info("   - %s executable found: %s.",
                          mode, system_run_mode)

                # TODO: change to match/case when moving to Python3.10
                if mode == 'docker':
                    version, _ = utils.exec_cmd(
                        "docker version --format '{{.Server.Version}}'")
                    self.check_docker_version(version)

                elif mode == 'singularity':
                    version, _ = utils.exec_cmd('singularity version')

                _log.info("   - %s version: %s.", mode, version)

            else:
                _log.error("   - %s is not installed in the system.", mode)
                self.failed_checks.append(1)

        else:
            _log.error("Invalid run mode specified: %s.", mode)
            self.failed_checks.append(1)

    def get_ncores(self):
        cpus = self.global_config.get('ncores')
        if not cpus:
            # problem getting CPUs from config or it's unconfigured try again with nproc
            _log.info(
                " - ncores not found in configuration, gathering core count from nproc")
            cpus, _ = utils.exec_cmd('nproc')
        if not cpus:
            # if the config is empty and nproc fails we'll try one last time with os.cpu_count()
            _log.info(
                " - nproc unable to determine core count, trying again with os.cpu_count")
            cpus = cpu_count()
        if not cpus:
            # unable to determine number of cpus from any source
            _log.error(
                " - Unable to determine number of cores from system or configuration.")
            return None
        return cpus
