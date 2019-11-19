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


The ``UID`` of the Demo App is ``treesofbavaria``. If you want to serve your app at the root directory ``/``, set the location alias as follows:

	.. code-block:: sourcecode

		location / {
			alias /var/www/localcosmos/apps/treesofbavaria/www;
		}


Do not forget to reload the nginx conf

	.. code-block:: bash

		sudo service nginx reload

The Demo App can now be served at the URL ``http://localhost/`` after it has been installed.


It is very important to **remember the url** which your webapp will be served at because you will have to enter this url in the **Server Control Panel** when installing an app.

Reserved locations are:
	.. code-block:: sourcecode

		/server-control-panel
		/app-admin
		/api
		/login
		/logout
		/load-footer-sponsors

You cannot use these locations for your webapps because they are used by the LocalCosmos Private Server django application.


3. Install the Demo App
-----------------------
Open ``http://localhost:8080/server-control-panel/`` and click on ``Install App``.

1. Select the zipfile ``TreesOfBavaria.zip`` you just downloaded.
2. Enter ``http://localhost/`` (or the URL according to your webserver configuration) to open the Webapp.
3. Click the install button

Now you can visit ``http://localhost/`` and start using the Demo App.
