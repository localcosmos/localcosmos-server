Installing the Demo App
=======================

The Demo App should **only be installed on a local development server for testing**. This tutorial covers nginx examples. If you plan to use apache2, you have to translate the examples into apache2 syntax.


0. Prerequisites
----------------

In this tutorial, we will configure the following setup:

+---------------------------------------------------+------------------------------+----------------------------+
| URL                                               | Function                     | Served by                  |
+===================================================+==============================+============================+
| http://localhost:8080/server/control-panel/       | Server Control Panel         | django development server  |
+---------------------------------------------------+------------------------------+----------------------------+
| http://localhost:8080/api/                        | API                          | django development server  |
+---------------------------------------------------+------------------------------+----------------------------+
| http://localhost:8080/app-admin/treesofbavaria/   | App Admin (Trees Of Bavaria) | django development server  |
+---------------------------------------------------+------------------------------+----------------------------+
| http://localhost/                                 | Trees Of Bavaria Webapp      | nginx                      |
+---------------------------------------------------+------------------------------+----------------------------+

The App Admin for the Demo App, Trees Of Bavaria, will be available after the App has been installed.
This Demo App expects the Local Cosmos Private Server api running at ``http://localhost:8080/api/``. Otherwise the Demo App will not work.

Start your Local Cosmos Development Server:

	.. code-block:: bash

		cd /opt/localcosmos
		# activate virtual environment if not yet activated
		source venv/bin/activate
		# start the server
		cd /opt/localcosmos/localcosmos_private
		python manage.py runserver 0.0.0.0:8080


1. Download the Demo App
------------------------
The Demo App is a .zip file named ``TreesOfBavaria.zip``.
You can dowload it `here <https://localcosmos.org/media/TreesOfBavaria.zip>`_ .

Note: The Demo App covers the Webapp version of Trees Of Bavaria. If you build your own App on localcosmos.org, you will receive Android and iOS versions alongside the Webapp version.

 

2. Configure nginx to serve your Webapp
---------------------------------------
Local Cosmos Webapps are served by nginx or apache2, not by django.

Later, you will install your webapp using the **Server Control Panel** of your Local Cosmos Private Server. Your webapps will automatically be stored in a subfolder of the folder defined by ``LOCALCOSMOS_APPS_ROOT`` in your ``settings.py`` file. The ``UID`` of your app will be the name of this subfolder.  The ``UID`` of the Demo App is ``treesofbavaria`` and ``LOCALCOSMOS_APPS_ROOT`` is set to ``/var/www/localcosmos/apps/``. So this app will be installed in ``/var/www/localcosmos/apps/treesofbavaria/``.


For this test we serve the App at the root directory ``/``. Open the configuration file named ``default`` living in ``/etc/nginx/sites-available/`` and modify ``location /`` as follows:

	.. code-block:: sourcecode

		location / {
			# /LOCALCOSMOS_APPS_ROOT/<APP_UID>/www/
			alias /var/www/localcosmos/apps/treesofbavaria/www/;
			try_files $uri $uri/index.html;
		}


Do not forget to reload the nginx conf

	.. code-block:: bash

		sudo service nginx reload

With this configuration, the Demo App will later be available the URL ``http://localhost/`` (after it has been installed).


It is very important to **remember the url** which your webapp will be served at **by nginx** because you will have to enter this url in the **Server Control Panel** when installing an app.


3. Install the Demo App
-----------------------
Open ``http://localhost:8080/server/control-panel/`` and click on ``Install App``.

1. Select the zipfile ``TreesOfBavaria.zip`` which you just downloaded.
2. Enter ``http://localhost/`` (or the URL according to your webserver configuration) as the URL of this App.
3. Click the Install button

Once the installation is complete, visit ``http://localhost/`` to open the Webapp. To test the API, try logging in with the Superuser Account credentials you created in the server tutorial, or try to report an observation.
