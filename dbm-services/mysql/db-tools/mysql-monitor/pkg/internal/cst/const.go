package cst

import "fmt"

const (
	// DBASchema TODO
	DBASchema = "infodba_schema"
	// DBAReportBase TODO
	DBAReportBase = "/home/mysql/dbareport"
	// SystemUser replication thread user name
	SystemUser = "system user"
)

const (
	OTHER_DB_NAME    = "_OTHER_"
	OTHER_TABLE_NAME = "_OTHER_"
)

var OTHER_DB_TABLE_NAME = fmt.Sprintf("%s.%s", OTHER_DB_NAME, OTHER_TABLE_NAME)
