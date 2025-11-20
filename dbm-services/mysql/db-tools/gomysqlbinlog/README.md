# gomysqlbinlog binlog解析工具
golang版本的可以实现 mysqlbinlog 同样的解析输出效果，但具备更强的库表过滤，记录过滤功能。

目前主要用 `gomysqlbinlog --flashback` 实现 binlog 反转来逆向闪回。

特点：
- 闪回功能，不需要将 binlog 转成 sql，而是直接将 rows_event 二进制内容进行反转
- 完全兼容所有版本(>= mysql-5.5) 的binlog
- 可按照 databases,tables 做 rows_event 库表变更记录的过滤
- 可按照 rows_event类型(insert,update,delete) 过滤
- 可按照 rows_event 里面指定字段值来过滤部分行
- binlog 离线解析，离线反转。不需要提供 schema 或者连接 mysqld
- 因为是对二进制内容进行反转/过滤，所以不会存在特殊字符集导致转 sql 形式意外问题。解析和导入速度也比转 sql 快
- binlog 反转时，即使单个 binlog 非常大，不会造成内存使用过多
- binlog 过滤/反转时，如果遇到对应的表有 ddl 操作，会提示异常

## build
```
cd go-mysql/cmd/go-binlogparser
go build  -o gomysqlbinlog
```

## gomysqlbinlog

```
./gomysqlbinlog -h
gomysqlbinlog replace mysqlbinlog

Usage:
  gomysqlbinlog [flags]

Flags:
  -c, --autocommit                      set auto_commit=1 to output (default true)
      --binlog-dir string               binlog dir
      --binlog-row-event-max-size int   binlog-row-event-max-size
      --conv-rows-update-to-write       change update event to write
  -B, --databases strings               databases
      --disable-foreign-key-checks      set session foreign_key_checks=0
      --disable-log-bin                 disable sql_log_bin
      --exclude-databases strings       exclude databases
      --exclude-tables strings          exclude tables
  -f, --file strings                    binlog file name
      --flashback                       flashback
      --help                            help for this command
  -i, --idempotent                      idempotent mode
      --log-dir string                  log file path. default empty will log files to dir dbbackup/logs/
      --parallel-type string            database | table | database_hash | table_hash | key_hash (default "mysqlbinlog")
  -r, --result-file string              Direct output to a given file
      --result-file-max-size-mb int     result-file-max-size-mb (default 128)
      --rewrite-db strings              Rewrite the row event to point so that it can be applied to a new database
      --rows-event-type strings         insert,update,delete
      --rows-filter string              col[0] == 'abc'
      --rows-filter-from-csv string     file csv format like:col[0],col[1]
                                        xxx,100
                                        yyy,200
      --server-id int                   Extract only binlog entries created by the server having the given id
      --set-charset string              Add 'SET NAMES character_set' to the output, | utf8 | utf8mb4 | latin1 | gbk
  -s, --short                           short will not print un-matched event header (default true)
      --start-datetime string           start datetime
      --start-file string               binlog start file name
      --start-position int              start position for --file or --start-file (default 4)
      --stop-datetime string            stop datetime
      --stop-file string                binlog stop file name
      --stop-position int               stop position for --file or --stop-file
  -T, --tables strings                  tables
      --threads int                     parse binlog threads (default 1)
  -v, --verbose int                     verbose, 0, 1, 2
      --version                         version for gomysqlbinlog
```

## gomysqlbinlog 正向过滤
```
# 过滤 db1.tb1 的 binlog 变更记录
./gomysqlbinlog -v 1 --databases db1 --tables tb1 -f binlog.00002

# 也可以指定 %, * 这样的模式匹配
# * 只能单独使用，标识所有，%必须结合其它字符串使用
./gomysqlbinlog -v 1 --databases db1,table% --tables '*' -f binlog.00002 \
  --idempotent --rows-filter "col[0] == 'abc'"
```

`col[0]` 代表表的第一个字段，一般闪回某条记录时，指定的表是同一类表，更广泛一点说，指定的过滤字段代表相同的 字段名，不然过滤可能无意义。

rows-filter 过滤有两种方式：
- csv:  `--rows-filter-from-csv`  
  csv表头，多行值等值比较
  ```
  col[0],col[1]
  xxx,100
  yyy,200
  ```

- expr: `--rows-filter`
  表达式：https://expr-lang.org/docs/language-definition#operators
  ```
  col[0] == 'aaa' and col[1] > 100
  ```

## gomysqlbinlog flashback 闪回
```
./gomysqlbinlog -v 1 --flashback --databases db1 --tables tb1 -f binlog.00002 -r binlog.00002.back.sql

./gomysqlbinlog -v 1 --flashback --databases db1 --tables tb1,tb2 -f binlog.00002 \
  --start-datetime '2025-06-27 14:00:01' --stop-datetime '2025-06-28 14:00:01'
  --idempotent --rows-filter "col[0] == 'abc'"
  -r binlog.00002.back.sql
```

### 逆向示例：

```
./gomysqlbinlog --flashback --databases test --tables 'xiaogtest1' -v 1 -f  binlog.000013
```

