#!/bin/bash
#########################################################################################
# Simple script to start the LocalCosmos application.
# It will use the docker-compose.yml file to load the application and run it as daemon.
#########################################################################################

# Defaults
MIGRATE=true
DELETE_DATA=false
FORCE_BUILD=--no-cache

# Possible override by command line parameters for customization
optspec=":cfim-:"
while getopts "$optspec" optchar; do
  case "${optchar}" in
    -)
      case "${OPTARG}" in
        migrate)
          MIGRATE=true
          ;;
        force-build)
          FORCE_BUILD=--no-cache
          ;;
        delete-data)
          DELETE_DATA=true
          ;;
        esac;;
      m)
        MIGRATE=true
        ;;
      f)
        FORCE_BUILD=--no-cache
        ;;
  esac
done


echo "Stopping and removing localcosmos-private-server image (not volumes)"
# Remove any existing database container and its volumes
docker stop localcosmos-private-server ; docker rm -v localcosmos-private-server

if [[ $DELETE_DATA == true ]];
then
  # Remove any existing database named volumes
  echo "Removing the named volumes of the database"
  docker volume rm localcosmos-private-server_database_config
  docker volume rm localcosmos-private-server_database_log
  docker volume rm localcosmos-private-server_database_data
  
  echo "Removing the persistent named volumes of the web containers"
  # Remove the named volumes of the container
  docker volume rm localcosmos-private-server_www
  docker volume rm localcosmos-private-server_apps
fi


# Setting up error handling, exiting if any error occurs
ExitOnError () {
  exit 1;
}
trap ExitOnError ERR


# Copy or delete the .dockerignore file
echo "Removing any existing ignore file from local folder"
rm -f .dockerignore

# Build the image
echo "Build the localcosmos project"
docker-compose --project-name localcosmos-private-server build $FORCE_BUILD lc-private


# Start the environment
echo "Start up the localcosmos environment"
docker-compose --project-name localcosmos-private-server up -d

exit $?
