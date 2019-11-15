Deploy your Server
==================

Once you have successfully tested your LocalCosmos Private Server in development mode youcan deploy your server and make it accessible for the public.

1. Configure nginx and uwsgi
----------------------------


1.1 Configure nginx to serve your django LocalCosmos Private Server using wsgi
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
