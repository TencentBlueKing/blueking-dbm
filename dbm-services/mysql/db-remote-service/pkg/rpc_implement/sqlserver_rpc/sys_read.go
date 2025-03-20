package sqlserver_rpc

import "dbm-services/mysql/db-remote-service/pkg/config"

type SqlserverSySReadRPCEmbed struct {
	SqlserverRPCEmbed
}

// InitQueryParseCommands 定义可以支持查询语句的结构
func (s *SqlserverSySReadRPCEmbed) InitQueryParseCommands() []string {
	return []string{
		"show",
		"select",
	}
}

// InitQueryParseCommands 定义可以支持查询语句的结构
func (s *SqlserverSySReadRPCEmbed) InitExecuteParseCommands() []string {
	return []string{}
}

func (s *SqlserverSySReadRPCEmbed) User() string {
	return config.RuntimeConfig.SqlserverSySReadUser
}

func (s *SqlserverSySReadRPCEmbed) Password() string {
	return config.RuntimeConfig.SqlserverSySReadPassword
}
