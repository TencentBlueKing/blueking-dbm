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