Installation using docker
=========================

Duration: 15-30 minutes.

1. Install and Configure nginx
------------------------------
This is only required for a production environment. If you test on your local machine, you can skip this step.

	.. code-block:: bash

		sudo apt-get install nginx


Create the nginx conf file for your app. Replace ``<my-project.org>`` with the domain of your project.

	.. code-block:: bash
		
		sudo touch /etc/nginx/sites-available/<my-project.org>.conf
		
		
For example, if you plan to host your server at ``treesofbavaria.org``, use the following command:

	.. code-block:: bash
		
		sudo touch /etc/nginx/sites-available/treesofbavaria.org.conf
		

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

			client_max_body_size 50M;

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



2. Install docker
-----------------

Install docker and the docker-compose-utility

	.. code-block:: bash

		sudo apt-get install docker.io docker-compose


Start docker

	.. code-block:: bash

		sudo systemctl start docker


make docker start on boot

	.. code-block:: bash

		sudo systemctl enable docker


3. Get the Local Cosmos Private Server docker image
---------------------------------------------------

All docker commands have to be run as the superuser.

	.. code-block:: bash

		sudo docker pull docker.sisol-systems.com/localcosmos-private-server


4. Configuration with docker-compose.yml
----------------------------------------
On your server, create a folder for your project.

	.. code-block:: bash

		sudo mkdir /opt/<my-project-name>


Create the file docker-compose.yml

	.. code-block:: bash

		cd /opt/<my-project-name>
		sudo touch docker-compose.yml


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


5. Run the docker container
---------------------------

	.. code-block:: bash

		cd /opt/<my-project-name>
		sudo docker-compose up -d
		
		
6. Enable nginx conf and reload nginx conf
------------------------------------------
First, add your nginx conf to ``sites-enabled``. Replace ``<my-project.org>`` with the name of you project.

	.. code-block:: bash

		sudo ln -s /etc/nginx/sites-available/<my-project.org>.conf /etc/nginx/sites-enabled/
		

Now, reload your nginx conf with the following command.

	.. code-block:: bash

		sudo service nginx reload


After Installation, visit ``localhost:9202/server/control-panel/`` or ``<myproject.org>/server/control-panel/`` and follow the on-screen instructions.

You now have your Local Cosmos Private Server up and running.

If you are on a local machine and want to test the Demo App, proceed to **Installing the Demo App**.
