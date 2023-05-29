package main

import (
	"bk-dbconfig/internal/repository"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/internal/router"
	"bk-dbconfig/pkg/core/config"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/middleware"
	"log"
	_ "net/http/pprof"
	"os"

	"github.com/gin-gonic/gin"
	"github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/source/file"
	"github.com/spf13/pflag"
	"github.com/spf13/viper"
)

// @title           bkconfigsvr API
// @version         0.0.1
// @description     This is a bkconfigsvr celler server.
// @termsOfService  http://swagger.io/terms/
// @host            localhost:80
// @Schemes        http
// @contact.name   API Support
// @contact.url    http://www.swagger.io/support
// @contact.email  support@swagger.io

// @license.name  Apache 2.0
// @license.url   http://www.apache.org/licenses/LICENSE-2.0.html

// @BasePath  /

// main TODO
// @securityDefinitions.basic  BasicAuth
func main() {
	// init DB
	model.DB.Init()
	defer model.DB.Close()
	model.InitCache()

	// process db migrate
	pflag.Parse()
	if config.GetBool("migrate") || config.GetBool("migrate.enable") {
		if err := dbMigrate(); err != nil && err != migrate.ErrNoChange {
			log.Fatal(err)
		}
		// 命令行指定了 --migrate 时，执行完退出
		// 配置文件指定了 --migrate.enable 时，执行完继续执行主进程
		if config.GetBool("migrate") {
			os.Exit(0)
		}
	}

	model.LoadCache()
	gin.SetMode(gin.ReleaseMode)
	engine := gin.New() // New()
	engine.Use(gin.Recovery())
	engine.Use(middleware.CorsMiddleware())
	engine.Use(middleware.RequestMiddleware())
	engine.Use(middleware.RequestLoggerMiddleware())
	router.RegisterPing(engine)
	router.RegisterRestRoutes(engine)
	if config.GetBool("swagger.enableUI") {
		router.RegisterRoutesSwagger(engine)
	}

	httpAddr := config.GetString("http.listenAddress")
	logger.Info("start http server on %s ", httpAddr)

	if err := engine.Run(httpAddr); err != nil {
		log.Fatal(err)
	}

}

// init reads in config file and ENV variables if set.
func init() {
	config.InitConfig("logger")
	config.InitConfig("config")
	logger.Init()

	pflag.Bool("migrate", false,
		"run migrate to databases and exit. set migrate.enable to config.yaml will run migrate and continue ")
	pflag.String("migrate.source", "", "migrate source path")
	pflag.Int("migrate.force", 0, "force the version to be clean if it's dirty")
	viper.BindPFlags(pflag.CommandLine)
}

func dbMigrate() error {
	logger.Info("run db migrations...")
	if err := repository.DoMigrateFromEmbed(); err == nil {
		return nil
	} else {
		return err
	}
	// logger.Info("try to run migrations with migrate.source")
	// return repository.DoMigrateFromSource()
}
