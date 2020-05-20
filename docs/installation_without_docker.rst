Installation without docker
===========================

Duration: 30-45 minutes.

This tutorial covers setting up a running LocalCosmos Private Server as a development server. This tutorial is intended for people not familiar with django. For more information about django visit https://www.djangoproject.com/ .

1. Prerequisites
-----------------

Before you can install django and the localcosmos_server package, you have to install the requirements below. All code examples are for Debian/Ubuntu based systems.


1.1 Required server components
------------------------------

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


1.2 Create Postgres database
----------------------------
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
	

1.3 Install the kmeans PostgreSQL extension
-------------------------------------------

1.3.1 Switch back to your server user
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This step only applies if you follow this tutorial step by step. Switch back from the postgres user to the user you use on your server. Replace ``<serveruser>`` with the username you use on your server.
 
	.. code-block:: bash

		su <serveruser>


1.3.2 Download kmeans
^^^^^^^^^^^^^^^^^^^^^
Download and unzip https://github.com/umitanuki/kmeans-postgresql on your server. In this example, kmeans is downloaded into ``/opt/kmeans``, but you can use any other folder.

	.. code-block:: bash

		sudo mkdir /opt/kmeans
		cd /opt/kmeans
		# replace <serveruser> with your username
		sudo chown <serveruser>:<serveruser> /opt/kmeans
		wget https://github.com/umitanuki/kmeans-postgresql/archive/master.zip
		# install unzip
		sudo apt-get install unzip
		unzip master.zip


1.3.3 Activate kmeans extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
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
		psql -f /usr/share/postgresql/10/extension/kmeans.sql -d localcosmos
		exit



2. Create a new django project
------------------------------

**Create a project folder**

Create a folder on your disk where your Local Cosmos Private Server can live. eg: ``/opt/localcosmos``.
Make sure you have permissions to write this folder. In the example the server user is ``<serveruser>`` - replace this with the username you use.


**Create a python3 virtual environment**

	.. code-block:: bash

		sudo mkdir /opt/localcosmos
		sudo chown <serveruser>:<serveruser> /opt/localcosmos
		cd /opt/localcosmos
		virtualenv -p python3 venv


**Activate the virtual environment**

   .. code-block:: bash

      source venv/bin/activate


**Install django and localcosmos_server**

   .. code-block:: bash

      pip install django==2.2.*
      pip install localcosmos_server

This will install django, localcosmos_server and its requirements in your created and activated virtualenv. 


**Create a new django project**

In ``/opt/localcosmos`` execute the following:

   .. code-block:: bash

      django-admin startproject localcosmos_private


This will automatically create the folder ``/opt/localcosmos/localcosmos_private``, which contains your newly created django project.


3. Configure your django project
--------------------------------

3.1 settings.py
^^^^^^^^^^^^^^^
You now have to adjust the contents of the file ``settings.py`` located in ``/opt/localcosmos/localcosmos_private/localcosmos_private/`` to set up your LocalCosmos Private Server.

Replace ``INSTALLED_APPS`` with the following:

	.. code-block:: python

		INSTALLED_APPS = [

			# django defaults
			'django.contrib.admin',
			'django.contrib.auth',
			'django.contrib.contenttypes',
			'django.contrib.sessions',
			'django.contrib.messages',
			'django.contrib.staticfiles',

			# localcosmos
			'django.contrib.sites',

			'localcosmos_server',
			'localcosmos_server.app_admin',
			'localcosmos_server.server_control_panel',
			'localcosmos_server.datasets',
			'localcosmos_server.online_content',

			'django_road',    
			'anycluster',
			'content_licencing',

			'rules',
			'el_pagination',
			'django_countries',
			'corsheaders',
			'rest_framework',
			'rest_framework.authtoken',

			'octicons',
			'imagekit',

			'django.forms',
		]


Replace the ``MIDDLEWARE`` setting with the following

	.. code-block:: python

		MIDDLEWARE = [
			'localcosmos_server.middleware.LocalCosmosServerSetupMiddleware', # has to be on top
			'django.middleware.security.SecurityMiddleware',
			'django.contrib.sessions.middleware.SessionMiddleware',
			'django.middleware.locale.LocaleMiddleware',
			'corsheaders.middleware.CorsMiddleware',
			'django.middleware.common.CommonMiddleware',
			'django.middleware.csrf.CsrfViewMiddleware',
			'django.contrib.auth.middleware.AuthenticationMiddleware',
			'django.contrib.messages.middleware.MessageMiddleware',
			'django.middleware.clickjacking.XFrameOptionsMiddleware',
			'localcosmos_server.app_admin.middleware.AppAdminMiddleware',
			'localcosmos_server.server_control_panel.middleware.ServerControlPanelMiddleware',
		]


