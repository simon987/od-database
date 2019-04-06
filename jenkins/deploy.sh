#!/bin/bash

export ODDBROOT="od-database"

virtualenv ${ODDBROOT}/env -p python3.7
source ${ODDBROOT}/env/bin/activate
pip install -r ${ODDBROOT}/requirements.txt

screen -S oddb_web -X quit
killall -9 uwsgi

sleep 5

echo "starting oddb_web"
screen -S oddb_web -d -m bash -c "cd ${ODDBROOT} && source env/bin/activate && uwsgi od-database.ini 2> stderr.txt"
sleep 1
screen -list

echo "Installing crontabs"
absolute_dir=$(cd ${ODDBROOT} && pwd)

# Re-crawl dirs
command="bash -c \"cd '${absolute_dir}' && source env/bin/activate && python do_recrawl.py >> recrawl_logs.txt\""
job="*/10 * * * * $command"
echo "$job"
cat <(fgrep -i -v "$command" <(crontab -l)) <(echo "$job") | crontab -

# Cleanup captchas
command="bash -c \"cd '${absolute_dir}' && rm captchas/*.png\""
job="*/60 * * * * $command"
echo "$job"
cat <(fgrep -i -v "$command" <(crontab -l)) <(echo "$job") | crontab -
