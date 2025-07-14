
```
./dbevent-report --cluster-type tendbha --event-name "xiaogtest1" --bk-biz-id 1 --event-body '{
    "code": 401,
    "message": "invalid param",
    "data": ""
}'

./dbevent-report --cluster-type tendbha --event-name "xiaogtest1" --bk-biz-id 1 --event-body '
[
    {
        "code": 401,
        "message": "invalid param",
        "data": ""
    },
    {
        "code": 200,
        "message": "",
        "data": "{}"
    }
]'
```