// Package router TODO
package router

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/service"
	"dbm-services/mysql/db-simulation/handler"

	"github.com/gin-gonic/gin"
)

// RegisterRouter reg routers
func RegisterRouter(engine *gin.Engine) {
	engine.POST("/app/debug", TurnOnDebug)
	// mysql
	g := engine.Group("/mysql")
	g.POST("/simulation", handler.Dbsimulation)
	g.POST("/task", handler.QueryTask)
	// syntax
	s := engine.Group("/syntax")
	s.POST("/check/file", handler.SyntaxCheckFile)
	s.POST("/check/sql", handler.SyntaxCheckSQL)
	// rule
	r := engine.Group("/rule")
	r.POST("/manage", handler.ManageRule)
	r.GET("/getall", handler.GetAllRule)
	r.POST("/update", handler.UpdateRule)
	// spider
	sp := engine.Group("/spider")
	sp.POST("/simulation", handler.SpiderClusterSimulation)
	sp.POST("/create", handler.CreateTmpSpiderPodCluster)

}

// TurnOnDebug TODO
func TurnOnDebug(r *gin.Context) {
	logger.Info("current delpod: %v", service.DelPod)
	service.DelPod = !service.DelPod
	r.JSON(0, map[string]interface{}{
		"delpod": service.DelPod,
	})
}
