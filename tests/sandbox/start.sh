#!/bin/sh
set -eu
install -d -m 700 -o yubarta -g yubarta /home/yubarta/.ssh
install -m 600 -o yubarta -g yubarta /run/test-key.pub /home/yubarta/.ssh/authorized_keys
ssh-keygen -A
systemctl restart tomcat9
exec /usr/sbin/sshd -D -e
