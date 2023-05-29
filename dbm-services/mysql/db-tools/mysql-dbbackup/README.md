# dbbackup-go

### BUILD
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
