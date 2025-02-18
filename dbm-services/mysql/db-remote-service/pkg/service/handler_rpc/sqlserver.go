package handler_rpc

import (
	"dbm-services/mysql/db-remote-service/pkg/rpc_implement/sqlserver_rpc"
)

// SqlserverRPCHandler TODO
var SqlserverRPCHandler = generalHandler(&sqlserver_rpc.SqlserverRPCEmbed{})

// SqlserverRPCHandler TODO
var SqlserverDataReadRPCHandler = generalHandler(&sqlserver_rpc.SqlserverDataReadRPCEmbed{})

// SqlserverRPCHandler TODO
var SqlserverSySReadRPCHandler = generalHandler(&sqlserver_rpc.SqlserverSySReadRPCEmbed{})
