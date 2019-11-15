Installing the Demo App
=======================

The Demo App should **only be installed on a development server for testing**.


0. Prerequisites
----------------

A running LocalCosmos Private development server. 


1. Download the Demo App
------------------------
The Demo App is a .zip file named ``TreesOfBavaria.zip``.
You can dowload it at https://github.com/SiSol-Systems/localcosmos-server/demo-app/blob/master/TreesOfBavaria.zip .

The Demo App expects a development server running at ``http://localhost:8080`` and the LocalCosmos Private Server api running at ``http://localhost:8080/api/``. Otherwise the Demo App will not work. 


2. Prepare your nginx or apache server
--------------------------------------
The ``UID`` of the app is ``treesofbavaria``. So this app will be installed in e.g. ``/var/www/localcosmos/apps/treesofbavaria``, if your ``LOCALCOSMOS_APPS_ROOT`` setting in ``settings.py`` is ``/var/www/localcosmos/apps``.

The Demo App will be served by your webserver after installation, not by django. If you want to serve your app at the root directory ``/``, set the location alias as follows (nginx)
	.. code-block:: sourcecode

		location / {
			alias /var/www/localcosmos/apps/treesofbavaria/www;
		}


3. Install the Demo App
-----------------------
Open ``http://localhost:8080/server-control-panel/`` and click in ``Install App``.

1. Select the zipfile ``TreesOfBavaria.zip`` you just downloaded.
2. Enter ``localhost/`` as URL of this App, according to your webservers configuration
3. Click the install button

Now you can visit ``http://localhost/`` (no port given) and use the Demo App.
