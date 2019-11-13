LocalCosmos Private Server Tutorial 
===================================

This tutorial covers setting up a running LocalCosmos Private Server and installing an App on it.

0. Prequisities
---------------

Install all required server components.


1. Create a new django project
------------------------------

**Create a project folder**

Create a folder on your disk where your LocalCosmos Private Server can live. eg: ``/opt/localcosmos``


**Create a python3 virtual environment**

   .. code-block:: bash

      cd /opt/localcosmos
      virtualenv -p python3 venv


**Activate the virtual environment**

   .. code-block:: bash

      source venv/bin/activate


**Install django and localcosmos_server**

   .. code-block:: bash

      pip install django
      pip install localcosmos_server


**Create a new django project**

In ``/opt/localcosmos`` execute the following:

   .. code-block:: bash

      django_admin.py startproject localcosmos_private


This will automatically create the folder ``/opt/localcosmos/localcosmos_private``, which contains your newly created django project.


2. Configure your django project
--------------------------------

**settings.py**

You now have to adjust the contents ``/opt/localcosmos/localcosmos_private/localcosmos_private/settings.py`` to set up your LocalCosmos Private Server.

Add the following to ``INSTALLED_APPS``

    .. code-block:: python

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


Configure the middleware chain

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


Include rules in the authenticatoin backend for per-object-permissions

	.. code-block:: python

		AUTHENTICATION_BACKENDS = (
			'rules.permissions.ObjectPermissionBackend', # LC
			'django.contrib.auth.backends.ModelBackend', # LC
		)


Set context processors and template loaders

	.. code-block:: python

		TEMPLATES = [
			{
				'BACKEND': 'django.template.backends.django.DjangoTemplates',
				'DIRS': [],
				#'APP_DIRS': True,
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


Set up the database

	.. code-block:: python

		DATABASES = {
			'default': {
				'ENGINE': 'django.contrib.gis.db.backends.postgis',
				'NAME': 'localcosmos', # or any other name
				'USER' : YOURDBUSER,
				'PASSWORD' : YOURDBPASSWORD,
				'HOST' : 'localhost',
			}
		}

Set ``STATIC`` and ``MEDIA`` paths

    .. code-block:: python

       STATIC_URL = '/static/'
       STATIC_ROOT = '/var/www/localcosmos/static/'

       MEDIA_ROOT = '/var/www/localcosmos/media/'
       MEDIA_URL = '/media/'



Inlude localcosmos_server settings. This covers anycluster, django_road and cors settings.

    .. code-block:: python

		from localcosmos_server.settings import *


Set localcosmos specific variables

	.. code-block:: python

		# location where apps are installed
		# your apps index.html will be in LOCALCOSMOS_APPS_ROOT/{APP_UID}/www/index.html
		LOCALCOSMOS_APPS_ROOT = '/var/www/localcosmos/apps/' 

		LOCALCOSMOS_SPONSORING_API = 'https://staging.localcosmos.org/api/sponsoring/'


Now your django LocalCosmos Private Server is configured.


3. set up nginx or apache
-------------------------
