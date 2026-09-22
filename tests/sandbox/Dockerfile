FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends openssh-server sudo python3 procps util-linux && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --shell /bin/bash yubarta && passwd -d yubarta && mkdir -p /run/sshd /var/log/apache2 /opt/yubarta /var/lib/yubarta-sandbox && touch /var/log/apache2/error.log && chmod 644 /var/log/apache2/error.log
COPY yubarta/controllers/remediations/scripts/ /opt/yubarta/
COPY tests/sandbox/service.py /opt/sandbox/service.py
COPY tests/sandbox/control.py /usr/local/bin/systemctl
COPY tests/sandbox/swapon.py /usr/local/bin/swapon
COPY tests/sandbox/start.sh /opt/sandbox/start.sh
RUN chmod 755 /opt/yubarta/* /usr/local/bin/systemctl /usr/local/bin/swapon /opt/sandbox/start.sh && ln -s /usr/local/bin/systemctl /usr/local/bin/sandbox-control && printf 'yubarta ALL=(root) NOPASSWD: /usr/local/bin/systemctl *, /usr/local/bin/sandbox-control *, /opt/yubarta/ensure-swap, /opt/yubarta/fix-tomcat-restart-policy\n' > /etc/sudoers.d/yubarta && chmod 440 /etc/sudoers.d/yubarta && printf 'PasswordAuthentication no\nPermitRootLogin no\nPubkeyAuthentication yes\n' > /etc/ssh/sshd_config.d/yubarta.conf
ENTRYPOINT ["/opt/sandbox/start.sh"]
