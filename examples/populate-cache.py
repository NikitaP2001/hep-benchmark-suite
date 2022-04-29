#!/usr/bin/env python3
"""Helper script to pre-pull benchmark images.

This script will pull benchmark images (singularity or docker) based on 
the contents of a config file for the HEP benchmark suite, or HEPscore.

Example:

    $ ./populate-cache.py my_custom_suite_conf.yaml
    
Attributes:
    pull_exec (str): executive to pull with (default singularity)
    hs06_image (str): SPEC container image, if found
    hsconfig_file (str): Path to hepscore config file, if local
    hs_images (dict): dict of {image:tag} for container images to pull

Args:
    config.yml (str, optional) A config yaml for the suite or HEPscore
"""


from pathlib import Path
import requests
import sys
from yaml import safe_load, dump

# Singularity is default for suite, will override if defined in suite config
pull_exec = "singularity"
hs06_image = False
hsconfig_file = False
hs_images = dict()
uri = {"singularity":"oras://", "docker":"https://"}

# use conf given, or get default one according to version
if len(sys.argv) > 1:
    configfile = Path(sys.argv[1])
else:
    # temporarily block local/relative imports
    syspath = sys.path
    sys.path = syspath[1:]
    try:
        import hepbenchmarksuite
        configfile = Path(hepbenchmarksuite.__path__[0])/'config'/'benchmarks.yml'
        sys.path = syspath
    except:
        print("[ERROR] HEP Benchmark Suite not found. Please install via pip, or provide a config.yaml as argument.")
        exit(1)

with configfile.open() as stream:
        config = safe_load(stream)

# if the config is for the suite, set the pull exec, and find the hepscore config to use
if 'global' in config:
    pull_exec = config['global']['mode']
    if 'hepspec06' in config: hs06_image = config['hepspec06']['image'].split('//')[1]
    if 'hepscore' in config:
        # try and use the config already present if installed, otherwise get from remote
        hsconfig_file = config['hepscore']['config']
        if hsconfig_file == "default":
            hs_remote_conf="hepscore-default.yaml"
            URL=f"https://gitlab.cern.ch/hep-benchmarks/hep-score/-/raw/{config['hepscore']['version']}/hepscore/etc/"
            hs_remote_conf = requests.get(URL+hs_remote_conf).text
            hs_config_text = requests.get(URL+hs_remote_conf).text
        else:
            with open(hsconfig_file) as stream:
                hs_config_text = stream.readlines()
        # we're done with HEP benchmark suite config now, parse HEPscore next
        config = safe_load(hs_config_text)['hepscore_benchmark']

# Parse hepscore images to pull
for bmk, conf in config['benchmarks'].items():
    if bmk.startswith('.'):
        print(f"Skipping commented benchmark {bmk}")
        continue
    hs_images[bmk] = conf['version']
registry = config['settings']['registry'].split('//')[1]

print(hs_images)
print(hs06_image)
print(registry)

# reminder
print("Please remember to `export SINGULARITY_CACHEDIR=/some/dir` to a shared location before running!")