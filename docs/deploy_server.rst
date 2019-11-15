Deploy your Server
==================

Once you have successfully tested your LocalCosmos Private Server in development mode youcan deploy your server and make it accessible for the public.

1. Configure nginx
------------------

1.1 Configure nginx to serve django static and media files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Configure nginx locations according to your django projects ``STATIC_ROOT`` and ``MEDIA_ROOT`` settings in ``settings.py``.

	.. code-block:: sourcecode

		location /media  {
			alias /var/www/localcosmos/media/;
		}

		location /static {
			alias /var/www/localcosmos/static/;
		}


1.2 Configure nginx to serve your django LocalCosmos Private Server using wsgi
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

	.. code-block:: sourcecode
		location /server-control-panel {
		    uwsgi_pass  django;
		    include     /var/www/localcosmos/uwsgi_params; # path to the uwsgi_params file you installed
		}

		location /app-admin {
			uwsgi_pass  django;
		    include     /var/www/localcosmos/uwsgi_params; # path to the uwsgi_params file you installed
		}

		location /api {
			uwsgi_pass  django;
		    include     /var/www/localcosmos/uwsgi_params; # path to the uwsgi_params file you installed
		}

		location /login {
			uwsgi_pass  django;
		    include     /var/www/localcosmos/uwsgi_params; # path to the uwsgi_params file you installed
		}

		location /logout {
			uwsgi_pass  django;
		    include     /var/www/localcosmos/uwsgi_params; # path to the uwsgi_params file you installed
		}

		location /load-footer-sponsors {
			uwsgi_pass  django;
		    include     /var/www/localcosmos/uwsgi_params; # path to the uwsgi_params file you installed
		}
