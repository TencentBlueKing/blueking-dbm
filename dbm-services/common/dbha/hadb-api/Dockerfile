FROM mirrors.tencent.com/sccmsp/golang:1.16
MAINTAINER hadb-api Development

ARG BASEDIR=/home/hadb

RUN mkdir ${BASEDIR}

COPY hadb-api ${BASEDIR}/

RUN groupadd -r dbmysql && useradd -r -g dbmysql dbmysql \
    && /usr/bin/install -m 0777 -o dbmysql -g root -d ${BASEDIR}\
    && chown -R dbmysql ${BASEDIR} \
    && chmod a+x ${BASEDIR}/hadb-api \
    && chmod a+x ${BASEDIR}

USER mysql

WORKDIR ${BASEDIR}

ENTRYPOINT ["/home/hadb/hadb-api"]
