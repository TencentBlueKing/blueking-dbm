package dbbackup

const (
	// ReSplitPart physical.part_0
	ReSplitPart = `(.+)(\.part_\d+)`
	// ReTarPart xxxx_logical_0.tar physical.tar
	// ReTarPart = `(.+)_(\d+)\.tar`
	ReTarPart = `(.+)\.tar$`
)

const (
	// MYSQL_FULL_BACKUP TODO
	MYSQL_FULL_BACKUP string = "full"
	// INCREMENT_BACKUP TODO
	INCREMENT_BACKUP string = "incr"
	// MYSQL_PRIV_FILE TODO
	MYSQL_PRIV_FILE string = "priv"
	// MYSQL_INFO_FILE TODO
	MYSQL_INFO_FILE string = "info"
	// BACKUP_INDEX_FILE TODO
	BACKUP_INDEX_FILE string = "index"
)

const (
	// DBRoleMaster TODO
	DBRoleMaster = "Master"
	// DBRoleSlave TODO
	DBRoleSlave = "Slave"
	// DBRoleRelay TODO
	DBRoleRelay = "Relay" // 中继节点

)
