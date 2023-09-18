FROM centos:7
MAINTAINER TenDB-New-DBHA Development

ARG BASEDIR=/home/mysql/dbha

COPY dbha /usr/bin/

RUN groupadd -r dbmysql && useradd -r -g dbmysql dbmysql \
    && /usr/bin/install -m 0775 -o dbmysql -g root -d ${BASEDIR}\
    && chown -R dbmysql ${BAKDIR} ${BASEDIR} \
    && chmod +x /usr/bin/dbha

USER mysql
ENTRYPOINT ["/usr/bin/dbha"]
