package mysql

import (
	"dbm-services/common/dbha/ha-module/config"
)

// MySQLProxyDetectInstance defined proxy detect info
type MySQLProxyDetectInstance struct {
	MySQLDetectInstance
}

// MySQLProxyDetectResponse defined proxy response struct
type MySQLProxyDetectResponse struct {
	MySQLDetectResponse
}

// MySQLProxyDetectInstanceInfoFromCmDB defined proxy detect info in cmdb
type MySQLProxyDetectInstanceInfoFromCmDB struct {
	MySQLDetectInstanceInfoFromCmDB
}

// NewMySQLProxyDetectInstance1 return detect info in cmdb
func NewMySQLProxyDetectInstance1(ins *MySQLProxyDetectInstanceInfoFromCmDB,
	conf *config.Config) *MySQLProxyDetectInstance {
	return &MySQLProxyDetectInstance{
		MySQLDetectInstance: *NewMySQLDetectInstance1(&ins.MySQLDetectInstanceInfoFromCmDB,
			conf),
	}
}

// NewMySQLProxyDetectInstance2 return detect info by agent report
func NewMySQLProxyDetectInstance2(ins *MySQLProxyDetectResponse, dbType string,
	conf *config.Config) *MySQLProxyDetectInstance {
	return &MySQLProxyDetectInstance{
		MySQLDetectInstance: *NewMySQLDetectInstance2(&ins.MySQLDetectResponse, dbType, conf),
	}
}
