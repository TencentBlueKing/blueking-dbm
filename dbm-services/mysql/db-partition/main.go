package main

import (
	"fmt"
	"net/http"
	"os"
	"time"

	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/common/go-pubpkg/apm/trace"

	"github.com/gin-gonic/gin"
	"github.com/golang-migrate/migrate/v4"
	flag "github.com/spf13/pflag"
	"github.com/spf13/viper"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
	"golang.org/x/exp/slog"

	"dbm-services/mysql/db-partition/assests"
	"dbm-services/mysql/db-partition/cron"
	"dbm-services/mysql/db-partition/model"
	"dbm-services/mysql/db-partition/monitor"
	"dbm-services/mysql/db-partition/router"
)

func main() {
	flag.Parse()
	// 元数据库 migration
	if viper.GetBool("migrate") {
		if err := assests.DoMigrateFromEmbed(); err != nil && err != migrate.ErrNoChange {
			slog.Error("migrate fail", err)
			os.Exit(0)
		}
	}

	// 获取监控配置，多次尝试
	i := 1
	for ; i <= 10; i++ {
		setting, err := monitor.GetMonitorSetting()
		if err != nil {
			slog.Error(fmt.Sprintf("try %d time", i), "get monitor setting error", err)
			if i == 10 {
				slog.Error("try too many times")
				os.Exit(0)
			}
			time.Sleep(3 * time.Second)
		} else {
			// for test
			slog.Info("msg", "monitor setting", setting)
			viper.Set("monitor.service", setting.MonitorService)
			// 蓝鲸监控自定义事件
			viper.Set("monitor.event.data_id", setting.MonitorEventDataID)
			viper.Set("monitor.event.access_token", setting.MonitorEventAccessToken)
			// 蓝鲸监控自定义指标
			viper.Set("monitor.metric.data_id", setting.MonitorMetricDataID)
			viper.Set("monitor.metric.access_token", setting.MonitorMetricAccessToken)
			break
		}
	}

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
