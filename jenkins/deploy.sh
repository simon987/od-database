#!/bin/bash

export ODDBROOT="od-database"

virtualenv ${ODDBROOT}/env -p python3.7
source ${ODDBROOT}/env/bin/activate
pip install -r ${ODDBROOT}/requirements.txt

screen -S oddb_web -X quit
killall -9 uwsgi

sleep 15

echo "starting oddb_web"
screen -S oddb_web -d -m bash -c "cd ${ODDBROOT} && source env/bin/activate && uwsgi od-database.ini 2> stderr.txt"
sleep 1
screen -list