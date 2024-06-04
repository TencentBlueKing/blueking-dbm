package handler_rpc

import "dbm-services/mysql/db-remote-service/pkg/webconsole_rpc"

var WebConsoleRPCHandler = generalHandler(&webconsole_rpc.WebConsoleRPC{})
