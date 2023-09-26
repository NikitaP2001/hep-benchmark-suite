FROM gitlab-registry.cern.ch/linuxsupport/cc7-base:latest

RUN yum install -y python3 util-linux  wget git \
    tar perl jq unzip \
    net-tools yum-plugin-ovl \
    && yum clean all

COPY requirements.txt .
RUN pip3 install -r requirements.txt 

