package handler_rpc

import "dbm-services/mysql/db-remote-service/pkg/mysql_rpc"

// MySQLRPCHandler mysql 请求响应
var MySQLRPCHandler = generalHandler(&mysql_rpc.MySQLRPCEmbed{})