Replace the ``TEMPLATES`` setting with the following

	.. code-block:: python

		TEMPLATES = [
			{
				'BACKEND': 'django.template.backends.django.DjangoTemplates',
				'DIRS': [],
				'APP_DIRS': False,
				'OPTIONS': {
				    'context_processors': [
				        'django.template.context_processors.debug',
				        'django.template.context_processors.request',
				        'django.contrib.auth.context_processors.auth',
				        'django.contrib.messages.context_processors.messages',
				        'localcosmos_server.context_processors.localcosmos_server',
				    ],
				    'loaders' : [
				        'django.template.loaders.filesystem.Loader',
				        'django.template.loaders.app_directories.Loader',
				    ]
				}
			},
		]


Set up the database. Replace the ``DATABASE``setting with the setting below. Make sure you replace ``<lcpassword>`` with the correct password. If you did not follow the **Preparing your webserver** tutorial, you will also have to adjust the ``NAME`` and ``USER`` paramters according to your postgresql database name and your postgresql username.

	.. code-block:: python

		DATABASES = {
			'default': {
				'ENGINE': 'django.contrib.gis.db.backends.postgis',
				'NAME': 'localcosmos',
				'USER' : 'lcuser',
				'PASSWORD' : '<lcpassword>',
				'HOST' : 'localhost',
			}
		}



Replace ``ALLOWED_HOSTS`` with the following.

	.. code-block:: python

		ALLOWED_HOSTS = ['localhost']


Replace or add ``STATIC`` and ``MEDIA`` paths

    .. code-block:: python

		STATIC_URL = '/static/'
		STATIC_ROOT = '/var/www/localcosmos/static/'

		MEDIA_ROOT = '/var/www/localcosmos/media/'
		MEDIA_URL = '/media/'


Inlude localcosmos_server settings in your ``settings.py`` file. This automatically covers anycluster, django_road and cors settings. Insert these lines at the bottom of settings.py

    .. code-block:: python

		from localcosmos_server.settings import *

		# location where apps are installed
		# your apps index.html will be in LOCALCOSMOS_APPS_ROOT/{APP_UID}/www/index.html
		LOCALCOSMOS_APPS_ROOT = '/var/www/localcosmos/apps/' 


3.2 urls.py
^^^^^^^^^^^
The file ``urls.py`` located in ``/opt/localcosmos/localcosmos_private/localcosmos_private/`` also needs configuration. You ``urls.py`` should look like this:

	.. code-block:: python

		from django.conf import settings
		from django.contrib import admin
		from django.urls import path, include

		urlpatterns = [
			path('admin/', admin.site.urls),
			path('', include('localcosmos_server.urls')),
		]

As long as you run the django development server, add the following at the bottom of ``urls.py``.

	.. code-block:: python

		# remove these lines after development
		if settings.DEBUG:
			from django.conf.urls.static import static
			urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

Make sure your remove these lines before deploying django. For better security, static and media files should be served directly by nginx in a production environment.

That's it for the django configuration.



4. Migrate database
-------------------
In your django project directory, ``/opt/localcosmos/localcosmos_private/``, run

	.. code-block:: bash

		python manage.py migrate

to migrate the database.


5. Create localcosmos www folder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
We need the folder ``/var/www/localcosmos`` and django has to be able to write into it. Replace ``<server_user>`` with the user you use on your computer.

	.. code-block:: bash

		# if the folder does not exist yet
		sudo mkdir /var/www/localcosmos
		# run this command in any case
		sudo chown <server_user>:www-data /var/www/localcosmos


6. Run the development server
-----------------------------
In your django project directory, ``/opt/localcosmos/localcosmos_private/``, run the following command to start the development server.

	.. code-block:: bash

		python manage.py runserver 0.0.0.0:8080


Now open a browser and navigate to ``http://localhost:8080`` . Follow the instructions to complete the setup.

Also check if the API works. Browse to ``http://localhost:8080/api/`` .

After you completed the setup, the Server Control Panel ist available at ``http://localhost:8080/server/control-panel/``.


7. Re-running the development server
------------------------------------
If you want to start the development server after rebooting, you have to activate the virtual environment first.

	.. code-block:: bash

		cd /opt/localcosmos
		source venv/bin/activate
		cd localcosmos_private
		python manage.py runserver 0.0.0.0:8080
