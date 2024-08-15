FROM gitlab-registry.cern.ch/linuxsupport/alma9-base:latest

RUN dnf install -y yum-utils
RUN yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

RUN if [ ! -s /etc/yum.repos.d/docker-ce.repo ]; then echo "Error retrieving docker-ce.repo"; exit 1; fi

RUN dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin \
    wget git tar jq unzip epel-release
