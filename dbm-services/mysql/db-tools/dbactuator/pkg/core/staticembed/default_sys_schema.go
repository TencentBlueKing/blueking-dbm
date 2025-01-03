package staticembed

import "embed"

// DefaultSysSchemaSQLFileName TODO
const DefaultSysSchemaSQLFileName = "default_sys_schema.sql"
const GrantProcedureSQLFileName = "procedure.sql"

// DefaultSysSchemaSQL TODO
//
//go:embed default_sys_schema.sql
var DefaultSysSchemaSQL embed.FS

//go:embed procedure.sql
var ProcedureSQL embed.FS

// SpiderInitSQL TODO
const SpiderInitSQL = `CREATE TABLE if not exists infodba_schema.tscc_schema_checksum(
	db char(64) NOT NULL,
	tbl char(64) NOT NULL,
	status char(32) NOT NULL DEFAULT "" COMMENT "检查结果,一致:ok,不一致:inconsistent",
	checksum_result json COMMENT "差异表结构信息,tdbctl checksum table 的结果",
	update_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (db,tbl)
);`
