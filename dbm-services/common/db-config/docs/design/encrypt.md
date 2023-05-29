# 密码加密
加密
```
curl --location --request POST 'http://bkdbm-dbconfig/bkconfig/v1/conffile/update' \
-d '{   
    "req_type": "SaveAndPublish",
    "conf_names": [
        {
            "conf_name": "xx",
            "value_default": "xxx",
            "op_type": "update",
            "value_type":"STRING"
        }
    ],
    "confirm": 0,
    "conf_file_info": {
        "namespace": "aaa",
        "conf_type": "bbb",
        "conf_file": "ccc"
    }
}'
```

查询：
```
curl --location --request POST 'http://bkdbm-dbconfig/bkconfig/v1/confitem/query' \
--header 'Content-Type: application/json' \
-d '{
    "bk_biz_id": "0",
    "level_name": "plat",
    "level_value": "0",
    "conf_file": "ccc",
    "conf_type": "bbb",
    "namespace": "aaa",
    "format": "map",
    "conf_name": "xx"
}'
```

# 修改加密 key
修改加密秘钥，一定要备份之前的秘钥和已生成的加密串（包括平台默认和业务密码），一旦秘钥丢失将无法拿到明文。
## 平台默认密码
```
### 用旧key来解密出明文密码
./bkconfigcli query --decrypt --old-key="xx"
./bkconfigcli query --decrypt --namespace=influxdb --old-key="xx"

### 修改key
./bkconfigcli update  --old-key="xx" --new-key="xxxx"
./bkconfigcli update  --namespace=influxdb --old-key="xx" --new-key="xxxx"
```

## 业务或者集群默认密码

```
### 查询某个业务所有相关密码
./bkconfigcli query --decrypt --old-key="xx" --bk-biz-id=123

### 用新key更新 业务 123 的相关密码，可用于先验证是否正确
./bkconfigcli update  --old-key="xx" --new-key="xxxx" --bk-biz-id=123

### 用新key更新所有业务的相关密码
./bkconfigcli update  --old-key="xx" --new-key="xxxx" --bk-biz-id=-1
```