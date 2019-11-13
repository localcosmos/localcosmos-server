Preparing your webserver 
========================


Required server components
--------------------------

* a Linux server with root access
* nginx or apache2 web server
* python3
* virtualenv (optional, recommended)
* PostGis 2.x
* kmeans PostgreSQL extension: https://github.com/umitanuki/kmeans-postgresql


Install the kmeans PostgreSQL extension
---------------------------------------

1. Download and unzip https://github.com/umitanuki/kmeans-postgresql on your server.
2. make sure you have the development packages for you postgresql server package installed (e.g. sudo apt-get install libpq-dev postgresql-server-dev-10)

3. In your unzipped kmeans folder run the following (e.g. on ubuntu)

   .. code-block:: bash

      make
      sudo make install
      psql -f /usr/share/postgresql/10/extension/kmeans.sql -d YOURGEODJANGODATABASE

   The latter needs to be processed as a postgresql superuser, e.g. the user postgres.

