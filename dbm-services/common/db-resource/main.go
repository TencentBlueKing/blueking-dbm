package main

import (
	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/db-resource/internal/middleware"
	"dbm-services/common/db-resource/internal/routers"
	"dbm-services/common/go-pubpkg/logger"
	"net/http"
	"os"

	"github.com/gin-contrib/pprof"
	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
)

var buildstamp = ""
var githash = ""
var version = ""

func main() {
	logger.Info("buildstamp:%s,githash:%s,version:%s", buildstamp, githash, version)
	engine := gin.New()
	pprof.Register(engine)
	engine.Use(requestid.New())
	engine.Use(middleware.ApiLogger)
	engine.Use(middleware.BodyLogMiddleware)
	routers.RegisterRoutes(engine)
	engine.POST("/app", func(ctx *gin.Context) {
		ctx.SecureJSON(http.StatusOK, map[string]interface{}{"buildstamp": buildstamp, "githash": githash,
			"version": version})
	})
	engine.Run(config.AppConfig.ListenAddress)
}

// init TODO
func init() {
	if err := initLogger(); err != nil {
		logger.Fatal("Init Logger Failed %s", err.Error())
		return
	}
}

// initLogger initialization log
func initLogger() (err error) {
	var writer *os.File
	formatJson := true
	level := logger.InfoLevel
	writer = os.Stdin
	l := logger.New(writer, formatJson, level, map[string]string{})
	logger.ResetDefault(l)
	defer logger.Sync()
	return
}
