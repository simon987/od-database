#!/bin/bash

export ODDBROOT="od-database"

screen -S oddb -X quit
echo "starting oddb_web"
screen -S tt_drone -d -m bash -c "cd ${ODDBROOT} && uwsgi od-database.ini"
sleep 1
screen -list