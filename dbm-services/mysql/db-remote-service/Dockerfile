FROM mirrors.tencent.com/sccmsp/tmysqlparse:3.0.7

ADD build/db-remote-service /
ADD https://downloads.mongodb.com/compass/mongosh-1.10.6-linux-x64.tgz /
ADD https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-rhel70-4.2.19.tgz /
RUN tar zxf /mongodb-linux-x86_64-rhel70-4.2.19.tgz && tar zxf /mongosh-1.10.6-linux-x64.tgz
RUN cp /mongosh-1.10.6-linux-x64/bin/mongosh /usr/local/bin/ && \
    cp /mongodb-linux-x86_64-rhel70-4.2.19/bin/mongo /usr/local/bin/ && \
    chmod +x /usr/local/bin/mongosh && \
    chmod +x /usr/local/bin/mongo && \
    rm -rf /mongosh-1.10.6-linux-x64 /mongodb-linux-x86_64-rhel70-4.2.19

WORKDIR /
ENTRYPOINT ["/db-remote-service"]