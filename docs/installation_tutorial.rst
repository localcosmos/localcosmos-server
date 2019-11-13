Setting up a LocalCosmos Private Server as a development server
===============================================================

This tutorial covers setting up a running LocalCosmos Private Server as a development server and installing an App on it.

0. Prerequisites
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
This will install django, localcosmos_server and its requirements in your created and activated virtualenv. 
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
		INSTALLED_APPS = [

			(...)		

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
			'rules.permissions.ObjectPermissionBackend',
			'django.contrib.auth.backends.ModelBackend',
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


**urls.py**
	.. code-block:: python
		from django.conf import settings
		from django.contrib import admin
		from django.urls import path, include

		urlpatterns = [
			(...)
			path('admin/', admin.site.urls),
			path('', include('localcosmos_server.urls')),
			path('api/', include('localcosmos_server.api.urls')),
		]

If you plan to run a django development server for settings, add the following at the bottom of ``urls.py``.
	.. code-block:: python
		# remove this line after development
		if settings.DEBUG:
			from django.conf.urls.static import static
			urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

Make sure your remove these lines before deploying django. For better security, static and media files should be served directly by nginx (see 3.1).

That's it for the django configuration.


3. set up nginx or apache
-------------------------
This tutorial covers nginx examples. If you plan to use apache2, you have to translate the examples into apache2 syntax.

3.1 Configure nginx to serve django static and media files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Configure nginx locations according to your django projects ``STATIC_ROOT`` and ``MEDIA_ROOT`` settings in ``settings.py``.

	.. code-block:: sourcecode
		location /media  {
			alias /var/www/localcosmos/media/;
		}

		location /static {
			alias /var/www/localcosmos/static/;
		}


3.2 Configure nginx to serve your webapp
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Later, you will install your webapp using the **Server Control Panel** of your LocalCosmos Private Server. Your webapps will automatically be stored in a subfolder of the folder defined in ``settings.LOCALCOSMOS_APPS_ROOT``. The ``uid`` of your app will be name of this subfolder. You can look up the uid of your app on localcosmos.org. The webapp consists of a ``www`` folder which contains an ``index.html``.

abstract example:
	.. code-block:: sourcecode
		LOCALCOSMOS_APPS_ROOT/{APP_UID}/www/index.html

concrete example:
	.. code-block:: sourcecode
		/var/www/localcosmos/myapp/www/index.html


Create an alias to serve your webapp. If you want to server your app on the root of your domain: 
	.. code-block:: sourcecode
		location / {
			alias /var/www/localcosmos/apps/myapp/www;
		}

It is very important to remember the url which your webapp will be served at because you will have to enter this url in the **Server Control Panel**

Reserved locations are:
	.. code-block:: sourcecode
		/server-control-panel
		/app-admin
		/api
		/login
		/logout
		/load-footer-sponsors

You cannot use these locations for your webapps because they are used by your django application.
