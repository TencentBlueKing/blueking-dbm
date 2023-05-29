FROM golang:1.19

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo "Asia/Shanghai" > /etc/timezone

ADD conf /conf/
ADD bkconfigsvr /

WORKDIR /
CMD /bkconfigsvr