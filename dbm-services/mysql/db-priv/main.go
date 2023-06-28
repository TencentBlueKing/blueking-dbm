package main

import (
	"io"
	"os"
	"strings"

	"dbm-services/mysql/priv-service/assests"
	"dbm-services/mysql/priv-service/handler"
	"dbm-services/mysql/priv-service/service"
	"dbm-services/mysql/priv-service/util"

	"github.com/gin-gonic/gin"
	"github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/source/file"
	flag "github.com/spf13/pflag"
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
	"gopkg.in/natefinch/lumberjack.v2"
)

func main() {
	// 把用户传递的命令行参数解析为对应变量的值
	flag.Parse()
	// 元数据库 migration
	if viper.GetBool("migrate") {
		if err := dbMigrate(); err != nil && err != migrate.ErrNoChange {
			slog.Error("migrate失败", err)
			os.Exit(0)
		}
	}

	// 生成公钥、私钥
	if err := util.CreateKeyFile(); err != nil {
		slog.Error("读取密码文件失败", err)
	}

	// 数据库初始化
	service.DB.Init()
	defer service.DB.Close()

	// 注册服务
	gin.SetMode(gin.ReleaseMode)
	engine := gin.New()
	engine.Use(gin.Recovery())
	handler.RegisterRoutes(engine, "/priv", (&handler.PrivService{}).Routes())
	if err := engine.Run(viper.GetString("http.listenAddress")); err != nil {
		slog.Error("注册服务失败", err)
	}
}

// init 初始化环境变量
func init() {
	viper.AddConfigPath("conf")
	viper.SetConfigType("yaml")
	viper.SetConfigName("config")
	viper.AutomaticEnv()

	replacer := strings.NewReplacer(".", "_")
	viper.SetEnvKeyReplacer(replacer)
	if err := viper.ReadInConfig(); err != nil {
		slog.Error("读取配置文件失败", err)
	}

	flag.Bool(
		"migrate", false,
		"run migrate to databases, not exit.",
	)
	viper.BindPFlags(flag.CommandLine)
	InitLog()
}

// dbMigrate 元数据库 migration
//
//		1、如果是首次migration：创建元数据库 CREATE DATABASE IF NOT EXISTS `bk_dbpriv` DEFAULT CHARACTER SET utf8;
//	 2、命令行执行 ./bk_dbpriv --migrate
func dbMigrate() error {
	slog.Info("run db migrations...")
	if err := assests.DoMigrateFromEmbed(); err == nil {
		return nil
	} else {
		return err
	}
}

// InitLog 程序日志初始化
func InitLog() {
	var logLevel = new(slog.LevelVar)
	logLevel.Set(slog.LevelInfo)
	if strings.ToLower(strings.TrimSpace(viper.GetString("log.level"))) == "debug" {
		logLevel.Set(slog.LevelDebug)
	}
	var logger *slog.TextHandler
	logger = slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: logLevel, AddSource: true})
	logPath := strings.TrimSpace(viper.GetString("log.path"))
	if logPath != "" {
		logger = slog.NewTextHandler(
			io.MultiWriter(
				os.Stdout,
				&lumberjack.Logger{
					Filename:   logPath,
					MaxSize:    viper.GetInt("log.max_size"),
					MaxAge:     viper.GetInt("log.max_age"),
					MaxBackups: viper.GetInt("log.max_backups"),
					LocalTime:  true,
				}),
			&slog.HandlerOptions{Level: logLevel, AddSource: true},
		)
	}
	slog.SetDefault(slog.New(logger))
}
