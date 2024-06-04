package webconsole_rpc

import (
	"dbm-services/mysql/db-remote-service/pkg/config"
	"dbm-services/mysql/db-remote-service/pkg/mysql_rpc"
)

type WebConsoleRPC struct {
	mysql_rpc.MySQLRPCEmbed
}

func (c *WebConsoleRPC) User() string {
	return config.RuntimeConfig.WebConsoleUser
}

func (c *WebConsoleRPC) Password() string {
	return config.RuntimeConfig.WebConsolePass
}
