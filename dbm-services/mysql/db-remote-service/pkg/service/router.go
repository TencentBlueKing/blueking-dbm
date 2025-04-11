package service

import (
	"dbm-services/mysql/db-remote-service/pkg/service/handler_rpc"

	"github.com/gin-gonic/gin"
)

// RegisterRouter 服务路由
func RegisterRouter(engine *gin.Engine) {
	mysqlGroup := engine.Group("/mysql")
	mysqlGroup.POST("/rpc", handler_rpc.MySQLRPCHandler)
	mysqlGroup.POST("/complex-rpc", handler_rpc.MySQLComplexHandler)

	proxyGroup := engine.Group("/proxy-admin")
	proxyGroup.POST("/rpc", handler_rpc.ProxyRPCHandler)

	redisGroup := engine.Group("/redis")
	redisGroup.POST("/rpc", handler_rpc.RedisRPCHandler)

	twemproxyGroup := engine.Group("/twemproxy")
	twemproxyGroup.POST("/rpc", handler_rpc.TwemproxyRPCHandler)

	mongodbGroup := engine.Group("/mongodb")
	mongodbGroup.POST("/rpc", handler_rpc.MongoRPCHandler)

	sqlserverGroup := engine.Group("/sqlserver")
	// 这是drs内部远程查询接口，不给业务开放
	sqlserverGroup.POST("/rpc", handler_rpc.SqlserverRPCHandler)
	// 这是drs业务数据查询接口，对应运维用户自助查询功能
	sqlserverGroup.POST("/data-read-rpc", handler_rpc.SqlserverDataReadRPCHandler)
	// 这是drs系统库数据查询接口，对应DBA用户的自助查询功能
	sqlserverGroup.POST("/sys-read-rpc", handler_rpc.SqlserverSySReadRPCHandler)

	webConsoleGroup := engine.Group("/webconsole")
	webConsoleGroup.POST("/rpc", handler_rpc.WebConsoleRPCHandler)
}
