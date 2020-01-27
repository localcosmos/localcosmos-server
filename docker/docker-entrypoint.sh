#!/bin/bash

# start postgresql
/etc/init.d/postgresql start

# wait for the database to be available
/code/wait-for-it.sh localhost:5432 -t 60

# Create the database user if it does not exist yet
if su postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='$DB_USER';\"" | grep -q 1;
then
  echo "Database user $DB_USER already exists"
else
  echo "Create the database user $DB_USER"
  su postgres -c "psql --command \"CREATE USER $DB_USER WITH SUPERUSER PASSWORD '$DB_PASSWORD';\""
fi

# Create the database if it does not yet exist
if [[ -z $(su postgres -c "psql -Atqc '\list $DATABASE_NAME'") ]];
then
  echo "Create database $DATABASE_NAME"
  su postgres -c "createdb -O $DB_USER $DATABASE_NAME"
  echo "activate kmeans postgresql extension"
  su postgres -c "psql -f /usr/share/postgresql/10/extension/kmeans.sql -d $DATABASE_NAME"
else
  echo "Database $DATABASE_NAME already exists"
fi


# Then do the python migration and one time db configuration
if [[ $MIGRATE == true ]];
then
  echo "Perform python migrations"
  python3 /opt/localcosmos/localcosmos_private/manage.py migrate

  echo "Copy all statics to their proper location"
  python3 /opt/localcosmos/localcosmos_private/manage.py collectstatic --no-input
fi

# create correct nginx conf
envsubst '${SERVE_APP_URL} ${APP_UID}' < /etc/nginx/conf.d/localcosmos-server.conf.template > /etc/nginx/conf.d/localcosmos-server.conf

# start nginx uwsgi
uwsgi --ini /opt/localcosmos/uwsgi/localcosmos-server-uwsgi.ini &&\
            nginx -g 'daemon off;'

