### mongo_execute_script
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="mongo_execute_script"  --payload='{{payload_base64}}'
```


原始payload

# 原始payload
```json
{
  "ip":"1.1.1.1",
  "port":27021,
  "script":"xxx",
  "type":"cluster",
  "secondary": false,
  "scriptName": "xxx",
  "adminUsername":"xxx",
  "adminPassword":"xxxxxx",
  "repoUrl":"url",
  "repoUsername":"username",
  "repoToken":"token",
  "repoProject":"project",
  "repoRepo":"project-package",
  "repoPath":"path"
}
```

"script" 为JavaScript脚本内容

"scriptName" 为脚本名称

"secondary" 为true时,表示在secondary节点执行；为false时，表示在primary节点执行

以repo为前缀的字段为制品库信息