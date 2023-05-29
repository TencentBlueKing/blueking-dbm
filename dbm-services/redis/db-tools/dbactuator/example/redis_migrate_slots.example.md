### tendisplus migrate slot
迁移slots:
```
原始payload
示例1:
```
```

{
    "src_node": {
		"ip": "127.0.0.1",
		"port":40000,
        "password": "redisPassTest"
	},
    "dst_node": {
		"ip": "127.0.0.1",
		"port":45100,
        "password": "redisPassTest"
	},
	"migrate_specified_slot":true, 
	"slots":"0-100"

}
```
```
原始payload
示例2:
{
    "src_node": {
		"ip": "127.0.0.1",
		"port":40000,
        "password": "redisPassTest"
	},
    "dst_node": {
		"ip": "127.0.0.1",
		"port":45100,
        "password": "redisPassTest"
	},
	"migrate_specified_slot":false, 
	"slots":"0-100"

}
```
