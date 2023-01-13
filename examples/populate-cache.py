#!/usr/bin/env python3
"""Helper script to pre-pull benchmark images.

This script will pull benchmark images (singularity or docker) based on 
the contents of a config file for the HEP benchmark suite, or HEPscore.

Example:

    $ ./populate-cache.py my_custom_suite_conf.yaml
    
Attributes:
    pull_exec (str): executive to pull with defined in config (default singularity)
    hs06_image (str): SPEC container image, if found
    hsconfig_file (str): Path to hepscore config file, if local
    hs_images (dict): dict of {image:tag} for container images to pull

Args:
    config.yml (str, optional) A config yaml for the suite or HEPscore
"""

from os import getenv
from pathlib import Path
from urllib.request import urlopen
from subprocess import run
import sys
from yaml import safe_load

# Singularity is default for suite, will override if defined in suite config
pull_exec = "singularity"
hs06_image = False
hsconfig_file = False
hs_images = dict()
SCACHE=getenv("SINGULARITY_CACHEDIR", default=None)

# use conf given, or get default one according to version
if len(sys.argv) > 1:
    configfile = Path(sys.argv[1]).resolve()
    print(f"Using specified config '{configfile}'")
else:
    # temporarily block local/relative imports
    syspath = sys.path
    sys.path = syspath[1:]
    try:
        import hepbenchmarksuite
        configfile = Path(hepbenchmarksuite.__path__[0])/'config'/'benchmarks.yml'
        sys.path = syspath
        print(f"Using default config '{configfile.resolve()}'")
    except ImportError:
        print("[ERROR] HEP Benchmark Suite not found. Please install via pip, or provide a config.yaml as argument.")
        sys.exit(1)

with configfile.open(encoding="utf-8") as stream:
    config = safe_load(stream)

# if the config is for the suite, set the pull exec, and find the hepscore config to use
if 'global' in config:
    pull_exec = config['global']['mode']
    if 'hepspec06' in config:
        hs06_image = config['hepspec06']['image'].split('//')[1]
    if 'hepscore' in config:
        # try and use the config already present if installed, otherwise get from remote
        hsconfig_file = config['hepscore']['config']
        if hsconfig_file == "default":
            print("pulling from remote")
            HS_REMOTE_CONF="hepscore-default.yaml"
            URL=f"https://gitlab.cern.ch/hep-benchmarks/hep-score/-/raw/{config['hepscore']['version']}/hepscore/etc/"
            with urlopen(URL+HS_REMOTE_CONF) as remote:
                hs_remote_version = remote.read().decode()
            with urlopen(URL+hs_remote_version) as remote:
                hs_config_text = remote.read().decode()
        else:
            with open(hsconfig_file, encoding="utf-8") as stream:
                hs_config_text = stream.readlines()
        print(hs_config_text)
        # we're done with HEP benchmark suite config now, parse HEPscore next
        config = safe_load(hs_config_text)['hepscore_benchmark']

# Parse hepscore images to pull
for bmk, conf in config['benchmarks'].items():
    if bmk.startswith('.'):
        print(f"Skipping commented benchmark {bmk}")
        continue
    hs_images[bmk] = conf['version']
registry = config['settings']['registry']+"/"

print()
print(f"This script will pull the following images via {pull_exec} {'to '+SCACHE if SCACHE else ''}")
for image, tag in hs_images.items():
    print(f"{image}:{tag}")
print()
if not SCACHE and pull_exec == "singularity":
    print("[!WARNING! 'SINGULARITY_CACHEDIR' is not defined! Images will be downloaded to $HOME/.singularity")
response = input("Do you want to continue? [y/n]: ").lower().strip()
if response[:1] != 'y':
    sys.exit(1)

for image, tag in hs_images.items():
    print(f"Pulling {image}:{tag}")
    run([pull_exec, "pull", registry+image+":"+tag], check=True)
