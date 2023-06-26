package main

import (
	"net/http"
	"os"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/db-resource/internal/middleware"
	"dbm-services/common/db-resource/internal/routers"
	"dbm-services/common/db-resource/internal/svr/task"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/gin-contrib/pprof"
	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
	"github.com/robfig/cron/v3"
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
	lcron := cron.New()
	initCron(lcron)
	lcron.Start()
	defer lcron.Stop()
	engine.Run(config.AppConfig.ListenAddress)
}

// init TODO
func init() {
	if err := initLogger(); err != nil {
		logger.Fatal("Init Logger Failed %s", err.Error())
		return
	}
}

func initCron(localcron *cron.Cron) {
	localcron.AddFunc("1 */5 * * *", func() {
		if err := task.UpdateResourceGseAgentStatus(); err != nil {
			logger.Error("update gse status %s", err.Error())
		}
	})
}

// initLogger initialization log
func initLogger() (err error) {
	var writer *os.File
	formatJson := true
	level := logger.InfoLevel
	writer = os.Stdout
	l := logger.New(writer, formatJson, level, map[string]string{})
	logger.ResetDefault(l)
	defer logger.Sync()
	return
}
