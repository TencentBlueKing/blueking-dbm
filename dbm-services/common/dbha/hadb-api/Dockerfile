FROM mirrors.tencent.com/sccmsp/golang:1.16
MAINTAINER hadb-api Development

ARG BASEDIR=/home/hadb

RUN mkdir ${BASEDIR}

COPY build/hadb-api ${BASEDIR}/

RUN groupadd -r mysql && useradd -r -g mysql mysql \
    && /usr/bin/install -m 0777 -o mysql -g root -d ${BASEDIR}\
    && chown -R mysql ${BASEDIR} \
    && chmod a+x ${BASEDIR}/hadb-api \
    && chmod a+x ${BASEDIR}

USER mysql

WORKDIR ${BASEDIR}

ENTRYPOINT ["/home/hadb/hadb-api"]
