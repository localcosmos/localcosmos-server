Set up Tutorial
===============

1. Installation using docker
----------------------------

Duration: 10-15 minutes.

1.1 Install and Configure nginx
-------------------------------
This is only required for a production environment. If you test on your local machine, you can skip this step.

	.. code-block:: bash

		sudo apt-get install nginx


Create the nginx conf file for your app. Replace ``<my-project.org>`` with the domain of your project.

	.. code-block:: bash
		
		touch /etc/nginx/sites-available/<my-project.org>.conf>
		

Put the following in your just created ``.conf`` file. Again, replace ``<my-project.org>`` with the domain of your project

	.. code-block:: bash

		upstream lcprivate_docker {
			server localhost:9202;
		}

		server {
			listen 80;
			server_name <my-project.org> www.<my-project.org>;
			return 301 https://<my-project.org>/$request_uri;
		}

		server {
			listen 443;
			server_name <my-project.org> www.<my_project.org>;

			location / {
				proxy_http_version 1.1;
				proxy_set_header Upgrade $http_upgrade;
				proxy_set_header Connection 'upgrade';
				proxy_set_header Host $host;
				proxy_set_header X-Real-IP $remote_addr;
				proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
				proxy_set_header X-Forwarded-Proto $scheme;
				proxy_cache_bypass $http_upgrade;
				proxy_pass http://lcprivate_docker;
			}

		}



1.2 Install docker
------------------

	.. code-block:: bash
		sudo apt-get install docker.io docker-compose

	.. code-block:: bash
		sudo systemctl start docker

	.. code-block:: bash
		sudo systemctl enable docker


1.3 pull the Local Cosmos Private Server docker image
-----------------------------------------------------

All docker commands have to be run as the superuser.

	.. code-block:: bash

		sudo docker pull docker.sisol-systems.com/localcosmos-private-server


1.4 Configuration with docker-compose.yml
-----------------------------------------
On your server, create a folder for your project.

	.. code-block:: bash

		mkdir /opt/<my-project-name>


Create the file docker-compose.yml

	.. code-block:: bash

		cd /opt/<my-project-name>
		touch docker-compose.yml


Put the following content into ``docker-compose.yml``. Replace ``<my-project-name>`` with the name of your project. Also Replace ``<db_username>`` and ``<db_password>``. This will **set** your database credentials, so do not share these values openly.

Also replace ``<.myproject.org>`` with the domain you run your Localcosmos Private Server on. Do not forget the leading ``.``. Finally, replace ``<APP_UID>`` with app_uid of your App. You find your app_uid in the App Kit on localcosmos.org. If you just want to run the Demo App on localhost, use ``treesofbavaria`` as the app_uid. You cannot run the Demo App on something else than localhost.

	.. code-block:: bash

		version: '3.3'

		services:
		  lc-private:
			container_name: '<my-project-name>'
			image: 'docker.sisol-systems.com/localcosmos-private-server' 
			restart: always
			build: .
			volumes:
			  - type: volume
				source: www
				target: /var/www/localcosmos/
			  - type: volume
				source: database_config
				target: /etc/postgresql/
			  - type: volume
				source: database_log
				target: /var/log/postgresql/
			  - type: volume
				source: database_data
				target: /var/lib/postgresql/
			ports:
			  - 9202:8001
			environment:
			  - DATABASE_NAME=localcosmos
			  - DB_USER=<db_username>
			  - DB_PASSWORD=<db_password>
			  - ALLOWED_HOSTS=localhost|<.myproject.org>
			  - APP_UID=<APP_UID>
			  - SERVE_APP_URL=/

		volumes:
		  www:
		  database_config:
		  database_log:
		  database_data:


Optionally, you can add email settings to the environment. This enables django to send email to you if an error occurs server-side.

	.. code-block:: bash
		  - EMAIL_HOST=<email_host>
		  - EMAIL_PORT=<email_port>
		  - EMAIL_HOST_USER=<email_host_user>
		  - EMAIL_HOST_PASSWORD=<email_host_password>
		  - EMAIL_USE_TLS=1

Replace ``<email_host>``, ``<email_port>``, ``<email_host_user>``, ``<email_host_password>`` with your parameters and set ``EMAIL_USE_TLS`` to 1 or 0.


1.5 Installation
----------------

	.. code-block:: bash

		cd /opt/<my-project-name>
		sudo docker-compose up -d


After Installation, visit ``localhost:9202/server/control-panel/`` or ``<myproject.org>/server/control-panel/`` and follow the on-screen instructions.

You now have your Local Cosmos Private Server up and running.

If you are on a local machine and want to test the Demo App, got to


2. Installation without docker
------------------------------

Duration: 30-45 minutes.

This tutorial covers setting up a running LocalCosmos Private Server as a development server. This tutorial is intended for people not familiar with django. For more information about django visit https://www.djangoproject.com/ .

2.0 Prerequisites
-----------------
Install all required server components as described in **Preparing your webserver**.

2.1 Create a new django project
-------------------------------

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


2.2 Configure your django project
---------------------------------

2.2.1 settings.py
^^^^^^^^^^^^^^^^^
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


2.2.2 urls.py
^^^^^^^^^^^^^
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



2.3 Migrate database
--------------------
In your django project directory, ``/opt/localcosmos/localcosmos_private/``, run

	.. code-block:: bash

		python manage.py migrate

to migrate the database.


2.4 Create localcosmos www folder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
We need the folder ``/var/www/localcosmos`` and django has to be able to write into it. Replace ``<server_user>`` with the user you use on your computer.

	.. code-block:: bash

		# if the folder does not exist yet
		sudo mkdir /var/www/localcosmos
		# run this command in any case
		sudo chown <server_user>:www-data /var/www/localcosmos


2.5 Run the development server
------------------------------
In your django project directory, ``/opt/localcosmos/localcosmos_private/``, run the following command to start the development server.

	.. code-block:: bash

		python manage.py runserver 0.0.0.0:8080


Now open a browser and navigate to ``http://localhost:8080`` . Follow the instructions to complete the setup.

Also check if the API works. Browse to ``http://localhost:8080/api/`` .

After you completed the setup, the Server Control Panel ist available at ``http://localhost:8080/server/control-panel/``.


2.6 Re-running the development server
-------------------------------------
If you want to start the development server after rebooting, you have to activate the virtual environment first.

	.. code-block:: bash

		cd /opt/localcosmos
		source venv/bin/activate
		cd localcosmos_private
		python manage.py runserver 0.0.0.0:8080
