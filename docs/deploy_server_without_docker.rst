Deploy your Server (without docker)
===================================

Once you have successfully tested your LocalCosmos Private Server in development mode, you can deploy your server and make it accessible for the public. This tutorial covers deployment of Local Cosmos Private Server using ``nginx``, ``uwsgi`` and Ubuntu 18.04.

1. Make your django application ready
-------------------------------------

1.1 Update settings.py
^^^^^^^^^^^^^^^^^^^^^^
Add your Domain name, in this example ``localcosmos-private.org``, to ``ALLOWED_HOSTS`` in your ``settings.py`` file. Also set ``DEBUG`` to ``False``.

	.. code-block:: python
		
		ALLOWED_HOSTS = ['localcosmos-private.org']

		DEBUG = False


1.2 Check the application
^^^^^^^^^^^^^^^^^^^^^^^^^
Run the development server once to check if there are errors

	.. code-block:: bash
		
		cd /opt/localcosmos
		source venv/bin/activate
		python manage.py runserver 0.0.0.0:8080


If you installed the Demo App (Trees Of Bavaria), you have to remove it before continuing. The Demo App is not configured to run with a deployed Local Cosmos Private Server. Go to ``http://localhost:8080/server/control-panel/`` and remove the App.


If there are no errors, stop the development server and continue.


1.3 Clean urls.py
^^^^^^^^^^^^^^^^^
Remove the development lines from ``urls.py``

	.. code-block:: bash

		# remove these lines after development
		#if settings.DEBUG:
		#	from django.conf.urls.static import static
		#	urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


2. uwsgi
--------

2.1 Install uwsgi
^^^^^^^^^^^^^^^^^
If still active, deactivate your virtual environment. We have to install uwsgi system-wide and not inside the virtual environment.

	.. code-block:: bash

		deactivate


Install ``uwsgi`` using ``pip``:

	.. code-block:: bash

		sudo apt-get install python3-pip
		sudo -H pip3 install uwsgi


2.2 Create uwsgi.ini
^^^^^^^^^^^^^^^^^^^^
First, create a ``uwsgi`` folder where all the uwsgi stuff will go

	.. code-block:: bash

		cd /opt/localcosmos
		mkdir uwsgi

Create the file ``localcosmos_private_uwsgi.ini`` in ``/opt/localcosmos/uwsgi/`` 

	.. code-block:: bash

		cd /opt/localcosmos/uwsgi/
		touch localcosmos_private_uwsgi.ini

and put the following in it:

	.. code-block:: sourcecode

		# localcosmos_private_uwsgi.ini file
		[uwsgi]

		# Django-related settings

		# the base directory (full path)
		chdir           = /opt/localcosmos/localcosmos_private

		# Django's wsgi file
		module          = localcosmos_private.wsgi:application

		# the virtualenv (full path)
		home            = /opt/localcosmos/venv

		# process-related settings
		# master
		master          = true
		# maximum number of worker processes
		processes       = 10

		# the socket (use the full path to be safe)
		socket          = /opt/localcosmos/uwsgi/socket/localcosmos-private.sock

		# ... with appropriate permissions - may be needed
		chmod-socket    = 666

		# clear environment on exit
		vacuum          = true

		daemonize 		= /var/log/uwsgi/localcosmos-private.log


2.3 Prepare the socket
^^^^^^^^^^^^^^^^^^^^^^
The socket ``localcosmos-private.sock`` will automatically be created. Therefore, we need a folder ``www-data`` can write into.

	.. code-block:: bash

		cd /opt/localcosmos/uwsgi
		mkdir socket
		# set permissions
		sudo chgrp www-data /opt/localcosmos/uwsgi/socket
 

2.4 Get uwsgi_params
^^^^^^^^^^^^^^^^^^^^

	.. code-block:: bash
		
		cd /opt/localcosmos/uwsgi
		wget https://raw.githubusercontent.com/nginx/nginx/master/conf/uwsgi_params


2.5 Logging
^^^^^^^^^^^

	.. code-block:: bash

		sudo mkdir /var/log/uwsgi
		sudo chown <server-user>:www-data /var/log/uwsgi



3. Configure nginx
------------------

