### Description

Resource Import  
### Headers  
| Parameter Name     | Parameter Type     | Required   | Description             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | Yes     | application/json     |
| X-Bkapi-Authorization | dict | Yes | Contains bk_app_code, bk_app_secret, bk_username |

### Input Parameters  
| Parameter Name          | Parameter Type     | Required   | Description             |
| ----------------- | ------------ | ------ | ---------------- |
| for_biz           | int         | Yes     | Business identifier         |
| resource_type     | string      | Yes     | Resource type         |
| bk_biz_id         | int         | Yes     | Business ID           |
| hosts             | array       | Yes     | Host list         |
| labels            | array       | Yes     | Label list         |
| return_resource   | boolean     | Yes     | Whether to return resources     |
| os_type           | string      | Yes     | Operating system type     |
| label_names       | array       | Yes     | Label name list     |

### Call Example  
```python
curl -X 'POST' \
  'http://example.com/apis/dbresource/resource/import/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}' \
  -d '{
  "for_biz": 0,
  "resource_type": "string",
  "bk_biz_id": 3,
  "hosts": [
    {
      "ip": "string",
      "host_id": 0,
      "bk_cloud_id": 0,
      "status": "string",
      "city_name": "string",
      "sub_zone": "string",
      "rack_id": "string",
      "bk_os_name": "string",
      "svr_device_class": "string",
      "bk_cloud_name": "string"
    }
  ],
  "labels": [
    "string"
  ],
  "return_resource": true,
  "os_type": "1",
  "label_names": [
    "string"
  ]
}'
```

### Response Example  
```python
{
  "code": 0,
  "request_id": "string",
  "data": ""
}
```

### Response Parameter Description  
| Parameter Name     | Parameter Type   | Description                           |
| ------------ | ---------- | ------------------------------ |
| code         | int        | Response code                         |
| request_id   | string     | Request ID                         |
| data         | string     | Data                           |