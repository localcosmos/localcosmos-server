Installing the Demo App
=======================

The Demo App should **only be installed on a local development server for testing**. This tutorial covers nginx examples. If you plan to use apache2, you have to translate the examples into apache2 syntax.


0. Prerequisites
----------------

A running LocalCosmos Private development server.


1. Download the Demo App
------------------------
The Demo App is a .zip file named ``TreesOfBavaria.zip``.
You can dowload it `here <https://localcosmos.org/media/TreesOfBavaria.zip>`_ .

Note: The Demo App covers the Webapp version of Trees Of Bavaria. If you build your own App on localcosmos.org, you will receive Android and iOS versions alongside the Webapp version.

The Demo App expects a development server running at ``http://localhost:8080`` and the LocalCosmos Private Server api running at ``http://localhost:8080/api/``. Otherwise the Demo App will not work. 


2. Configure nginx to serve your webapp
---------------------------------------
LocalCosmos Webapps are served by nginx or apache2, not by django.

Later, you will install your webapp using the **Server Control Panel** of your LocalCosmos Private Server. Your webapps will automatically be stored in a subfolder of the folder defined in ``settings.LOCALCOSMOS_APPS_ROOT``. The ``UID`` of your app will be name of this subfolder.  The ``UID`` of the Demo App is ``treesofbavaria``. So this app will be installed in e.g. ``/var/www/localcosmos/apps/treesofbavaria``, if your ``LOCALCOSMOS_APPS_ROOT`` setting in ``settings.py`` is ``/var/www/localcosmos/apps``.

abstract example:
	.. code-block:: sourcecode

		LOCALCOSMOS_APPS_ROOT/{APP_UID}/www/index.html


The ``UID`` of the Demo App is ``treesofbavaria``. For this test we serve the App at the root directory ``/``. Open the configuration file named ``default`` living in ``/etc/nginx/sites-available/`` and modify ``location /`` as follows:

	.. code-block:: sourcecode

		location / {
			alias /var/www/localcosmos/apps/treesofbavaria/www/;
			try_files $uri $uri/index.html;
		}


Do not forget to reload the nginx conf

	.. code-block:: bash

		sudo service nginx reload

With this configuration, the Demo App will later be available the URL ``http://localhost/`` (after it has been installed).


It is very important to **remember the url** which your webapp will be served at because you will have to enter this url in the **Server Control Panel** when installing an app.

Reserved locations are:
	.. code-block:: sourcecode

		/server
		/app-admin
		/api

You cannot use these locations for your webapps because they are used by the Local Cosmos Private Server django application.


3. Run the development server
-----------------------------
If not yet done, activate the virtual environment first

	.. code-block:: bash

		cd /opt/localcosmos
		# activate virtual environment if not yet activated
		source venv/bin/activate
		# start the server
		cd /opt/localcosmos/localcosmos_private
		python manage.py runserver 0.0.0.0:8080


The Demo App expects the Local Cosmos Server being available at ``http://localhost:8080/``, so make sure you do not use something else.


4. Install the Demo App
-----------------------
Open ``http://localhost:8080/server/control-panel/`` and click on ``Install App``.

1. Select the zipfile ``TreesOfBavaria.zip`` which you just downloaded.
2. Enter ``http://localhost/`` (or the URL according to your webserver configuration) as the URL of this App.
3. Click the Install button

Once the installation is complete, visit ``http://localhost/`` to open the Webapp.
