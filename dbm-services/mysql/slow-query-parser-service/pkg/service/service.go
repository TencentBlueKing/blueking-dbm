// Package service TODO
package service

import (
	"dbm-services/mysql/slow-query-parser-service/pkg/mysql"

	"github.com/gin-gonic/gin"
)

// Start TODO
func Start(address string) error {
	r := gin.New()
	r.Use(gin.Logger())
	mysql.AddRouter(r)
	return r.Run(address)
}
