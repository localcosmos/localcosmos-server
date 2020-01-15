############################################################
# Dockerfile to create a base LocalCosmos container
# - based on ubuntu 18.04
# - python3.6, postgresql and nginx webserver
############################################################

# Set the base image to Ubuntu
FROM ubuntu:18.04
ENV UBUNTU_NAME=bionic

# File Author / Maintainer
MAINTAINER Thomas Uher <thomas.uher@sisol-systems.com>


ENV PYTHONIOENCODING=utf-8


# Install basic applications and perform cleanup
RUN apt-get update &&\
    apt-get install --no-install-recommends -y python3 python-3-dev &&\
    apt-get install --no-install-recommends -y virtualenv &&\
    apt-get install --no-install-recommends -y postgresql-10 postgresql-10-postgis-2.4 libpq-dev postgresql-server-dev-10 &&\
    apt-get clean autoclean &&\
    apt-get autoremove -y &&\
    rm -rf /var/lib/{apt,dpkg,cache,log}/


COPY install_nginx.sh /tmp

# Install and configure the nginx webserver
WORKDIR /tmp
RUN chmod +x install_nginx.sh &&\
    bash install_nginx.sh &&\
    rm install_nginx.sh &&\
    apt-get clean autoclean &&\
    apt-get autoremove -y &&\
    rm -rf /var/lib/{apt,dpkg,cache,log}/