原 binlog 内容：
```
#250729 18:04:24 server id 81482679  end_log_pos 2857 CRC32 0xc7c1c14c  Delete_rows: table id 2690 flags: STMT_END_F

BINLOG '
qJyIaBO3U9sERwAAAMgKAAAAAIIKAAAAAAEABHRlc3QACnhpYW9ndGVzdDEACQMPDwj8/BIRBAke
AB4AAgIAAAT8ABjtT6c=
qJyIaCC3U9sEYQAAACkLAAAAAIIKAAAAAAEAAgAJ//8A/gQAAAAEY2NjYwQzMzMzMHUAAAAAAAAK
AGNjY2NjY2NjY2MKAGNjY2NjY2NjY2OZtzsebGiImxjNVFBFTMHBxw==
'/*!*/;
### DELETE FROM `test`.`xiaogtest1`
### WHERE
###   @1=4 /* INT meta=0 nullable=0 is_null=0 */
###   @2='cccc' /* VARSTRING(30) meta=30 nullable=0 is_null=0 */
###   @3='3333' /* VARSTRING(30) meta=30 nullable=1 is_null=0 */
...
# at 2857
```

逆向之后变成：
```
BINLOG '
qJyIaBO3U9sERwAAAMgKAAAAAIIKAAAAAAEABHRlc3QACnhpYW9ndGVzdDEACQMPDwj8/BIRBAke
AB4AAgIAAAT8ABjtT6c=
qJyIaB63U9sEYQAAACkLAAAAAIIKAAAAAAEAAgAJ//8A/gQAAAAEY2NjYwQzMzMzMHUAAAAAAAAK
AGNjY2NjY2NjY2MKAGNjY2NjY2NjY2OZtzsebGiImxjNVFBF8YTdFw==
'/*!*/;
### INSERT INTO `test`.`xiaogtest1`
### SET
###   col[0]=4
###   col[1]='cccc'
###   col[2]='3333'
...
```

如果有多个 binlog 需要反转，解析的文件结果，需要反向导入到 mysql

### 过滤示例

```
./gomysqlbinlog  --databases test --tables 'xiaogtest1' --rows-filter="col[1]=='bbbb'" -v 2 -f binlog.000013
```

原始 binlog内容：
```
BINLOG '
apuIaBO3U9sERwAAAEMGAAAAAIMKAAAAAAEABHRlc3QACnhpYW9ndGVzdDIACQMPDwj8/BIRBAl4
AHgAAgIAAAT8AKlelk8=
apuIaB63U9sEGAEAAFsHAAAAAIMKAAAAAAEAAgAJ//8A/gIAAAAEYWFhYQQxMTExECcAAAAAAAAK
AGFhYWFhYWFhYWEKAGFhYWFhYWFhYWGZtzsexmiIm2oz44pEAP4DAAAABGJiYmIEMjIyMiBOAAAA
AAAACgBiYmJiYmJiYmJiCgBiYmJiYmJiYmJimbc7HsZoiJtqM+MKRQD+BAAAAARjY2NjBDMzMzMw
dQAAAAAAAAoAY2NjY2NjY2NjYwoAY2NjY2NjY2NjY5m3Ox7GaIibas1UUEUA/gUAAAAEZGRkZAQ0
NDQ0QJwAAAAAAAAKAGRkZGRkZGRkZGQKAGRkZGRkZGRkZGSZtzsexmiIm2oz44pFIwMLyA==
'/*!*/;
### INSERT INTO `test`.`xiaogtest2`
### SET
###   @1=2 /* INT meta=0 nullable=0 is_null=0 */
###   @2='aaaa' /* VARSTRING(120) meta=120 nullable=0 is_null=0 */
###   @3='1111' /* VARSTRING(120) meta=120 nullable=1 is_null=0 */
...
### INSERT INTO `test`.`xiaogtest2`
### SET
###   @1=3 /* INT meta=0 nullable=0 is_null=0 */
###   @2='bbbb' /* VARSTRING(120) meta=120 nullable=0 is_null=0 */
###   @3='2222' /* VARSTRING(120) meta=120 nullable=1 is_null=0 */
...
### INSERT INTO `test`.`xiaogtest2`
### SET
###   @1=4 /* INT meta=0 nullable=0 is_null=0 */
###   @2='cccc' /* VARSTRING(120) meta=120 nullable=0 is_null=0 */
###   @3='3333' /* VARSTRING(120) meta=120 nullable=1 is_null=0 */
...
### INSERT INTO `test`.`xiaogtest2`
### SET
###   @1=5 /* INT meta=0 nullable=0 is_null=0 */
###   @2='dddd' /* VARSTRING(120) meta=120 nullable=0 is_null=0 */
###   @3='4444' /* VARSTRING(120) meta=120 nullable=1 is_null=0 */
...
```

过滤后 binlog:
```
# Timestamp=2025-07-29 17:57:44 ServerId=81482679 EventType=WriteRowsEventV2 EndLogPos=1012 Db=test Table=xiaogtest1 TableID=2690 Rows=1/4
BEGIN/*!*/;

BINLOG '
GJuIaBO3U9sERwAAANwCAAAAAIIKAAAAAAEABHRlc3QACnhpYW9ndGVzdDEACQMPDwj8/BIRBAke
AB4AAgIAAAT8AI/xEQQ=
GJuIaB63U9sEYQAAAPQDAAAAAIIKAAAAAAEAAgAJ//8A/gMAAAAEYmJiYgQyMjIyIE4AAAAAAAAK
AGJiYmJiYmJiYmIKAGJiYmJiYmJiYmKZtzsebGiImxgz4wpFudHSMQ==
'/*!*/;
### INSERT INTO `test`.`xiaogtest1`
### SET
###   col[0]=3 /* INT false */
###   col[1]='bbbb' /* VARSTRING(30) false */
###   col[2]='2222' /* VARSTRING(30) false */
...
COMMIT/*!*/;
```

## TODO
- [ ] add unit test
- [ ] print rows num matched
- [ ] rows changed stats