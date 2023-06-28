package service

import (
	"dbm-services/mysql/db-remote-service/pkg/service/handler_rpc"

	"github.com/gin-gonic/gin"
)

// RegisterRouter 服务路由
func RegisterRouter(engine *gin.Engine) {
	mysqlGroup := engine.Group("/mysql")
	mysqlGroup.POST("/rpc", handler_rpc.MySQLRPCHandler)
	//mysqlGroup.POST("/parser", parseHandler)

	proxyGroup := engine.Group("/proxy-admin")
	proxyGroup.POST("/rpc", handler_rpc.ProxyRPCHandler)

	redisGroup := engine.Group("/redis")
	redisGroup.POST("/rpc", handler_rpc.RedisRPCHandler)

	twemproxyGroup := engine.Group("/twemproxy")
	twemproxyGroup.POST("/rpc", handler_rpc.TwemproxyRPCHandler)

	// predixyGroup := engine.Group("/predixy")
	// predixyGroup.POST("/rpc", handler_rpc.RedisRPCHandler)
}
