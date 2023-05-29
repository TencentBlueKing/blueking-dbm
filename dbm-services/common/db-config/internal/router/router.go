// Package router TODO
package router

import (
	"bk-dbconfig/internal/handler/simple"
	"net/http"

	"github.com/gin-gonic/gin"
)

// RegisterRestRoutes TODO
func RegisterRestRoutes(engine *gin.Engine) {
	simpleConfig := simple.Config{}
	RegisterRoutes(engine, "/bkconfig/v1/", simpleConfig.Routes())

	/*
	   userConfig := user.UserConfig{}
	   RegisterRoutes(engine, "/bkconfig/v1/", userConfig.Routes())
	*/
}

// RegisterPing TODO
func RegisterPing(engine *gin.Engine) {
	engine.GET("/ping", func(c *gin.Context) {
		c.String(http.StatusOK, "ok")
	})
}
