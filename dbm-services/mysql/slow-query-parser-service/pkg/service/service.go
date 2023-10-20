// Package service TODO
package service

import (
	"net/http"

	"dbm-services/mysql/slow-query-parser-service/pkg/mysql"

	"github.com/gin-gonic/gin"
)

// Start TODO
func Start(address string) error {
	r := gin.New()
	r.Use(gin.Logger())
	mysql.AddRouter(r)

	r.Handle("GET", "/ping", func(context *gin.Context) {
		context.String(http.StatusOK, "pong")
	})

	return r.Run(address)
}
