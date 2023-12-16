// Package service TODO
package service

import (
	"net/http"

	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/common/go-pubpkg/apm/trace"
	"dbm-services/mysql/slow-query-parser-service/pkg/mysql"

	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"

	"github.com/gin-gonic/gin"
)

// Start TODO
func Start(address string) error {
	r := gin.New()
	r.Use(gin.Logger())

	// setup trace
	trace.Setup()
	// apm: add otlgin middleware
	r.Use(
		gin.Recovery(),
		otelgin.Middleware("slow_query_parser_service"),
	)
	// apm: add prom metrics middleware
	metric.NewPrometheus("").Use(r)

	mysql.AddRouter(r)

	r.Handle("GET", "/ping", func(context *gin.Context) {
		context.String(http.StatusOK, "pong")
	})

	return r.Run(address)
}
