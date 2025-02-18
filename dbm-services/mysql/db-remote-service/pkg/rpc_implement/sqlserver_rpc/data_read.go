package sqlserver_rpc

import "dbm-services/mysql/db-remote-service/pkg/config"

type SqlserverDataReadRPCEmbed struct {
	SqlserverRPCEmbed
}

// InitQueryParseCommands 定义可以支持查询语句的结构
func (s *SqlserverDataReadRPCEmbed) InitQueryParseCommands() []string {
	return []string{
		"show",
		"select",
	}
}

// InitQueryParseCommands 定义可以支持查询语句的结构
func (s *SqlserverDataReadRPCEmbed) InitExecuteParseCommands() []string {
	return []string{}
}

func (s *SqlserverDataReadRPCEmbed) User() string {
	return config.RuntimeConfig.SqlserverDataReadUser
}

func (s *SqlserverDataReadRPCEmbed) Password() string {
	return config.RuntimeConfig.SqlserverDataReadPassword
}
