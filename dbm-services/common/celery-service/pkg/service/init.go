package service

import (
	"bytes"
	"io"
	"log/slog"
	"time"

	"github.com/gin-gonic/gin"

	"celery-service/pkg/handler"
	"celery-service/pkg/log"
)

var r *gin.Engine
var logger *slog.Logger

func Init() error {
	logger = log.GetLogger("root")

	r = gin.New()

	r.Use(gin.Recovery())
	r.Use(func(ctx *gin.Context) {
		start := time.Now()

		body, _ := io.ReadAll(ctx.Request.Body)
		ctx.Request.Body = io.NopCloser(bytes.NewReader(body))

		ctx.Next()

		logger.With(
			"METHOD", ctx.Request.Method,
			"URI", ctx.Request.RequestURI,
			"STATUS", ctx.Writer.Status(),
			"LATENCY", time.Now().Sub(start),
			"CLIENT", ctx.ClientIP(),
			"BODY", string(body),
		).Info("HTTP REQUEST")

		ctx.Next()
	})

	err := buildRouter(r)
	if err != nil {
		return err
	}

	handler.HandleAsyncKill(r)
	handler.HandleAsyncQuery(r)
	handler.HandleList(r)
	handler.HandleDiscovery(r)

	for _, rt := range r.Routes() {
		logger.Info(
			"init service",
			slog.String("method", rt.Method),
			slog.String("path", rt.Path),
			slog.String("handler", rt.Handler),
		)
	}

	return nil
}
