# bk-dbha-api
bk-dbha-api提供一系列api方便bk-dbha组件访问高可用相关数据库。包括日常切换状态的访问，心跳上报，切换日志等

## 要求
go1.14+

## 编译
```bash
go build -o hadb main.go
```

## 运行
./hadb run port:8090