
1. 下载备份
2. 解压备份
  如果文件有切分，先合并 `cat xx_xx.part_0, xx_xx.part_1 |tar -xf - -C /data/dbbak/`
  记下解压后的数据目录，比如  /data/dbbak/xx_xx_x.x.x.x_xxxxxx_logical
3. 准备配置文件 loader_xxx.ini
IndexFilePath: 备份的元数据文件(后缀 .index)所在目录
MysqlLoadDir: 解压后的数据目录，绝对路径
```
[LogicalLoad]
MysqlHost       =       
MysqlPort       =       0
MysqlPasswd     =       
MysqlUser       =       
MysqlCharset    =       binary
MysqlLoadDir    =       /data/dbbak/your_loader_dir
IndexFilePath   =       /data/dbbak/xxxxx
Regex   =       
Threads =       8
CreateTableIfNotExists  =       false
DBListDropIfExists      =       
EnableBinlog    =       false
ExtraOpt        =

[PhysicalLoad]
CopyBack        =       false
DefaultsFile    =       /etc/my.cnf
ExtraOpt        =       
IndexFilePath   =       /xx/xxx.index
MysqlLoadDir    =       /xx/loader_dir
Threads =       2
```
3. 确认目标库是空库
4. 执行恢复
```
./dbbackup loadbackup -c loader_xxx.ini
```