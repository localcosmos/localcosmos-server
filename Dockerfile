FROM python:3.10

WORKDIR /opt/localcosmos

RUN apt-get update &&\
    apt-get install --no-install-recommends -y libgeos-dev libgdal-dev &&\
    apt-get clean autoclean &&\
    apt-get autoremove -y &&\
    rm -rf /var/lib/{apt,dpkg,cache,log}/

COPY localcosmos_server/requirements.txt /opt/localcosmos
RUN pip install -r /opt/localcosmos/requirements.txt

RUN django-admin startproject localcosmos_private

RUN ls /opt/localcosmos/localcosmos_private

CMD python manage.py runserver 0.0.0.0:8000