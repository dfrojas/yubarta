#!/bin/bash
# E2E entrypoint: sshd + real JVM workload. tini reaps killed JVM processes;
# the container follows logs independently of JVM restarts.
service ssh start 2>/dev/null || /usr/sbin/sshd
/usr/local/bin/appctl start
touch /var/log/apache2/error.log
chmod 666 /var/log/apache2/error.log
exec tail -F /var/log/apache2/error.log /var/log/yubarta-app/app.log 2>/dev/null || exec sleep infinity
