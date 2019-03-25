#!/bin/bash

export ODDBROOT="od-database"

screen -S oddb_web -X quit
echo "starting oddb_web"
screen -S oddb_web -d -m bash -c "cd ${ODDBROOT} && uwsgi od-database.ini"
sleep 1
screen -list