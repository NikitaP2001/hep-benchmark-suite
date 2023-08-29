"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""

from glob import glob
import json
import logging
import os
import platform
import re
import socket
import sys
import shutil

from hepbenchmarksuite import utils

_log = logging.getLogger(__name__)


class Extractor():
    """********************************************************
                    *** HEP-BENCHMARK-SUITE ***
        This class allows you to extract Hardware Metadata.

        This tool depends on some system tools and will check for
        their existence. For a complete data dump, it is recommend
        to run as priviledge user.

    *********************************************************"""

    def __init__(self, extra):
        """Initialize setup."""
        self.data = {}
        self.pkg = {}
        self.extra = extra

        # Check if the script is run as root user; needed to extract full data.

        if os.geteuid() != 0:
            _log.info("you should run this program as super-user for a complete output.")
            self._permission = False
        else:
            self._permission = True

        # Check if the required tools to extract the data are installed.
        # If the tools are not present, the output will be limited on certain fields.
        # The dict self.pkg enforces the switching of outputs.

        req_packages = ('lshw', 'ipmitool', 'dmidecode', 'facter')

        for pkg_name in req_packages:

            _sys_pkg = shutil.which(pkg_name)

            if _sys_pkg is not None:
                _log.debug("Package installed: %s", pkg_name)
                self.pkg[pkg_name] = True
            else:
                _log.debug("Package not installed: %s", pkg_name)
                self.pkg[pkg_name] = False

        _log.debug("Installed packages: %s", self.pkg)

    def exec_cmd(self, cmd_str):
        """Execute a command string and return its output."""
        reply, _ = utils.exec_cmd(cmd_str)
        return reply

    def collect_sw(self):
        """Collect Software specific metadata."""
        _log.info("Collecting SW information.")


        sw_cmd = {}

        if self.extra['mode'] == 'docker':
            sw_cmd.update({'docker': "docker version --format '{{.Server.Version}}'"})

        elif self.extra['mode'] == 'singularity':
            sw_cmd.update({'singularity': 'singularity version'})


        software = {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
        }

        # Execute commands and append result to a dict
        for key, val in sw_cmd.items():
            software[key] = self.exec_cmd(val)

        return software

    def collect_cpu(self):
        """Collect all relevant CPU information."""
        _log.info("Collecting CPU information.")

        # Get the parsing result from lscpu
        cpu = self.get_cpu_parser(self.exec_cmd("lscpu"))

        # Expand paths
        scaling_governors = ' '.join(glob('/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor'))
        scaling_drivers = ' '.join(glob('/sys/devices/system/cpu/cpu*/cpufreq/scaling_driver'))

        # Default to /dev/null [BMK-1258]
        scaling_governors = scaling_governors if scaling_governors else '/dev/null'
        scaling_drivers = scaling_drivers if scaling_drivers else '/dev/null'

        # Update with additional data
        cpu.update({
            'Power_Policy': self.exec_cmd(f"cat {scaling_governors} | sort | uniq"),
            'Power_Driver': self.exec_cmd(f"cat {scaling_drivers} | sort | uniq"),
            'Microcode'   : self.exec_cmd("awk '/microcode/ {print $3}' /proc/cpuinfo | uniq"),
            'SMT_Enabled' : self.exec_cmd("cat /sys/devices/system/cpu/smt/active")
        })

        return cpu

    def get_cpu_parser(self, cmd_output):
        """Collect all CPU data from lscpu."""
        parse_lscpu = self.get_parser(cmd_output, "lscpu")

        def conv(arg, req_typ=str):
            """Convert data to specified type."""

            res = parse_lscpu(arg)

            if res == 'not_available' and (req_typ in (float, int)):
                return req_typ(-1)
            try:
                return req_typ(res)
            except ValueError:
                return res

        cpu = {
            'Architecture'     : conv("Architecture"),
            'CPU_Model'        : conv("Model name"),
            'CPU_Family'       : conv("CPU family"),
            'CPU_num'          : conv(r"CPU\(s\)", int),
            'Online_CPUs_list' : conv(r"On-line CPU\(s\) list"),
            'Threads_per_core' : conv(r"Thread\(s\) per core", int),
            'Cores_per_socket' : conv(r"Core\(s\) per socket", int),
            'Sockets'          : conv(r"Socket\(s\)", int),
            'Vendor_ID'        : conv("Vendor ID"),
            'Stepping'         : conv("Stepping"),
            'CPU_MHz'          : conv("CPU MHz", float),
            'CPU_Max_Speed_MHz': conv("CPU max MHz", float),
            'CPU_Min_Speed_MHz': conv("CPU min MHz", float),
            'BogoMIPS'         : conv("BogoMIPS", float),
            'L2_cache'         : conv("L2 cache"),
            'L3_cache'         : conv("L3 cache"),
            'NUMA_nodes'       : conv(r"NUMA node\(s\)", int),
        }

        # ARM-specific logic
        if cpu['Architecture'] == 'aarch64':
            if cpu['L2_cache'] == 'not_available':
                cpu['L2_cache'] = conv("L2")
            if self._permission:
                cpu['CPU_Model'] = cpu['CPU_Model'] + " - " + conv("BIOS Model name")

        # Populate NUMA nodes
        try:
            for i in range(0, int(cpu['NUMA_nodes'])):
                cpu['NUMA_node{}_CPUs'.format(i)] = parse_lscpu(r"NUMA node{} CPU\(s\)".format(i))
        except ValueError:
            _log.warning('Failed to parse or NUMA nodes not existent.')

        return cpu

    def collect_bios(self):
        """Collect all relevant BIOS information."""
        _log.info("Collecting BIOS information.")
        
        # get common parser
        if self.pkg['dmidecode'] and self._permission:
            parse_bios = self.get_parser(self.exec_cmd("dmidecode -t bios"), "bios")
        else:
            def parse_bios(sysfsEntry):
                """
                read from syfs - BIOS Board entries readable for users on most systems
                """
                sysfsBasePath="/sys/class/dmi/id/"
                sysfsDict = {
                    'Version':'bios_version',
                    'Vendor':'bios_vendor',
                    'Release Date':'bios_date',
                    'Board Version':'board_version',
                    'Board Vendor':'board_vendor',
                }
                try:
                    with open(os.path.join(sysfsBasePath,sysfsDict[sysfsEntry]), 'r') as f:
                        return(f.read().strip())
                except:
                    return "not_available"

        bios = {
            'Vendor'      : parse_bios("Vendor"),
            'Version'     : parse_bios("Version"),
            'Release_data': parse_bios("Release Date"),
        }

        return bios

    def collect_system(self):
        """Collect relevant BIOS information."""
        _log.info("Collecting system information.")

        # get common parser
        if self.pkg['dmidecode'] and self._permission:
            parse_system = self.get_parser(self.exec_cmd("dmidecode -t system"), "system")
        else:
            parse_system = lambda x: "not_available"

        if self.pkg['ipmitool'] and self._permission:
            parse_bmc_fru = self.get_parser(self.exec_cmd("ipmitool fru"), "BMC")
        else:
            parse_bmc_fru = lambda x: "not_available"

        if self.pkg['facter']:
            is_virtual = self.exec_cmd("facter is_virtual").casefold() == 'true'
        else:
            is_virtual = self.exec_cmd("grep hypervisor /proc/cpuinfo") != "not_available"

        system = {
            'Manufacturer'     : parse_system("Manufacturer"),
            'Product_Name'     : parse_system("Product Name"),
            'Version'          : parse_system("Version"),
            'Product_Serial'   : parse_bmc_fru("Product Serial"),
            'Product_Asset_Tag': parse_bmc_fru("Product Asset Tag"),
            'isVM'             : is_virtual
        }

        return system

    def collect_memory(self):
        """Collect system memory."""
        _log.info("Collecting system memory.")

        if self.pkg['dmidecode'] and self._permission:
            # Execute command and get output to parse
            cmd_output = self.exec_cmd("dmidecode -t 17")

            # Get memory parser for memory listing
            mem = Extractor.get_mem_parser(cmd_output)

        else:
            mem = {}

        mem.update({
            'Mem_Total'    : int(self.exec_cmd("free | awk 'NR==2{print $2}'")),
            'Mem_Available': int(self.exec_cmd("free | awk 'NR==2{print $7}'")),
            'Mem_Swap'     : int(self.exec_cmd("free | awk 'NR==3{print $2}'"))
        })

        return mem

    @staticmethod
    def get_mem_parser(cmd_output):
        """Memory parser for dmidecode."""
        # Regex for matches
        reg_size = re.compile(r'\n\s*(?P<Field>Size:\s*\s)(?P<value>(?!No Module Installed).*\S)')
        reg_part = re.compile(r'\n\s*(?P<Field>Part Number:\s*\s)(?P<value>(?!NO DIMM).*\S)')
        reg_man  = re.compile(r'\n\s*(?P<Field>Manufacturer:\s*\s)(?P<value>(?!NO DIMM).*\S)')
        reg_type = re.compile(r'\n\s*(?P<Field>Type:\s*\s)(?P<value>(?!Unknown).*\S)')

        # Return iterators containing matches
        result_size = re.finditer(reg_size, cmd_output)
        result_part = re.finditer(reg_part, cmd_output)
        result_man  = re.finditer(reg_man,  cmd_output)
        result_type = re.finditer(reg_type, cmd_output)

        count = 1
        mem = {}

        # Loop at same time each iterator
        for size, part, man, typ in zip(result_size, result_part, result_man, result_type):
            mem["dimm" + str(count)] = "{0} {1} | {2} | {3}".format(size.group('value'),
                                                                typ.group('value'),
                                                                man.group('value'),
                                                                part.group('value'))
            count += 1

        return mem

    def collect_storage(self):
        """Collect system memory."""
        _log.info("Collecting system storage.")

        if self.pkg['lshw'] and self._permission:
            # Execute command and get output to parse
            cmd_output = self.exec_cmd("lshw -c disk")

            # Get storage parser
            storage = Extractor.get_storage_parser(cmd_output)

        else:
            storage = {}

        return storage

    @staticmethod
    def get_storage_parser(cmd_output):
        """Storage parser for lshw -c disk."""
        # Regex for matches
        reg_logic   = re.compile(r'\n\s*(?P<Field>logical name:\s*\s)(?P<value>.*)')
        reg_product = re.compile(r'\n\s*(?P<Field>product:\s*\s)(?P<value>.*)')
        reg_size    = re.compile(r'\n\s*(?P<Field>size:\s*\s)(?P<value>.*)')

        # Return iterators containing matches
        result_logic   = re.finditer(reg_logic,   cmd_output)
        result_product = re.finditer(reg_product, cmd_output)
        result_size    = re.finditer(reg_size,    cmd_output)

        count = 1
        storage = {}
        for log, prod, siz in zip(result_logic, result_product, result_size):
            storage["disk" + str(count)] = "{0} | {1} | {2}".format(log.group('value'),
                                                                prod.group('value'),
                                                                siz.group('value'))
            count += 1

        return storage

    def get_parser(self, cmd_output, reg="common"):
        """Common regex parser."""
        def parser(pattern):
            """Parser function."""
            # Different regex for parsing different outputs
            if reg == "BMC":
                exp = r'(?P<Field>{}\s*:\s)(?P<Value>.*)'.format(pattern)
            else:
                exp = r'(?P<Field>{}:\s*\s)(?P<Value>.*)'.format(pattern)

            # Search pattern in output
            result = re.search(exp, cmd_output)
            try:
                _log.debug("Parsing = %s | Field = %s | Value = %s", reg,
                                                                     pattern,
                                                                     result.group('Value'))
                return result.group('Value')

            except AttributeError:
                _log.debug("Parsing = %s | Field = %s | Value = %s", reg, pattern, "None")
                return "not_available"

        return parser

    def collect(self):
        """Collect all metadata."""
        _log.info("Collecting the full metadata information.")

        self.data['Hostname'] = socket.getfqdn()
        self._save("SW", self.collect_sw())
        self._save("HW", self.collect_hw())

    def collect_hw(self):
        """Collect Hardware specific metadata."""
        _log.info("Collecting HW information.")

        hardware = {
            "CPU"    : self.collect_cpu(),
            "BIOS"   : self.collect_bios(),
            "SYSTEM" : self.collect_system(),
            "MEMORY" : self.collect_memory(),
            "STORAGE": self.collect_storage()
        }
        return hardware

    def dump(self, stdout=False, outfile=False):
        """Dump data to stdout and json file."""
        meta_data = json.dumps(self.data, indent=4)

        if stdout:
            print(meta_data)

        # Dump json data to file
        if outfile is not False:
            with open(outfile, 'w') as json_file:
                json.dump(self.data, json_file, indent=4, sort_keys=True)

    def export(self):
        """Export collected data as a dict."""
        return self.data


    def _save(self, tag, new_data):
        """Save a given dict to the final data dict."""
        self.data[tag] = new_data
