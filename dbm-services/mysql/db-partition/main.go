package main

import (
	"os"

	"dbm-services/mysql/db-partition/assests"
	"dbm-services/mysql/db-partition/cron"
	"dbm-services/mysql/db-partition/model"
	"dbm-services/mysql/db-partition/router"

	"github.com/gin-gonic/gin"
	"github.com/golang-migrate/migrate/v4"
	flag "github.com/spf13/pflag"
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
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
