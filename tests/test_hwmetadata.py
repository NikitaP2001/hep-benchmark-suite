#!/usr/bin/env python3
"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""

import json
import unittest
from pathlib import Path
from hepbenchmarksuite.plugins.extractor import Extractor
from schema import Schema, And, Use, Optional, Or


class TestHWExtractor(unittest.TestCase):
    """********************************************************
                 *** HEP-BENCHMARK-SUITE ***

     Testing the extraction of Hardware Metadata.

    *********************************************************"""

    def test_command_success(self):
        """
        Test if the execution of a command is successfull.
        """

        hw = Extractor(extra={})
        result = hw.exec_cmd("echo 1")
        self.assertEqual(result, "1")

    def test_command_failure(self):
        """
        Test if the execution of a command fails.
        """

        hw = Extractor(extra={})
        result = hw.exec_cmd("echofail 1")
        self.assertEqual(result, "not_available")
        
    def test_command_success_with_grep(self):
        """
        Test if the execution of a command fails.
        """

        # || and && are NOT supported without the unsafe shell=True
        hw = Extractor(extra={})
        result = hw.exec_cmd("echo abc | grep -c 'abc'")
        self.assertEqual(result, "1")
        result = hw.exec_cmd("echo abc | grep -c 'def'")
        self.assertEqual(result, "not_available")
        result = hw.exec_cmd("grep 'def' nofile")
        self.assertEqual(result, "not_available")
        result = hw.exec_cmd("grep -c hypervisor /proc/cpuinfo")
        self.assertGreater(int(result), 0)

    def test_parser_bios(self):
        """
        Test the parser for a BIOS output.
        """

        hw = Extractor(extra={})

        with open("tests/data/BIOS.sample", "r") as bios_file:
            bios_text = bios_file.read()

        parser = hw.get_parser(bios_text)

        self.assertEqual(
            parser("Version"),
            "SE5C600.86B.02.01.0002.082220131453",
            "BIOS parser mismatch!",
        )
        self.assertEqual(parser("Vendor"), "Intel Corp.", "BIOS parser mismatch!")
        self.assertEqual(parser("Release Date"), "08/22/2013", "BIOS parser mismatch!")

    def base_parser_cpu(self, input_to_parse, expected_output):
        hw = Extractor(extra={})

        with open(input_to_parse, "r") as cpu_file:
            cpu_text = cpu_file.read()
            
        cpu_output = hw.get_cpu_parser(cpu_text)
        self.maxDiff = None
        self.assertEqual(cpu_output, expected_output, "CPU parser mismatch!")
        
    def test_parser_cpu_Intel(self):
        """
        Test the parser for an Intel CPU output.
        """
        CPU_OK = {
            "Architecture": "x86_64",
            "CPU_Model": "Intel(R) Xeon(R) CPU E5-2695 v2 @ 2.40GHz",
            "CPU_Family": "6",
            "CPU_num": 48,
            "Online_CPUs_list": "0-47",
            "Threads_per_core": 2,
            "Cores_per_socket": 12,
            "Sockets": 2,
            "Vendor_ID": "GenuineIntel",
            "Stepping": "4",
            "CPU_MHz": 1255.664,
            "CPU_Max_Speed_MHz": 3200.0000,
            "CPU_Min_Speed_MHz": 1200.0000,
            "BogoMIPS": 4788.43,
            "L2_cache": "256K",
            "L3_cache": "30720K",
            "NUMA_nodes": 2,
            "NUMA_node0_CPUs": "0-11,24-35",
            "NUMA_node1_CPUs": "12-23,36-47",
        }
        self.base_parser_cpu("tests/data/CPU_Intel.sample", CPU_OK)

    def test_parser_cpu_AMD(self):
        """
        Test the parser for an AMD CPU output.
        """
        CPU_OK = {
            "Architecture": "x86_64",
            "CPU_Model": "AMD EPYC 7742 64-Core Processor",
            "CPU_Family": "23",
            "CPU_num": 128,
            "Online_CPUs_list": "0-127",
            "Threads_per_core": 1,
            "Cores_per_socket": 64,
            "Sockets": 2,
            "Vendor_ID": "AuthenticAMD",
            "Stepping": "0",
            "CPU_MHz": 2245.758,
            "CPU_Max_Speed_MHz": -1,
            "CPU_Min_Speed_MHz": -1,
            "BogoMIPS": 4491.51,
            "L2_cache": "512K",
            "L3_cache": "16384K",
            "NUMA_nodes": 8,
            "NUMA_node0_CPUs": "0-15",
            "NUMA_node1_CPUs": "16-31",
            "NUMA_node2_CPUs": "32-47",
            "NUMA_node3_CPUs": "48-63",
            "NUMA_node4_CPUs": "64-79",
            "NUMA_node5_CPUs": "80-95",
            "NUMA_node6_CPUs": "96-111",
            "NUMA_node7_CPUs": "112-127",
        }
        self.base_parser_cpu("tests/data/CPU_AMD.sample", CPU_OK)

    def test_parser_cpu_ARM(self):
        """
        Test the parser for an AMD CPU output.
        """
        CPU_OK = {
            "Architecture": "aarch64",
            "CPU_Model": "Neoverse-N1 - Ampere(R) Altra(R) Processor",
            "CPU_Family": "not_available",
            "CPU_num": 160,
            "Online_CPUs_list": "0-159",
            "Threads_per_core": 1,
            "Cores_per_socket": 80,
            "Sockets": 2,
            "Vendor_ID": "ARM",
            "Stepping": "r3p1",
            "CPU_MHz": -1.0,
            "CPU_Max_Speed_MHz": 3000.0000,
            "CPU_Min_Speed_MHz":  1000.0000,
            "BogoMIPS": 50.00,
            "L2_cache": "160 MiB (160 instances)",
            "L3_cache": "not_available",
            "NUMA_nodes": 2,
            "NUMA_node0_CPUs": "0-79",
            "NUMA_node1_CPUs": "80-159",
        }
        self.base_parser_cpu("tests/data/CPU_ARM.sample", CPU_OK)

    def test_parser_memory(self):
        """
        Test the parser for a memory output.
        """

        hw = Extractor(extra={})

        with open("tests/data/MEM.sample", "r") as mem_file:
            mem_text = mem_file.read()

        mem_output = hw.get_mem_parser(mem_text)

        MEM_OK = {
            "dimm1": "8192 MB DDR3 | Nanya | NT8GC72C4NG0NL-CG",
            "dimm2": "8192 MB DDR3 | Nanya | NT8GC72C4NG0NL-CG",
            "dimm3": "8192 MB DDR3 | Nanya | NT8GC72C4NG0NL-CG",
            "dimm4": "8192 MB DDR3 | Nanya | NT8GC72C4NG0NL-CG",
            "dimm5": "8192 MB DDR3 | Nanya | NT8GC72C4NG0NL-CG",
            "dimm6": "8192 MB DDR3 | Nanya | NT8GC72C4NG0NL-CG",
            "dimm7": "8192 MB DDR3 | Nanya | NT8GC72C4NG0NL-CG",
            "dimm8": "8192 MB DDR3 | Nanya | NT8GC72C4NG0NL-CG",
        }

        self.assertEqual(mem_output, MEM_OK, "Memory parser mismatch!")

    def test_parser_memory__shouldnt_match_substrings(self):
        """
        Test the parser for a memory output where the output contains
        attributes of a similar name as a part of others, which
        should not be selected.

        E.g. The value of the `Size` attribute should not be extracted from the
        following line: `	Cache Size: None`.
        """
        hw = Extractor(extra={})

        with open("tests/data/MEM.sample.2", "r") as mem_file:
            mem_text = mem_file.read()

        mem_output = hw.get_mem_parser(mem_text)

        MEM_OK = {
            "dimm1": "16384 MB DDR4 | SK Hynix | HMA82GR7DJR8N-XN",
            "dimm2": "16384 MB DDR4 | SK Hynix | HMA82GR7DJR8N-XN",
            "dimm3": "16384 MB DDR4 | SK Hynix | HMA82GR7DJR8N-XN",
            "dimm4": "16384 MB DDR4 | SK Hynix | HMA82GR7DJR8N-XN",
            "dimm5": "16384 MB DDR4 | SK Hynix | HMA82GR7DJR8N-XN",
            "dimm6": "16384 MB DDR4 | SK Hynix | HMA82GR7DJR8N-XN",
            "dimm7": "16384 MB DDR4 | SK Hynix | HMA82GR7DJR8N-XN",
            "dimm8": "16384 MB DDR4 | SK Hynix | HMA82GR7DJR8N-XN",
            "dimm9": "16384 MB DDR4 | SK Hynix | HMA82GR7DJR8N-XN",
            "dimm10": "16384 MB DDR4 | SK Hynix | HMA82GR7DJR8N-XN",
            "dimm11": "16384 MB DDR4 | SK Hynix | HMA82GR7DJR8N-XN",
            "dimm12": "16384 MB DDR4 | SK Hynix | HMA82GR7DJR8N-XN",
            "dimm13": "16384 MB DDR4 | SK Hynix | HMA82GR7DJR8N-XN",
            "dimm14": "16384 MB DDR4 | SK Hynix | HMA82GR7DJR8N-XN",
            "dimm15": "16384 MB DDR4 | SK Hynix | HMA82GR7DJR8N-XN",
            "dimm16": "16384 MB DDR4 | SK Hynix | HMA82GR7DJR8N-XN",
        }

        self.assertEqual(mem_output, MEM_OK, "Memory parser mismatch!")

    def test_parser_storage(self):
        """
        Test the parser for a storage output.
        """

        hw = Extractor(extra={})

        with open("tests/data/STORAGE.sample", "r") as storage_file:
            storage_text = storage_file.read()

        storage_output = hw.get_storage_parser(storage_text)

        STORAGE_OK = {
            "disk1": "/dev/sda | INTEL SSDSC2CW24 | 223GiB (240GB)",
            "disk2": "/dev/sdb | INTEL SSDSC2CW24 | 223GiB (240GB)",
            "disk3": "/dev/sdc | INTEL SSDSC2CW24 | 223GiB (240GB)",
        }

        self.assertEqual(storage_output, STORAGE_OK, "Storage parser mismatch!")

    def test_full_metadata(self):
        """
        Test the metadata schema
        """
        # Collect data
        hw = Extractor(extra={'mode': 'docker'})
        hw.collect()

        # Print the output to stdout and save metadata to json file
        TMP_FILE = Path("metadata.tmp")
        hw.dump(stdout=True, outfile=TMP_FILE)

        # Define Hardware metadata schema
        metadata_schema = Schema(And(Use(json.loads),
                                {
                                 "HW": { "BIOS"   : { str : str },
                                         "SYSTEM" : {  str   : str,
                                                      "isVM" : bool,
                                                    },
                                         "MEMORY" : { "Mem_Available" : int,
                                                      "Mem_Total"     : int,
                                                      "Mem_Swap"      : int,
                                                    },
                                         "STORAGE": { Optional(str) : Optional(str) },
                                         "CPU"    : { str : str,
                                                      "SMT_Enabled"      : str,
                                                      "CPU_num"          : int,
                                                      "Threads_per_core" : int,
                                                      "Cores_per_socket" : int,
                                                      "Sockets"          : int,
                                                      "BogoMIPS"         : float,
                                                      "CPU_MHz"          : float,
                                                      "CPU_Max_Speed_MHz": Or(int, float),
                                                      "CPU_Min_Speed_MHz": Or(int, float),
                                                      "NUMA_nodes"       : int,
                                                      "Stepping"         : str,
                                                    }
                                 },
                                 "SW" : { str : str },
                                 "Hostname" : str,
                                }))

        # Validate schema from extractor
        with open(TMP_FILE, "r") as fin:
            metadata_schema.validate(fin.read())

        # Cleanup tmp file
        if TMP_FILE.exists():
            TMP_FILE.unlink()


if __name__ == "__main__":
    unittest.main(verbosity=2)
