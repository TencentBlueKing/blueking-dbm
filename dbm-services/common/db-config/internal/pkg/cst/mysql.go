package cst

import "bk-dbconfig/pkg/constvar"

// common const variable
const (
	Default = "default"
	Master  = "master"
	Slave   = "slave"

	MySQLMaster        = "mysql_master"
	MySQLLogdb         = "mysql_logdb"
	MySQLSlave         = "mysql_slave"
	MySQLMasterSlave   = "mysql_master&mysql_slave"
	MySQLMasterOrSlave = "mysql_master|mysql_slave"
	SpiderMaster       = "spider_master"
	SpiderSlave        = "spider_slave"
	ProxyMaster        = "proxy_master"
	ProxyPairs         = "proxy_pairs"
	// ProxySlaveBak 后面废弃掉
	ProxySlaveBak = "proxy_slave_abandoned"

	Logdb        = "mysql_logdb"
	Tokudb       = "tokudb"
	Proxy        = "Proxy"
	MySQL        = "MySQL"
	Unlimit      = "unlimit"
	IDCCutLength = 2 // 前2个字为城市
	Linux        = "linux"
	Windows      = "windows"
	New          = "new"
	Null         = "NULL"
	NO           = "NO"
	// Dumper TODO
	// tbinlogdumper
	Dumper = "Dumper"
)

// isntance status
const (
	RUNNING      = "RUNNING"
	UNAVAILABLE  = "UNAVAILABLE"
	AVAIL        = "AVAIL"
	LOCKED       = "LOCKED"
	ALONE        = "ALONE"
	UNIQ_LOCK    = "UNIQ_LOCK"
	INITIALIZING = "INITIALIZING"
)

// proxy status
const (
	REFRESH_ONE = 1
	REFRESH_TWO = 2
)

// mysql switch type
const (
	AutoSwitch = "AutoSwitch" // 0
	HandSwitch = "HandSwitch" // 1
	NotSwitch  = "NotSwitch"  // 9
)

// tb_role_config
const (
	ConfigOn  = "on"
	ConfigOff = "off" // 这个不确定关闭就是 off
)

// DNS type
const (
	DNS_NOT_RELATED      = 0
	DNS_DIRECT_RELATED   = 1
	DNS_INDIRECT_RELATED = 2
)

// master
const (
	IsMaster    = 1
	IsNotMaster = 0
)

// switch
const (
	SwitchOn  = "on"
	SwitchOff = "off"
)

// disasterLevel
const (
	IDC        = "idc"
	City       = "city"
	DiffCampus = "DiffCampus"
	SameCampus = "SameCampus"
)

// config related
const (
	// MiscAttribute 猜测 miscellaneous  混杂的；各色各样混在一起；多才多艺的
	MiscAttribute                  = "misc"
	MySQLVersion                   = "mysqlversion"
	CheckDbdrEquipSwitch           = "check_dbdr_equip_switch"
	CheckDbdrSvrType               = "check_dbdr_svr_type"
	CheckDbdrRaidType              = "check_dbdr_raid_type"
	CheckDbdrLinkNetdeviceIDSwitch = "check_dbdr_LinkNetdeviceId_switch"
	PubBKBizID                     = constvar.LevelPlat
	ConfigRole                     = "config"
	GamedbRole                     = "gamedb"
)

// number
const (
	ZERO = 0
	ONE  = 1
)

// LeastTokuVersion TODO
const LeastTokuVersion = "TMySQL-2.1.0"

// intall mysql check item
const (
	CheckTokudb  = "check tokudb"
	CheckSuccess = "OK"
	CheckFail    = "FAIL"
	CheckPass    = "PASS"
)

const (
	// OneChance TODO
	OneChance = 1
)

// uninstallOption
const (
	CancelOwn           = 1
	ClearAndBackup      = 2
	ForceClearAndBackup = 3
	ForceClearAll       = 4
)
