package handler_rpc

import (
	"dbm-services/mysql/db-remote-service/pkg/rpc_implement/mongodb_rpc"
)

// MongoRPCHandler TODO
var MongoRPCHandler = mongodb_rpc.NewMongoRPCEmbed().DoCommand
