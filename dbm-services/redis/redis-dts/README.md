## redis-dts

### 简介
redis数据传输服务.

### 使用说明
- 申请一台`Tlinux 2.2+`机器作为`DTS server`;
- `DTS server`配置DNS,配置地址;
- 程序本地执行`make build`;
- 将`redis-dts`目录打包传输到`DTS server`上,建议`/data1/dbbak`目录下;
- `DTS server`上执行`cd /data1/dbbak/redis-dts && sh start.sh`;
- 源`TendisSSD`集群必须支持参数`slave-log-keep-count`,建议版本:`2.8.17-TRedis-v1.2.20`、`2.8.17-TRedis-v1.3.10`;

### 原理简介
#### 架构图
![redis-dts架构图](./images/redis-dts%E6%9E%B6%E6%9E%84%E5%9B%BE.png)