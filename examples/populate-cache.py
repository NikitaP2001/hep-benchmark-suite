#!/usr/bin/env python3
"""Helper script to pre-pull benchmark images.

This script will pull benchmark images (singularity or docker) based on 
the contents of a config file for the HEP benchmark suite, or HEPscore.

Unless specified, architecture pulled will be the result of $(uname -m)

Example:

    $ ./populate-cache.py my_custom_suite_conf.yaml
    $ ./populate-cache.py tmp/hepscore23.yaml aarch64
    
Attributes:
    PULL_EXEC (str): executive to pull with defined in config (default singularity)
    HS06_IMAGE (str): SPEC container image, if found
    HSCONFIG_FILE (str): Path to hepscore config file, if local
    hs_images (dict): dict of {image:tag} for container images to pull

Args:
    config.yml (str, optional) A config yaml for the suite or HEPscore, 
                        if not specified, defaults to current installed HEPscore
    arch (str, optional) Architecture to pull, defaults to $(uname -m)
"""

import argparse
from os import getenv
from pathlib import Path
from platform import machine
from urllib.request import urlopen
from subprocess import run
import sys
from yaml import safe_load

# Singularity is default for suite, will override if defined in suite config
PULL_EXEC = "singularity"
HS06_IMAGE = False
HSCONFIG_FILE = False
hs_images = {}
SCACHE = getenv("SINGULARITY_CACHEDIR", default=None)
if not SCACHE:
    SCACHE = getenv("APPTAINER_CACHEDIR", default=None)


parser = argparse.ArgumentParser(
    description="Helper script to pre-pull benchmark images."
)
parser.add_argument(
    "configfile", nargs="?", default=None, help="config file (path-like)"
)
parser.add_argument("arch", nargs="?", default=machine(), help="architecture to pull")
args = parser.parse_args()


# use conf given, or get default one according to version
if args.configfile:
    configfile = Path(args.configfile).resolve()
    print(f"Using specified config '{args.configfile}'")
else:
    # temporarily block local/relative imports
    syspath = sys.path
    sys.path = syspath[1:]
    try:
        import hepbenchmarksuite

        configfile = Path(hepbenchmarksuite.__path__[0]) / "config" / "benchmarks.yml"
        sys.path = syspath
        print(f"Using default config '{configfile.resolve()}'")
    except ImportError:
        print(
            "[ERROR] HEP Benchmark Suite not found. \
            Please install via pip, or provide a config.yaml as argument."
        )
        sys.exit(1)

with configfile.open(encoding="utf-8") as stream:
    config = safe_load(stream)

# if the config is for the suite, set the pull exec, and find the hepscore config to use
if "global" in config:
    PULL_EXEC = config["global"]["mode"]
    if "hepspec06" in config:
        print(
            "'hepspec06' configuration key has been deprecated; please replace it by 'hs06'"
        )
        config["hs06"] = config["hepspec06"]
    if "hs06" in config:
        HS06_IMAGE = config["hs06"]["image"].split("//")[1]
    if "hepscore" in config:
        # try and use the config already present if installed, otherwise get from remote
        HSCONFIG_FILE = config["hepscore"]["config"]
        if HSCONFIG_FILE == "default":
            print("pulling from remote")
            HS_REMOTE_CONF = "hepscore-default.yaml"
            URL = f"https://gitlab.cern.ch/hep-benchmarks/hep-score/-/raw/\
            {config['hepscore']['version']}/hepscore/etc/"
            with urlopen(URL + HS_REMOTE_CONF) as remote:
                hs_remote_version = remote.read().decode()
            with urlopen(URL + hs_remote_version) as remote:
                hs_config_text = remote.read().decode()
        else:
            with open(HSCONFIG_FILE, encoding="utf-8") as stream:
                hs_config_text = stream.readlines()
        print(hs_config_text)
        # we're done with HEP benchmark suite config now, parse HEPscore next
        config = safe_load(hs_config_text)

if "hepscore_benchmark" in config:
    config = config["hepscore_benchmark"]
elif "hepscore" in config:
    config = config["hepscore"]
else:
    print(config)
    print(
        "Error parsing hepscore config. Could not find key 'hepscore' or 'hepscore_benchmark'"
    )
    print(
        "Please report this error to https://gitlab.cern.ch/hep-benchmarks/user-support"
    )
    exit(1)

# Parse hepscore images to pull
for bmk, conf in config["benchmarks"].items():
    if bmk.startswith("."):
        print(f"Skipping commented benchmark {bmk}")
        continue
    hs_images[bmk] = conf["version"]
registry = config["settings"]["registry"] + "/"

print()
print(
    f"This script will pull the following images for \
    {args.arch} via {PULL_EXEC} {'to '+SCACHE if SCACHE else ''}"
)
for image, tag in hs_images.items():
    print(f"{image}:{tag}")
print()
if not SCACHE and PULL_EXEC in ("singularity", "apptainer"):
    print(
        "!WARNING! 'SINGULARITY_CACHEDIR' or 'APPTAINER_CACHEDIR' is not defined! \
        Images will be downloaded to $HOME/.singularity"
    )
response = input("Are you SURE you want to continue? [y/n]: ").lower().strip()
if response[:1] != "y":
    sys.exit(1)


if PULL_EXEC == "singularity" or PULL_EXEC == "apptainer":
    Path("hep-workloads-sif").resolve().mkdir(exist_ok=True)
    for image, tag in hs_images.items():
        print(f"Pulling {image}:{tag}")
        run(
            [
                PULL_EXEC,
                "pull",
                "--dir",
                "hep-workloads-sif",
                image + ":" + tag,
                registry + image + ":" + tag + "_" + args.arch,
            ],
            check=True,
        )
    print(f"Images cached in {SCACHE}/cache.")
    print(
        "SIF image files composed in 'hep-workloads-sif/'. \
        You may use this directory with singularity 'dir://' paths."
    )
else:
    for image, tag in hs_images.items():
        print(f"Pulling {image}:{tag}")
        run([PULL_EXEC, "pull", registry + image + ":" + tag], check=True)
    print("Docker images pulled to local cache.")
