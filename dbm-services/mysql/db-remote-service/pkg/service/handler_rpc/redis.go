package handler_rpc

import "dbm-services/mysql/db-remote-service/pkg/redis_rpc"

// RedisRPCHandler TODO
var RedisRPCHandler = redis_rpc.NewRedisRPCEmbed().DoCommand

// TwemproxyRPCHandler TODO
var TwemproxyRPCHandler = redis_rpc.NewTwemproxyRPCEmbed().DoCommand
