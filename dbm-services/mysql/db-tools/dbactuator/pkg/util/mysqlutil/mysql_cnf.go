package mysqlutil

import (
	"gopkg.in/ini.v1"
)

// MysqlCnfFile my.cnf 配置ini 解析
type MysqlCnfFile struct {
	FileName string
	Cfg      *ini.File
}

// MycnfObject TODO
type MycnfObject struct {
	Client    map[string]string `json:"client" sectag:"client"`
	Mysql     map[string]string `json:"mysql"  sectag:"mysql"`
	Mysqld    map[string]string `json:"mysqld" sectag:"mysqld"`
	Mysqldump map[string]string `json:"mysqldump" sectag:"mysqldump"`
	Mysqld55  map[string]string `json:"mysqld-5.5" sectag:"mysqld-5.5"`
	Mysqld56  map[string]string `json:"mysqld-5.6" sectag:"mysqld-5.6"`
	Mysqld57  map[string]string `json:"mysqld-5.7" sectag:"mysqld-5.7"`
	Mysqld80  map[string]string `json:"mysqld-8.0" sectag:"mysqld-8.0"`
}
