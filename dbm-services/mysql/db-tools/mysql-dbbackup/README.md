# dbbackup-go

## BUILD
### package
```
// 产出 dbbackup-go-community.tar.gz # 只含 community 依赖
make package VERSION=1.0.0 DIST=community
make package VERSION=1.0.0 DIST=community STAGE=alpha


// 产出 dbbackup-go-txsql.tar.gz # 只含 txsql 依赖
make package VERSION=1.0.0 DIST=txsql

// 产出 dbbackup-go-universal.tar.gz , 同时包含 community 和 txsql 的备份依赖
make package VERSION=1.0.0 DIST=universal
make package VERSION=1.0.0 DIST=universal STAGE=alpha

// 产出 dbbackup-go.tar.gz # 只含 community 依赖
make universal VERSION=1.0.0 DIST=community

// 产出 dbbackup-go.tar.gz # 只含 txsql 依赖
make universal VERSION=1.0.0 DIST=txsql

// 产出 dbbackup-go.tar.gz # 合并 community+txsql 依赖
// 与 dbbackup-go-universal.tar.gz 内容相同，只是包名不同
make universal VERSION=1.0.0 DIST=all        

```

### compile
```
go build src/dbbackup.go
```

or make package

```
sh build.sh
```

### USAGE
dump backup
```
./dbbackup dumpbackup -c test.20000.ini
```

load backup
```
./dbbackup loadbackup -c test.20000.ini
```


##  使用原生 mydumper/myloader 或 xtrabackup
```
source bin/export.sh
```
