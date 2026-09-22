# Fast E2E target: compile the Java workload, then run it on a JRE + sshd.
FROM eclipse-temurin:17-jdk-noble AS build
COPY src/HelloApp.java /src/HelloApp.java
RUN javac -d /out /src/HelloApp.java

FROM eclipse-temurin:17-jre-noble

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server sudo procps curl tini \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/run/sshd /var/log/apache2 /var/log/yubarta-app /run/yubarta-app /srv/app /opt/yubarta \
    && useradd -m -s /bin/bash yubarta \
    && echo "yubarta:yubarta" | chpasswd \
    && echo "yubarta ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/yubarta \
    && touch /var/log/apache2/error.log && chmod 666 /var/log/apache2/error.log \
    && ln -sf /opt/java/openjdk/bin/java /usr/local/bin/java

COPY --from=build /out /srv/app
COPY entrypoint.sh /entrypoint.sh
COPY appctl /usr/local/bin/appctl
COPY scripts/ /opt/yubarta/
RUN chmod +x /entrypoint.sh /usr/local/bin/appctl /opt/yubarta/*

EXPOSE 22 8080
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/entrypoint.sh"]
