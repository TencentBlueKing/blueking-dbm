
# 恢复备份数据
如果明确知道备份类型是 logical 还是 physical，可以用子命令形式：
### 逻辑备份 恢复：
```
./dbbackup loadbackup logical --help
logical load data dumped using mydumper or mysqldump

Usage:
  dbbackup loadbackup logical [flags]

Flags:
      --charset string             User password, overwrite LogicalLoad.MysqlCharset
  -B, --databases string           Database to dump, default all
      --databases-drop string      database list to drop, overwrite LogicalLoad.DBListDropIfExists
      --enable-binlog              overwrite LogicalLoad.EnableBinlog
      --exclude-databases string   databases to dump, comma separated, default empty
      --exclude-tables string      tables to dump, comma separated, default empty
  -h, --host string                The host to connect to, overwrite LogicalLoad.MysqlHost (default "localhost")
  -p, --password string            User password, overwrite LogicalLoad.MysqlPasswd
  -P, --port int                   TCP/IP port to connect to, overwrite LogicalLoad.MysqlPort (default 3306)
  -x, --regex string               Regular expression for 'db.table' matching
      --tables string              tables to dump, comma separated, default all
  -T, --tables-list string         Comma delimited table list to dump (does not exclude regex option). Table name must include database name. For instance: test.t1,test.t2
  -u, --user string                Username with the necessary privileges, overwrite LogicalLoad.MysqlUser

Global Flags:
  -c, --config string            one config file to load. logical backup need connect string given
      --help                     help for this command
      --load-dir string          backup root path to save, overwrite LogicalLoad.MysqlLoadDir
  -i, --load-index-file string   backup index file, overwrite LogicalLoad.IndexFilePath, PhysicalLoad.IndexFilePath
      --log-dir string           log file path. default empty will log files to dir dbbackup/logs/
      --threads int              threads for myloader or xtrabackup, default 8 (default 8)
```

示例：
```
./dbbackup loadbackup logical \
 --load-dir /data/dbbak/xx_xx_xxxxxx_logical \
 -i /data/dbbak/xx_xx_xxxxxx_logical.index \
 --host x.x.x.x --port 3306 -u xxx -p xxx
 
./dbbackup loadbackup logical --config loader_xxx.ini
```

如果是 mydumper 备份出的文件，还可以通过 `--databases` 等选项控制导入的数据。mysqldump 导出的数据 使用 `--databases` 则会提示错误。

逻辑备份导入 `loadbackup logical` 是不需要指定字符集，dbbackup 会自动使用导出后备份文件里面的 charset (即 .index 里面的 backup_charset ) 

### 物理备份 恢复:
```
./dbbackup loadbackup physical --help
physical recover using xtrabackup

Usage:
  dbbackup loadbackup physical [flags]

Flags:
      --copy-back              tables to dump, comma separated, default all
      --defaults-file string   Database to dump, default all

Global Flags:
  -c, --config string            one config file to load. logical backup need connect string given
      --help                     help for this command
      --load-dir string          backup root path to save, overwrite LogicalLoad.MysqlLoadDir
  -i, --load-index-file string   backup index file, overwrite LogicalLoad.IndexFilePath, PhysicalLoad.IndexFilePath
      --threads int              threads for myloader or xtrabackup, default CPU Cores
```

示例：
```
./dbbackup loadbackup physical \
 --load-dir /data/dbbak/xx_xx_xxxxxx_logical \
 -i /data/dbbak/xx_xx_xxxxxx_logical.index \
 --defaults-file /etc/my.cnf.3306
 
./dbbackup loadbackup physical -c loader_xxx.ini

```

### 也可以不指定子命令，不关心备份文件类型
```
./dbbackup loadbackup -c loader_xxx.ini
```

1. 下载备份
2. 解压备份
  如果文件有切分，先合并 `cat xx_xx.part_0, xx_xx.part_1 |tar -xf - -C /data/dbbak/`
  记下解压后的数据目录，比如  /data/dbbak/xx_xx_x.x.x.x_xxxxxx_logical
3. 准备配置文件 loader_xxx.ini  
IndexFilePath: 备份的元数据文件(后缀 .index)所在目录  
MysqlLoadDir: 解压后的数据目录，绝对路径  
```
[LogicalLoad]
MysqlLoadDir    =       /data/dbbak/your_loader_dir
IndexFilePath   =       /data/dbbak/xxxxx
MysqlHost       =       
MysqlPort       =       0
MysqlUser       =       
MysqlPasswd     =       
MysqlCharset    =       binary
Threads =       8
CreateTableIfNotExists  =       false
DBListDropIfExists      =       
EnableBinlog    =       false
ExtraOpt        =
Regex   =       
Databases = 
ExcludeDatabases = 

[PhysicalLoad]
MysqlLoadDir    =       /xx/loader_dir
IndexFilePath   =       /xx/xxx.index
DefaultsFile    =       /etc/my.cnf
CopyBack        =       false
Threads =       2
ExtraOpt        =       
```
3. 全库恢复，确认目标库是空库
4. 执行恢复

逻辑备份导入时默认不开启 binlog，如需开启，可以设置 `LogicalBackup.EnableBinlog = true`