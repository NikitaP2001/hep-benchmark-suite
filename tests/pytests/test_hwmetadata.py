#!/usr/bin/env python3
"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""

import json
import os
import unittest
from unittest.mock import patch
from pathlib import Path
from hepbenchmarksuite.plugins.extractor import Extractor
from schema import Schema, And, Use, Optional, Or


class TestHWExtractor(unittest.TestCase):
    """********************************************************
                 *** HEP-BENCHMARK-SUITE ***

     Testing the extraction of Hardware Metadata.

    *********************************************************"""

    maxDiff = None

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
        # Make test pass on real nodes
        if result != "not_available":
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

        # The BIOS Model name will only be checked with root access
        cpu_model = "Neoverse-N1"
        if os.geteuid() == 0:
            cpu_model += " - Ampere(R) Altra(R) Processor"

        CPU_OK = {
            "Architecture": "aarch64",
            "CPU_Model": cpu_model,
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
            "CPU_Min_Speed_MHz": 1000.0000,
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

    def base_parser_storage(self, input_to_parse, expected_output, lsblk):
        hw = Extractor(extra={})

        with open(input_to_parse, "r") as storage_file:
            storage_text = storage_file.read()

        if lsblk:
            storage_output = hw.get_storage_parser_lsblk(storage_text)
        else:
            storage_output = hw.get_storage_parser(storage_text)

        self.assertEqual(storage_output, expected_output, "Storage parser mismatch!")

    def test_parser_storage(self):
        """
        Test the parser for a storage output.
        """

        STORAGE_OK = {
            "disk1": "/dev/sda | INTEL SSDSC2CW24 | 223GiB (240GB)",
            "disk2": "/dev/sdb | INTEL SSDSC2CW24 | 223GiB (240GB)",
            "disk3": "/dev/sdc | INTEL SSDSC2CW24 | 223GiB (240GB)",
        }

        self.base_parser_storage("tests/data/STORAGE.sample", STORAGE_OK, False)

    def test_parser_storage_missing_values(self):
        """
        Test the parser for a storage output with several missing values
        """
        STORAGE_OK = {
            "disk1": "/dev/ng0n1 | n/a | n/a",
            "disk2": "/dev/nvme0n1 | n/a | 1788GiB (1920GB)",
            "disk3": "/dev/ng1n1 | n/a | n/a",
            "disk4": "/dev/nvme1n1 | n/a | 1788GiB (1920GB)",
        }

        self.base_parser_storage("tests/data/STORAGE.sample.2", STORAGE_OK, False)

    def test_parser_storage_one_disk(self):
        """
        Test the parser for a storage output with one disk
        """

        STORAGE_OK = {
            "disk1": "/dev/sda | Samsung SSD 840 | 111GiB (120GB)"
        }

        self.base_parser_storage("tests/data/STORAGE.sample.3", STORAGE_OK, False)

    def test_parser_storage_missing_value(self):
        """
        Test the parser for a storage output with missing product name
        """

        STORAGE_OK = {
            "disk1": "/dev/vda | n/a | 100GiB (107GB)"
        }

        self.base_parser_storage("tests/data/STORAGE.sample.4", STORAGE_OK, False)

    def test_parser_storage_missing_size(self):
        """
        Test the parser for a storage output with missing size
        """

        STORAGE_OK = {
            "disk1": "/dev/sda | PERC 6/i | 931GiB (999GB)",
            "disk2": "/dev/sdc | PERC 6/i | 931GiB (999GB)",
            "disk3": "/dev/sdd | PERC 6/i | 931GiB (999GB)",
            "disk4": "/dev/cdrom | DVD-ROM DV28SV | n/a",
        }

        self.base_parser_storage("tests/data/STORAGE.sample.5", STORAGE_OK, False)

    def test_parser_storage_seven_disks(self):
        """
        Test the parser for a storage output with seven disks
        """

        STORAGE_OK = {
            "disk1": "/dev/sda | PERC H710 | 232GiB (249GB)",
            "disk2": "/dev/sdb | PERC H710 | 232GiB (249GB)",
            "disk3": "/dev/sdc | PERC H710 | 232GiB (249GB)",
            "disk4": "/dev/sdd | PERC H710 | 232GiB (249GB)",
            "disk5": "/dev/sde | PERC H710 | 232GiB (249GB)",
            "disk6": "/dev/sdf | PERC H710 | 232GiB (249GB)",
            "disk7": "/dev/sdg | PERC H710 | 232GiB (249GB)",
        }

        self.base_parser_storage("tests/data/STORAGE.sample.6", STORAGE_OK, False)

    def test_parser_storage_two_disks(self):
        """
        Test the parser for a storage output with two disks"
        """

        STORAGE_OK = {
            "disk1": "/dev/sda | INTEL SSDSC2BX20 | 186GiB (200GB)",
            "disk2": "/dev/sdb | INTEL SSDSC2BX01 | 1490GiB (1600GB)",
        }

        self.base_parser_storage("tests/data/STORAGE.sample.7", STORAGE_OK, False)

    def test_parser_storage_lsblk(self):
        """
        Test the parser for a storage output using lsblk
        """

        STORAGE_OK = {
            "disk1": "/dev/sda | ATA Samsung SSD 850 (scsi) | 120GB",
            "disk2": "/dev/vda | Virtio Block Device (virtblk) | 107GB",
        }

        self.base_parser_storage("tests/data/STORAGE.sample.8", STORAGE_OK, True)

    def test_parser_storage_one_disk_lsblk(self):
        """
        Test the parser for a storage output with one disk using lsblk
        """

        STORAGE_OK = {
            "disk1": "/dev/sda | ATA Samsung SSD 840 (scsi) | 120GB"
        }

        self.base_parser_storage("tests/data/STORAGE.sample.9", STORAGE_OK, True)

    def test_parser_storage_two_disks_lsblk(self):
        """
        Test the parser for a storage output with two disks using lsblk
        """
        STORAGE_OK = {
            "disk1": "/dev/sda | ATA INTEL SSDSC2BX20 (scsi) | 200GB",
            "disk2": "/dev/sdb | ATA INTEL SSDSC2BX01 (scsi) | 1600GB",
        }

        self.base_parser_storage("tests/data/STORAGE.sample.10", STORAGE_OK, True)

    def test_parser_storage_three_disks_lsblk(self):
        """
        Test the parser for a storage output with three disks using lsblk
        """

        STORAGE_OK = {
            "disk1": "/dev/sda | DELL PERC 6/i (scsi) | 1000GB",
            "disk2": "/dev/sdc | DELL PERC 6/i (scsi) | 1000GB",
            "disk3": "/dev/sdd | DELL PERC 6/i (scsi) | 1000GB",
        }

        self.base_parser_storage("tests/data/STORAGE.sample.11", STORAGE_OK, True)

    def test_parser_storage_error_message_lsblk(self):
        """
        Test the parser for a storage output with an error message present using lsblk
        """

        STORAGE_OK = {
            "disk1": "/dev/sda | DELL PERC 6/E Adapter (scsi) | 1000GB",
            "disk2": "/dev/sdb | Dell VIRTUAL DISK (scsi) | 299GB",
        }

        self.base_parser_storage("tests/data/STORAGE.sample.12", STORAGE_OK, True)

    @patch("hepbenchmarksuite.plugins.extractor.Extractor.exec_cmd")
    def test_collect_gpu(self, mock_exec_cmd):
        """
        Test the collect_gpu method
        """
        # Collect no rocm-smi or nvidia-smi
        hw = Extractor(extra={})
        result = hw.collect_gpu()

        self.assertEqual(result, {})
        # case nvidia-smi
        hw.pkg = {"nvidia-smi": True, "rocm-smi": False}

        # case wrong return of fields for a GPU
        with open("tests/data/nvidia-smi_7fields.sample", "r") as smi_file:
            mock_exec_cmd.return_value = smi_file.read()
        result = hw.collect_gpu()

        nvresult = {
            "nvidia0": {
                "name": "NVIDIA H100 PCIe",
                "memory_total": "81559 MiB",
                "memory_used": "4 MiB",
                "clock_graphics": "345 MHz",
                "clock_sm": "345 MHz",
                "pci_bus": "00000000:19:00.0",
                "power_avg": "28.9 W",
            },
            "nvidia2": {
                "name": "NVIDIA H100 PCIe",
                "memory_total": "81559 MiB",
                "memory_used": "4 MiB",
                "clock_graphics": "345 MHz",
                "clock_sm": "345 MHz",
                "pci_bus": "00000000:33:00.0",
                "power_avg": "28.9 W",
            },
            "nvidia3": {
                "name": "NVIDIA H100 PCIe",
                "memory_total": "81559 MiB",
                "memory_used": "4 MiB",
                "clock_graphics": "345 MHz",
                "clock_sm": "345 MHz",
                "pci_bus": "00000000:34:00.0",
                "power_avg": "28.9 W",
            },
        }
        self.assertEqual(result, nvresult)
    
        with open("tests/data/nvidia-smi.sample", "r") as smi_file:
           mock_exec_cmd.return_value = smi_file.read()
        result = hw.collect_gpu()

        nvresult = {
            "nvidia0": {
                "name": "NVIDIA H100 PCIe",
                "memory_total": "81559 MiB",
                "memory_used": "4 MiB",
                "clock_graphics": "345 MHz",
                "clock_sm": "345 MHz",
                "pci_bus": "00000000:19:00.0",
                "power_avg": "28.9 W",
            },
            "nvidia1": {
                "name": "NVIDIA H100 PCIe",
                "memory_total": "81559 MiB",
                "memory_used": "4 MiB",
                "clock_graphics": "345 MHz",
                "clock_sm": "345 MHz",
                "pci_bus": "00000000:1A:00.0",
                "power_avg": "28.9 W",
            },
            "nvidia2": {
                "name": "NVIDIA H100 PCIe",
                "memory_total": "81559 MiB",
                "memory_used": "4 MiB",
                "clock_graphics": "345 MHz",
                "clock_sm": "345 MHz",
                "pci_bus": "00000000:33:00.0",
                "power_avg": "28.9 W",
            },
            "nvidia3": {
                "name": "NVIDIA H100 PCIe",
                "memory_total": "81559 MiB",
                "memory_used": "4 MiB",
                "clock_graphics": "345 MHz",
                "clock_sm": "345 MHz",
                "pci_bus": "00000000:34:00.0",
                "power_avg": "28.9 W",
            },
        }
        self.assertEqual(result, nvresult)
        # case rocm-smi
        hw.pkg = {"nvidia-smi": False, "rocm-smi": True}
        with open("tests/data/rocm-smi.json", "r") as smi_file:
            mock_exec_cmd.return_value = smi_file.read()

        result = hw.collect_gpu()

        rocm_result = {
            "card0": {
                "name": "0x0b0c SKU: D65201",
                "memory_total": "65520 MiB",
                "memory_used": "11 MiB",
                "clock_graphics": "800Mhz",
                "clock_sm": "1090Mhz",
                "pci_bus": "0000:D1:00.0",
                "power_avg": "85.0 W",
            },
            "card1": {
                "name": "0x0b0c SKU: D65201",
                "memory_total": "65520 MiB",
                "memory_used": "11 MiB",
                "clock_graphics": "800Mhz",
                "clock_sm": "1090Mhz",
                "pci_bus": "0000:D8:00.0",
                "power_avg": "90.0 W",
            },
        }
        self.assertEqual(result, rocm_result)

    def test_collect_gpu_fail_smi_call(self):
        """
        Test the collect_gpu method
        """
        # Collect no rocm-smi or nvidia-smi
        hw = Extractor(extra={})
        # see [BMK-1616]
        hw.pkg = {"nvidia-smi": True, "rocm-smi": False}
        result = hw.collect_gpu()
        self.assertEqual(result, {})

        hw.pkg = {"nvidia-smi": False, "rocm-smi": True}
        result = hw.collect_gpu()
        self.assertEqual(result, {})


    def test_full_metadata(self):
        """
        Test the metadata schema
        """
        # Collect data
        hw = Extractor(extra={"mode": "docker"})
        hw.collect()

        # Print the output to stdout and save metadata to json file
        TMP_FILE = Path("metadata.tmp")
        hw.dump(stdout=True, outfile=TMP_FILE)

        # Define Hardware metadata schema
        metadata_schema = Schema(
            And(
                Use(json.loads),
                {
                    "HW": {
                        "BIOS": {str: str},
                        "SYSTEM": {
                            str: str,
                            "isVM": bool,
                        },
                        "MEMORY": {
                            "Mem_Available": int,
                            "Mem_Total": int,
                            "Mem_Swap": int,
                            Optional("dimm1"): str,
                        },
                        "STORAGE": {Optional(str): Optional(str)},
                        "CPU": {
                            str: str,
                            "SMT_Enabled": str,
                            "CPU_num": int,
                            "Threads_per_core": int,
                            "Cores_per_socket": int,
                            "Sockets": int,
                            "BogoMIPS": float,
                            "CPU_MHz": float,
                            "CPU_Max_Speed_MHz": Or(int, float),
                            "CPU_Min_Speed_MHz": Or(int, float),
                            "NUMA_nodes": int,
                            "Stepping": str,
                        },
                        "GPU": Or(
                            {},  # empty dict (no GPUs)
                            {
                                str: {  # dict of gpus by address
                                    "name": str,
                                    "memory_total": str,
                                    "memory_used": str,
                                    "clock_graphics": str,
                                    "clock_sm": str,
                                    "pci_bus": str,
                                    "power_avg": str,
                                }
                            },
                        ),
                    },
                    "SW": {
                        str: str,
                        "OS": {
                            str: str,
                            "version": {str: str},
                        },
                        "kernel": {str: str},
                    },
                    "Hostname": str,
                },
            )
        )

        # Validate schema from extractor
        with open(TMP_FILE, "r") as fin:
            metadata_schema.validate(fin.read())

        # Cleanup tmp file
        if TMP_FILE.exists():
            TMP_FILE.unlink()

class TestCheckIfVirtual(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Mock executor
        class MockExecutor:
            def run_command(self, cmd):
                with open(cmd.split(" ")[-1], "r") as f:
                    return f.read()

        cls.mock_executor = MockExecutor()
        cls.extractor = Extractor(cls.mock_executor)

        # Prepare mock test files
        cls.file_A = "A_non_existing_file"  # Non-existent file
        cls.file_B = "B.txt"  # File without hypervisor
        cls.file_C = "C.txt"  # File with hypervisor

        with open(cls.file_B, "w") as f:
            f.write("physical system.\n")

        with open(cls.file_C, "w") as f:
            f.write("This system has a hypervisor.\n")

    @classmethod
    def tearDownClass(cls):
        # Clean up test files
        if os.path.exists(cls.file_B):
            os.remove(cls.file_B)
        if os.path.exists(cls.file_C):
            os.remove(cls.file_C)

    def test_non_existent_file(self):
        cmd = f"grep hypervisor {self.file_A}"
        result = self.extractor.check_if_virtual(cmd=cmd)
        self.assertFalse(result, "File without hypervisor should return False.")

    def test_file_without_hypervisor(self):
        cmd = f"grep hypervisor {self.file_B}"
        result = self.extractor.check_if_virtual(cmd=cmd)
        self.assertFalse(result, "File without hypervisor should return False.")

    def test_file_with_hypervisor(self):
        cmd = f"grep hypervisor {self.file_C}"
        result = self.extractor.check_if_virtual(cmd=cmd)
        self.assertTrue(result, "File with hypervisor should return True.")

    @patch.object(Extractor, "check_if_virtual")
    def test_check_if_virtual_mocked(self, mock_check_if_virtual):
        # Mock check_if_virtual behavior for a virtualized system
        mock_check_if_virtual.return_value = True
        result = self.extractor.check_if_virtual()
        self.assertTrue(result, "Mocked method with virtual system should return True.")

        # Mock check_if_virtual behavior for a non-virtualized system
        mock_check_if_virtual.return_value = False
        result = self.extractor.check_if_virtual()
        self.assertFalse(result, "Mocked method with non-virtual system should return False.")



if __name__ == "__main__":
    unittest.main(verbosity=2)
