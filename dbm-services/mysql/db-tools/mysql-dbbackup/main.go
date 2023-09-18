package main

import (
	"dbm-services/mysql/db-tools/mysql-dbbackup/cmd"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

func main() {
	logger.InitLog()
	cmd.Execute()
}
