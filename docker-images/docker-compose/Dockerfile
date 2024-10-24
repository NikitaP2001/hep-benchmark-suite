FROM gitlab-registry.cern.ch/linuxsupport/alma9-base:latest

COPY requirements.txt /opt/hep-benchmark-suite/requirements.txt
COPY tests/ /opt/hep-benchmark-suite/
COPY hepbenchmarksuite/plugins/ /opt/hep-benchmark-suite/

# epel-release needs to be installed before other packages, e.g. bats
RUN dnf install -y yum-utils epel-release

# Install docker and other deps
RUN yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
RUN if [ ! -s /etc/yum.repos.d/docker-ce.repo ]; then echo "Error retrieving docker-ce.repo"; exit 1; fi
RUN dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin \
    wget git tar jq unzip python3-pip bats

# Install and check docker-compose
RUN curl -L "https://github.com/docker/compose/releases/download/v2.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/bin/docker-compose
RUN chmod +x /usr/bin/docker-compose
RUN docker-compose --version

# Install python requirements and create alias
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN python3 -m pip install --upgrade pip
# Required to install pyyaml
RUN python3 -m pip install pathlib dictdiffer
RUN python3 -m pip install -r /opt/hep-benchmark-suite/requirements.txt
