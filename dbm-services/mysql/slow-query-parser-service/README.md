1. 命令行启动看 help
2. 容器启动 docker run -d --name test-parser -p 22222:22222 -e SQ_ADDRESS=0.0.0.0:22222 -e SQ_TMYSQLPARSER_BIN=/tmysqlparse ${THIS_IMAGE}

会优先使用 tidb sql parser 来解析 sql 里面的库表名，sql 类型，计算指纹。

如果 sql 非法（比如被异常截断），会使用 percona go-mysql lib 的来解析，它使用正则来计算 finger-print。


## 测试
```
./build/slow-query-parser-service run --address 127.0.0.1:8087


curl -XPOST http://127.0.0.1:8087/mysql/ -d '{"content":"select sleep(2)", "db":"test"}'
```