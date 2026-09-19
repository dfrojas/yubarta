FROM tomcat:10.1.55-jdk17-temurin-noble AS build
COPY src/HelloServlet.java /src/HelloServlet.java
COPY web.xml /war/WEB-INF/web.xml
RUN mkdir -p /war/WEB-INF/classes \
    && javac -cp /usr/local/tomcat/lib/servlet-api.jar -d /war/WEB-INF/classes /src/HelloServlet.java \
    && jar --create --file /ROOT.war -C /war .

FROM tomcat:10.1.55-jdk17-temurin-noble
RUN apt-get update && apt-get install -y --no-install-recommends \
      openssh-server sudo curl procps tini \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --home-dir /usr/local/tomcat --shell /usr/sbin/nologin tomcat \
    && useradd --create-home --shell /bin/bash yubarta \
    && echo 'yubarta:yubarta' | chpasswd \
    && mkdir -p /run/sshd /run/yubarta-tomcat \
    && printf '%s\n' 'PasswordAuthentication yes' 'PermitRootLogin no' > /etc/ssh/sshd_config.d/yubarta.conf \
    && printf '%s\n' 'yubarta ALL=(root) NOPASSWD: /usr/local/bin/tomcat-control status, /usr/local/bin/tomcat-control restart, /usr/bin/tail -n 60 /usr/local/tomcat/logs/catalina.out' > /etc/sudoers.d/yubarta \
    && chmod 440 /etc/sudoers.d/yubarta
COPY --from=build /ROOT.war /usr/local/tomcat/webapps/ROOT.war
COPY tomcat-control /usr/local/bin/tomcat-control
COPY entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh /usr/local/bin/tomcat-control \
    && chown -R tomcat:tomcat /usr/local/tomcat /run/yubarta-tomcat
EXPOSE 22 8080
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/entrypoint.sh"]
