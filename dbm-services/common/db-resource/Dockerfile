FROM mirrors.tencent.com/bcs/golang:1.23

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo "Asia/Shanghai" > /etc/timezone

ADD db-resource /
WORKDIR /
CMD /db-resource