3.1 Create nginx conf file
^^^^^^^^^^^^^^^^^^^^^^^^^^
First you have to create an nginx configuration file. Best practice is to name the file after the domain. For this tutorial we assume the domain is ``localcosmos-private.org``, so we create the file ``localcosmos-private.org.conf``. Adjust the filename according to the domain name you will use for your Local Cosmos Private Server.

	.. code-block:: bash

		cd /etc/nginx/sites-available
		sudo touch localcosmos-private.org.conf



Now put the following code into this file.

	.. code-block:: sourcecode

		# localcosmos-private.org.conf

		# the upstream component nginx needs to connect to
		upstream django {
			# according to recommendations, we use a file socket
			server unix:///opt/localcosmos/uwsgi/socket/localcosmos-private.sock;
		}

		# configuration of the server
		server {

			# the port your site will be served on
			listen      80;

			# the domain name it will serve for
			server_name localcosmos-private.org;

			charset     utf-8;

			# max upload size
			client_max_body_size 75M;   # adjust to taste

			# serve django media files according to settings.py
			location /media  {
				alias /var/www/localcosmos/media;
			}

			# serve django static files according to settings.py
			location /static {
				alias /var/www/localcosmos/static;
			}

			# pass /server to django
			location /server {
				uwsgi_pass  django;
				include     /opt/localcosmos/uwsgi/uwsgi_params;
			}

			# pass /app-admin to django
			location /app-admin {
				uwsgi_pass  django;
				include     /opt/localcosmos/uwsgi/uwsgi_params;
			}

			# pass /api to django
			location /api {
				uwsgi_pass  django;
				include     /opt/localcosmos/uwsgi/uwsgi_params;
			}

			# (optional) the app you are going to install at a later point

			location / {
				alias /var/www/localcosmos/apps/<APP_UID>/www/;
				try_files $uri $uri/index.html;
			}
		}

3.2 Make your site available
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Create the symlink to ``localcosmos-private.org.conf`` in ``/etc/nginx/sites-enabled/``

	.. code-block:: bash

		sudo ln -s /etc/nginx/sites-available/localcosmos-private.org.conf /etc/nginx/sites-enabled/


3.3 Collect static files
^^^^^^^^^^^^^^^^^^^^^^^^
Create the folder ``localcosmos`` in ``/var/www`` with the correct permissions, if it does not exist yet. Replace ``<server_user>`` with your username on your server.

	.. code-block:: bash

		cd /var/www
		sudo mkdir localcosmos
		sudo chown <serveruser>:www-data localcosmos

		# if not yet active, activate the virtual environment
		cd /opt/localcosmos
		source venv/bin/activate

		# collect static files
		cd localcosmos_private
		python manage.py collectstatic

		# deactivate virtualenv
		deactivate


3.4 Reload nginx
^^^^^^^^^^^^^^^^

	.. code-block:: bash

		sudo service nginx reload


Test your uwsgi setup using this command.

	.. code-block:: bash

		/usr/local/bin/uwsgi --ini /opt/localcosmos/uwsgi/localcosmos_private_uwsgi.ini --uid www-data --gid www-data


Now open ``http://YOUR_DOMAIN.org/server/control-panel/`` in a browser and check if it works.

On some installations you have to remove ``default`` from ``sites-enabled`` (NOT ``sites-available`` !!)

	.. code-block:: bash

		cd /etc/nginx/sites-enabled
		sudo rm default
		sudo service nginx reload


3.5 Make uwsgi startup when the system boots
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Create the file ``/etc/rc.local`` if it does not exist yet.

	.. code-block:: bash

		sudo touch /etc/rc.local
		sudo chmod +x /etc/rc.local


Put the following in it:

	.. code-block:: sourcecode

		#!/bin/sh -e
		# rc.local

		/usr/local/bin/uwsgi --ini /opt/localcosmos/uwsgi/localcosmos_private_uwsgi.ini --uid www-data --gid www-data

		exit 0


**That's it! You now have a fully working Local Cosmos Private Server!**


4. Troubleshooting
------------------

1. Check ``/var/log/nginx/error.log``
2. Check ``/var/log/uwsgi/localcosmos-private.log``
3. Read https://uwsgi-docs.readthedocs.io/en/latest/tutorials/Django_and_nginx.html
