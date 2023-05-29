# 介质初始化

## 从开发环境的制品库拉取制品库文件到本机

1. 配置制品库相关参数，将制品库指向开发环境的制品库
2. python manage.py download_bkrepo -o all

> 这里也支持指定存储类型拉取：python manage.py download_bkrepo -o download -p redis  
> 这里也支持指定存储类型解压：python manage.py download_bkrepo -o unzip -p redis  
> 制品库中文件过多时，可能会拉取失败，请提前清理无用的文件，比如key文件、sql文件等

## 从本机上传文件到目标环境的制品库

1. 配置制品库参数，将制品库指向目标制品库环境
2. 上传文件到目标制品库

> 全部上传： python manage.py upload_bkrepo   
> 指定db类型上传：python manage.py upload_bkrepo -p redis

## 同步制品库记录到saas数据库

前面两步需要在一台能同时访问到源制品库和目标制品库的主机执行，此步骤需要在saas生产环境执行：

```
python manage.py sync_from_bkrepo -t mysql
python manage.py sync_from_bkrepo -t redis
python manage.py sync_from_bkrepo -t es
python manage.py sync_from_bkrepo -t hdfs
python manage.py sync_from_bkrepo -t kafka
python manage.py sync_from_bkrepo -t pulsar
python manage.py sync_from_bkrepo -t influxdb
python manage.py sync_from_bkrepo -t cloud
```

该操作会按照制品库层级同步介质记录到Package模型表中
```
db_type
    pkg_type
        version
            media_file
```