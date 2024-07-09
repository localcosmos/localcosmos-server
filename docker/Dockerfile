############################################################
# Dockerfile to create a LocalCosmos Server container
# - based on ubuntu 18.04
# - python3.6, postgresql and nginx webserver
# - django, uwsgi
############################################################

# Set the base image to Ubuntu
FROM ubuntu:20.04
ENV UBUNTU_NAME=focal

LABEL maintainer Thomas Uher <thomas.uher@sisol-systems.com>

ENV PYTHONUNBUFFERED 1

ARG DEBIAN_FRONTEND=noninteractive

# create the localcosmos directory
RUN mkdir /opt/localcosmos

# Install the nginx webserver, python3, postgis
RUN apt-get update &&\	
    apt-get install -y --no-install-recommends nginx gettext-base &&\
	apt-get install -y --no-install-recommends python3 python3-dev python3-pip python3-setuptools &&\
	apt-get install -y --no-install-recommends make gcc &&\
	apt-get install -y --no-install-recommends postgresql-12 postgresql-12-postgis-3 libpq-dev postgresql-server-dev-12 \
      postgresql-client-12 postgresql-contrib-12  postgresql-12-postgis-scripts &&\
	apt-get clean autoclean &&\
    apt-get autoremove -y &&\
	rm -rf /var/lib/{apt,dpkg,cache,log}/


RUN locale-gen en_US.UTF-8 &&\
	update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 LANGUAGE=en_US.UTF-8

ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8
ENV PYTHONIOENCODING=utf-8


# install kmeans
ADD ["kmeans-postgresql-master/", "/opt/kmeans-postgresql-master/"]
WORKDIR /opt/kmeans-postgresql-master
RUN make &&\
	make install


# install django, localcosmos_server
RUN pip3 install wheel &&\
    pip3 install django==4.2.* uwsgi &&\
    pip3 install localcosmos_server

# create the django project
WORKDIR /opt/localcosmos
RUN django-admin startproject localcosmos_private

COPY ["localcosmos_private/settings.py", "/opt/localcosmos/localcosmos_private/localcosmos_private/settings.py"]
COPY ["localcosmos_private/urls.py", "/opt/localcosmos/localcosmos_private/localcosmos_private/urls.py"]


# Copy the nginx configuration files, remove old configuration if any
RUN rm -f /etc/nginx/conf.d/* &&\
    mkdir -p /var/www/localcosmos/ &&\
    mkdir -p /var/log/uwsgi/


COPY ["nginx/localcosmos-server.conf.template", "/etc/nginx/conf.d/localcosmos-server.conf.template"]

COPY ["nginx/uwsgi_params", "/opt/localcosmos/uwsgi/uwsgi_params"]
COPY ["nginx/localcosmos-server-uwsgi.ini", "/opt/localcosmos/uwsgi/localcosmos-server-uwsgi.ini"]


# ENTRYPOINT
RUN mkdir /code
COPY ["wait-for-it.sh", "/code/wait-for-it.sh"]
COPY ["docker-entrypoint.sh", "/code/docker-entrypoint.sh"]

ENV MIGRATE=true

RUN chmod +x /code/docker-entrypoint.sh &&\
    chmod +x /code/wait-for-it.sh

ENTRYPOINT ["/code/docker-entrypoint.sh"]

