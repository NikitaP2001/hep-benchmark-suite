"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""

import json
import logging
import os
import platform
import re
from subprocess import Popen, PIPE
import socket
import sys
import shutil

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

        req_packages = ('lshw', 'ipmitool', 'dmidecode')

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
        """Accept command string and returns output."""
        _log.debug("Excuting command: %s", cmd_str)

        cmd = Popen(cmd_str, shell=True, executable='/bin/bash',  stdout=PIPE, stderr=PIPE)
        cmd_reply, cmd_error = cmd.communicate()

        # Check for errors
        if cmd.returncode != 0:
            cmd_reply = "extractor_exec_cmd_fail"
            _log.error(cmd_error)

        # Force not_available when command return is empty
        elif len(cmd_reply) == 0 and cmd.returncode == 0:
            _log.debug('Result is empty: %s', cmd_reply)
            cmd_reply = "not_available"

        else:
            # Convert bytes to text and remove \n
            try:
                cmd_reply = cmd_reply.decode('utf-8').rstrip()
            except UnicodeDecodeError:
                _log.error("Failed to decode to utf-8: %s", cmd_reply)
                cmd_reply = "not_available"

        return cmd_reply

    def collect_sw(self):
        """Collect Software specific metadata."""
        # FIXME not tested
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

        # Update with additional data
        cpu.update({
            'Power_Policy': self.exec_cmd("cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort | uniq"),
            'Power_Driver': self.exec_cmd("cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_driver   | sort | uniq"),
            'Microcode'   : self.exec_cmd("grep microcode /proc/cpuinfo | uniq | awk 'NR==1{print $3}'"),
            'SMT_Enabled' : self.exec_cmd("cat /sys/devices/system/cpu/smt/active")
        })

        return cpu

    def format_converter(self, req, req_typ):
        """Convert data to specified type."""

        if req == 'not_available' and (req_typ in (float, int)):
            return req_typ(-1)
        else:
            try:
                return req_typ(req)
            except ValueError:
                _log.error('Failed to cast %s to %s.'%(req, req_typ))
                return req

    # TESTED
    def get_cpu_parser(self, cmd_output):
        """Collect all CPU data from lscpu."""
        parser_lscpu = self.get_parser(cmd_output, "lscpu")

        conv = lambda req,req_typ : self.format_converter(req, req_typ)

        cpu = {
            'Architecture'     : conv(parser_lscpu("Architecture"),str),
            'CPU_Model'        : conv(parser_lscpu("Model name"),str),
            'CPU_Family'       : conv(parser_lscpu("CPU family"),str),
            'CPU_num'          : conv(parser_lscpu(r"CPU\(s\)"), int),
            'Online_CPUs_list' : conv(parser_lscpu(r"On-line CPU\(s\) list"),str),
            'Threads_per_core' : conv(parser_lscpu(r"Thread\(s\) per core"), int),
            'Cores_per_socket' : conv(parser_lscpu(r"Core\(s\) per socket"), int),
            'Sockets'          : conv(parser_lscpu(r"Socket\(s\)"), int),
            'Vendor_ID'        : conv(parser_lscpu("Vendor ID"),str),
            'Stepping'         : conv(parser_lscpu("Stepping"),str),
            'CPU_MHz'          : conv(parser_lscpu("CPU MHz"), float),
            'CPU_Max_Speed_MHz': conv(parser_lscpu("CPU max MHz"), float),
            'CPU_Min_Speed_MHz': conv(parser_lscpu("CPU min MHz"), float),
            'BogoMIPS'         : conv(parser_lscpu("BogoMIPS"), float),
            'L2_cache'         : conv(parser_lscpu("L2 cache"),str),
            'L3_cache'         : conv(parser_lscpu("L3 cache"),str),
            'NUMA_nodes'       : conv(parser_lscpu(r"NUMA node\(s\)"), int),
        }

        # ARM-specific logic
        if cpu['Architecture'] == 'aarch64':
            if cpu['L2_cache'] == 'not_available':
                cpu['L2_cache'] = conv(parser_lscpu("L2"), str)
            if self._permission:
                cpu['CPU_Model'] = cpu['CPU_Model'] + " - " + conv(parser_lscpu("BIOS Model name"),str)

        # Populate NUMA nodes
        try:
            for i in range(0, int(cpu['NUMA_nodes'])):
                cpu['NUMA_node{}_CPUs'.format(i)] = conv(parser_lscpu(r"NUMA node{} CPU\(s\)".format(i)),str)
        except ValueError:
            _log.warning('Failed to parse or NUMA nodes not existent.')

        return cpu

    # TESTED
    def collect_bios(self):
        """Collect all relevant BIOS information."""
        _log.info("Collecting BIOS information.")

        # get common parser
        if self.pkg['dmidecode'] and self._permission:
            parse_bios = self.get_parser(self.exec_cmd("dmidecode -t bios"), "bios")
        else:
            parse_bios = lambda x: "not_available"

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

        is_virtual = (int(self.exec_cmd("grep -c hypervisor /proc/cpuinfo || [[ $? -le 1 ]] ")) >= 1)

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

    # TESTED
    @staticmethod
    def get_mem_parser(cmd_output):
        """Memory parser for dmidecode."""
        
        # Regex for matches
        reg_size = re.compile(r'(?P<Field>Size:\s*\s)(?P<value>(?!No Module Installed).*\S)')
        reg_part = re.compile(r'(?P<Field>Part Number:\s*\s)(?P<value>(?!NO DIMM).*\S)')
        reg_man  = re.compile(r'(?P<Field>Manufacturer:\s*\s)(?P<value>(?!NO DIMM).*\S)')
        reg_type = re.compile(r'(?P<Field>Type:\s*\s)(?P<value>(?!Unknown).*\S)')

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

    # TESTED
    @staticmethod
    def get_storage_parser(cmd_output):
        """Storage parser for lshw -c disk."""
        
        # Regex for matches
        reg_logic   = re.compile(r'(?P<Field>logical name:\s*\s)(?P<value>.*)')
        reg_product = re.compile(r'(?P<Field>product:\s*\s)(?P<value>.*)')
        reg_size    = re.compile(r'(?P<Field>size:\s*\s)(?P<value>.*)')

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
                expr = r'(?P<Field>{}\s*:\s)(?P<Value>.*)'.format(pattern)
            else:
                expr = r'(?P<Field>{}:\s*\s)(?P<Value>.*)'.format(pattern)

            # Search pattern in output
            result = re.search(expr, cmd_output)
            try:
                _log.debug("Parsing = %s | Field = %s | Value = %s", reg,
                                                                     pattern,
                                                                     result.group('Value'))
                return result.group('Value')

            except AttributeError:
                _log.debug("Parsing = %s | Field = %s | Value = %s", reg, pattern, "None")
                return "not_available"

        return parser

    # TESTED
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

    def _extract(self, cmd_dict):
        """Extract the data given a dict with commands."""
        data = {}
        for key, val in cmd_dict.items():
            self.data[key] = self.exec_cmd(val)

        return data

    def _save(self, tag, new_data):
        """Save a given dict to the final data dict."""
        self.data[tag] = new_data
