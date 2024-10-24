FROM gitlab-registry.cern.ch/linuxsupport/cc7-base:latest

COPY requirements.txt /opt/hep-benchmark-suite/requirements.txt
COPY tests/ /opt/hep-benchmark-suite/
COPY hepbenchmarksuite/plugins/ /opt/hep-benchmark-suite/

RUN yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

RUN if [ ! -s /etc/yum.repos.d/docker-ce.repo ]; then echo "Error retrieving docker-ce.repo"; exit 1; fi

RUN yum install -y docker-ce https://linuxsoft.cern.ch/wlcg/centos7/x86_64/wlcg-repo-1.0.0-1.el7.noarch.rpm \
    util-linux  wget git \
    screen  tar freetype jq unzip \
    yum-plugin-ovl python-pip \
    skopeo bats \
    openssl-devel libffi-devel bzip2-devel \
    epel openssl11-devel \
    && yum clean all
#workaround https://github.com/CentOS/sig-cloud-instance-images/issues/15

RUN curl -L "https://github.com/docker/compose/releases/download/1.28.6/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
RUN chmod +x /usr/local/bin/docker-compose
RUN docker-compose --version

# Install Python3.10
RUN yum groupinstall "Development Tools" -y
RUN wget https://www.python.org/ftp/python/3.10.4/Python-3.10.4.tgz
RUN tar xf Python-3.10.4.tgz
WORKDIR /Python-3.10.4
RUN sed -i 's/PKG_CONFIG openssl /PKG_CONFIG openssl11 /g' configure
RUN ./configure --enable-optimizations
RUN make install
RUN ln -sf `which python3.10` `which python`
WORKDIR /

RUN python -m pip install --upgrade pip
# Required to install pyyaml
RUN python -m pip install pathlib dictdiffer
RUN python -m pip install -r /opt/hep-benchmark-suite/requirements.txt
