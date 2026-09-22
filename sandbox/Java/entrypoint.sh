#!/bin/bash
set -euo pipefail
ssh-keygen -A
/usr/local/bin/tomcat-control start
# SSH stays available after a Tomcat failure. Only Yubarta or the user restarts Tomcat.
exec /usr/sbin/sshd -D -e
