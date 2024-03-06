package main

import (
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
	"github.com/golang-migrate/migrate/v4"
	flag "github.com/spf13/pflag"
	"github.com/spf13/viper"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
	"golang.org/x/exp/slog"

	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/common/go-pubpkg/apm/trace"
	"dbm-services/mysql/db-partition/monitor"

	"dbm-services/mysql/db-partition/assests"
	"dbm-services/mysql/db-partition/cron"
	"dbm-services/mysql/db-partition/model"
	"dbm-services/mysql/db-partition/router"
)

func main() {
	flag.Parse()

	defer model.DB.Close()

	// 元数据库 migration
	if viper.GetBool("migrate") {
		if err := assests.DoMigrateFromEmbed(); err != nil && err != migrate.ErrNoChange {
			slog.Error("migrate fail", err)
			os.Exit(0)
		}
	}

	// 获取监控配置，多次尝试，获取监控配置失败，如果服务异常无法上报监控，所以让服务退出，可触发服务故障的告警。
	monitor.InitMonitor()

	// 注册定时任务
	cronList, err := cron.RegisterCron()
	if err != nil {
		os.Exit(0)
	}

	defer func() {
		for _, c := range cronList {
			c.Stop()
		}
		slog.Info("stop all cron jobs")
	}()

	// 注册服务
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	r.Use(gin.Recovery())

	// setup trace
	trace.Setup()
	// apm: add otlgin middleware
	r.Use(otelgin.Middleware("db_partition"))
	// apm: add prom metrics middleware
	metric.NewPrometheus("").Use(r)

	r.Handle(http.MethodGet, "/ping", func(context *gin.Context) {
		context.String(http.StatusOK, "pong")
	})
	router.RegisterRouter(r)
	if err = r.Run(viper.GetString("listen_address")); err != nil {
		slog.Error("register router fail:", err)
		os.Exit(0)
	}
}

func init() {
	model.InitEnv()
	model.InitLog()
	model.DB.Init()
	model.InitClient()
}
