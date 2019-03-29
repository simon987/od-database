#!/bin/bash

export ODDBROOT="od-database"

screen -S oddb_web -X quit
killall -9 uwsgi

sleep 30

echo "starting oddb_web"
screen -S oddb_web -d -m bash -c "cd ${ODDBROOT} && uwsgi od-database.ini 2> stderr.txt"
sleep 1
screen -list