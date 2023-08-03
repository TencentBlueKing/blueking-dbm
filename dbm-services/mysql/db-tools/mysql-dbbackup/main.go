package main

import (
	"dbm-services/mysql/db-tools/mysql-dbbackup/cmd"
)

func main() {
	//logger.InitLog("")
	// logger 在子 command 里面设置，不同的日志名
	cmd.Execute()
}
