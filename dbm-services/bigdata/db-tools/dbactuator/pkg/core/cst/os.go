package cst

// status
const (
	Unknown      = "unknown"
	RUNNING      = "RUNNING"
	UNAVAILABLE  = "UNAVAILABLE"
	AVAIL        = "AVAIL"
	LOCKED       = "LOCKED"
	ALONE        = "ALONE"
	UNIQ_LOCK    = "UNIQ_LOCK"
	INITIALIZING = "INITIALIZING"
	NULL         = "NULL"
)

const (
	// Default TODO
	Default = "default"
)

// db role
const (
	MySQLMaster        = "mysql_master"
	MySQLLogDB         = "mysql_logdb"
	MySQLSlave         = "mysql_slave"
	MySQLMasterSlave   = "mysql_master&mysql_slave"
	MySQLMasterOrSlave = "mysql_master/mysql_slave"
	ProxyMaster        = "proxy_master"
	ProxySlave         = "proxy_slave"
	ProxyMasterSlave   = "proxy_master&proxy_slave"
)

// db Category(dbtype) 和 job 的 gamedb gamedr 是两个东西。
const (
	Logdb  = "logdb"
	MySQL  = "MySQL"
	Proxy  = "Proxy"
	Spider = "Spider"
	Dumper = "Dumper"
)

// switch type
const (
	AutoSwitch = "AutoSwitch"
	HandSwitch = "HandSwitch"
	NotSwitch  = "NotSwitch"
)

// switch weight
const (
	SwitchWeight0   = "0"
	SwitchWeight1   = "1"
	SwitchWeight100 = "100"
)

// os type
const (
	RedHat    = "redhat"
	Suse      = "suse"
	Slackware = "slackware"
)

// bits
const (
	Bit64  = "64"
	Bit32  = "32"
	OSBits = 32 << uintptr(^uintptr(0)>>63)
)

// switch
const (
	ON  = "ON"
	OFF = "OFF"
)

// dbmstype
const (
	MySQLCluster = "mysql_cluster"
	MySQLSingle  = "mysql_single"
)

// disasterLevel
const (
	IDC        = "IDC"
	City       = "CITY"
	DiffCampus = "DiffCampus"
	SameCampus = "SameCampus"
)

// etcd finished key value
const (
	Success = "success"
	Failed  = "failed"
)
