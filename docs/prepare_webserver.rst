Preparing your webserver 
========================

Before you can install django and the localcosmos_server package, you have to install the requirements below. All code examples are for Debian/Ubuntu based systems.


1. Required server components
-----------------------------

* nginx or apache2 web server
* python3 and python3-dev
* virtualenv (optional, recommended)
* PostgreSQL 10.x with PostGIS 2.x
* kmeans PostgreSQL extension: https://github.com/umitanuki/kmeans-postgresql

On Debian/ubuntu, you can install the required packages as follows:
	.. code-block:: bash

		sudo apt-get install nginx
		sudo apt-get install python3 python3-dev
		sudo apt-get install virtualenv
		sudo apt-get install postgresql-10 postgresql-10-postgis-2.4 libpq-dev postgresql-server-dev-10


2. Create Postgres database
---------------------------
If not yet done, create a postgres database. If your desired database name is ``localcomsos``, you can create the database as follows:

	.. code-block:: bash

		sudo -u postgres -i
		psql
		# create new database by the name localcosmos
		create database localcosmos;

You also have to create a database user which has the right to alter the just created ``localcosmos`` database. In this example the user is named ``lcuser``, but you can use any other name. You have to replace ``<lcpassword>`` with your desired password.

	.. code-block:: bash
		
		create user lcuser;
		alter role lcuser SUPERUSER;
		alter user lcuser PASSWORD '<lcpassword>';
		\q
	

Install the kmeans PostgreSQL extension
---------------------------------------

1. Switch back to your server user
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This step only applies if you follow this tutorial step by step. Switch back from the postgres user to the user you use on your server. Replace ``<serveruser>`` with the username you use on your server.
 
	.. code-block:: bash

		su <serveruser>


2. Download kmeans
^^^^^^^^^^^^^^^^^^
Download and unzip https://github.com/umitanuki/kmeans-postgresql on your server. In this example, kmeans is downloaded into ``/opt/kmeans``, but you can use any other folder.

	.. code-block:: bash

		sudo mkdir /opt/kmeans
		cd /opt/kmeans
		sudo chown <serveruser>:<serveruser> /opt/kmeans
		wget https://github.com/umitanuki/kmeans-postgresql/archive/master.zip
		# install unzip
		sudo apt-get install unzip
		unzip master.zip


3. Activate kmeans extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In this example, the database which we want to install the kmeans extension for, is named ``localcosmos``. Replace ``localcosmos`` if your database has a different name.

	.. code-block:: bash

		cd /opt/kmeans/kmeans-postgresql-master
		# if not yet done, install build requirements
		sudo apt-get install make gcc
		# make and make install kmeans
		make
		sudo make install
		# switch to the postgres user
		sudo -u postgres -i
		# activate the kmeans extension for the database localcosmos, replace the db name if necessary
		psql -f /usr/share/postgresql/10/extension/kmeans.sql -d localcomos
		exit


