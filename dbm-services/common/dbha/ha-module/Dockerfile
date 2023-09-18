FROM centos:7
MAINTAINER TenDB-New-DBHA Development

ARG BASEDIR=/home/mysql/dbha

COPY dbha /usr/bin/

RUN groupadd -r mysql && useradd -r -g mysql mysql \
    && /usr/bin/install -m 0775 -o mysql -g root -d ${BASEDIR}\
    && chown -R mysql ${BAKDIR} ${BASEDIR} \
    && chmod +x /usr/bin/dbha

USER mysql
ENTRYPOINT ["/usr/bin/dbha"]
