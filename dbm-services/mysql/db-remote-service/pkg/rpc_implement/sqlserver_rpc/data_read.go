package sqlserver_rpc

import "dbm-services/mysql/db-remote-service/pkg/config"

// SqlserverDataReadRPCEmbed 业务数据只读角色.
//
// 注意: Go 的 struct embedding 不是继承, IsQueryCommand / IsExecuteCommand
// 定义在基类 SqlserverRPCEmbed 上, 内部调用的 InitQueryParseCommands /
// InitExecuteParseCommands 永远是基类版本, 子结构体覆写不会生效.
// 因此这里不再覆写白名单, 只读语义通过 User()/Password() 走低权限账号来保证.
type SqlserverDataReadRPCEmbed struct {
	SqlserverRPCEmbed
}

func (s *SqlserverDataReadRPCEmbed) User() string {
	return config.RuntimeConfig.SqlserverDataReadUser
}

func (s *SqlserverDataReadRPCEmbed) Password() string {
	return config.RuntimeConfig.SqlserverDataReadPassword
}
