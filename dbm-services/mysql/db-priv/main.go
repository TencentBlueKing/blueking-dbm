package main

import (
	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/common/go-pubpkg/apm/trace"
	"dbm-services/common/go-pubpkg/kms"
	v2 "dbm-services/mysql/priv-service/handler/v2"
	"dbm-services/mysql/priv-service/service"
	"dbm-services/mysql/priv-service/util"
	"io"
	"log/slog"
	"net/http"
	"os"
	"strings"

	"github.com/pkg/errors"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
	"gopkg.in/natefinch/lumberjack.v2"

	"dbm-services/mysql/priv-service/assests"
	"dbm-services/mysql/priv-service/handler"

	"github.com/gin-gonic/gin"
	"github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/source/file"
	flag "github.com/spf13/pflag"
	"github.com/spf13/viper"
)

func main() {
	// 把用户传递的命令行参数解析为对应变量的值
	flag.Parse()

	// 数据库初始化
	service.DB.Init()
	defer service.DB.Close()

	// 元数据库 migration
	if viper.GetBool("migrate") {
		if err := dbMigrate(); err != nil && !errors.Is(err, migrate.ErrNoChange) {
			slog.Error("migrate失败", err)
			os.Exit(0)
		}
	}

	util.DbmetaClient = util.NewClientByHosts(viper.GetString("dbmeta"))
	util.DrsClient = util.NewClientByHosts(viper.GetString("dbRemoteService"))

	// 注册服务
	gin.SetMode(gin.ReleaseMode)
	engine := gin.New()
	engine.Use(gin.Recovery())

	// setup trace
	trace.Setup()
	// apm: add otlgin middleware
	engine.Use(otelgin.Middleware("db_priv"))
	// apm: add prom metrics middleware
	metric.NewPrometheus("").Use(engine)

	handler.RegisterRoutes(
		engine, "/", []*gin.RouteInfo{
			{
				Method: http.MethodGet,
				Path:   "ping", HandlerFunc: func(context *gin.Context) {
					context.String(http.StatusOK, "pong")
				},
			},
		},
	)
	handler.RegisterRoutes(engine, "/priv", (&handler.PrivService{}).Routes())
	handler.RegisterRoutes(engine, "/priv/v2", v2.Routes())

	for _, e := range engine.Routes() {
		slog.Info(
			"start service",
			slog.String("method", e.Method),
			slog.String("path", e.Path),
			slog.String("handler", e.Handler),
		)
	}

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
	_ = viper.BindPFlags(flag.CommandLine)

	InitLog()

	cred, err := loadRuntimeCredentials()
	if err != nil {
		slog.Error("load kms failed", slog.String("err", err.Error()))
		return
	}

	if cred != nil {
		viper.Set("db.username", cred.MySQL.DbPriv.Username)
		viper.Set("db.password", cred.MySQL.DbPriv.Password)
		viper.Set("bk_app_code", cred.BkAppIdSecret.Default.AppCode)
		viper.Set("bk_app_secret", cred.BkAppIdSecret.Default.AppSecret)
	}
}

// dbMigrate 元数据库 migration
//
//		1、如果是首次migration：创建元数据库 CREATE DATABASE IF NOT EXISTS `bk_dbpriv` DEFAULT CHARACTER SET utf8;
//	 2、命令行执行 ./bk_dbpriv --migrate
func dbMigrate() error {
	slog.Info("run db migrations...")
	err := assests.DoMigrateFromEmbed()
	if err != nil {
		return err
	}
	err = assests.DoMigratePlatformPassword()
	if err != nil {
		return err
	}
	return nil
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
				},
			),
			&slog.HandlerOptions{Level: logLevel, AddSource: true},
		)
	}
	slog.SetDefault(slog.New(logger))
}

type RuntimeCredentials struct {
	MySQL struct {
		DbPriv struct {
			Username string `json:"username"`
			Password string `json:"password"`
		} `json:"dbPriv"`
	} `json:"mysql"`
	BkAppIdSecret struct {
		Default struct {
			AppCode   string `json:"app_code"`
			AppSecret string `json:"app_secret"`
		} `json:"default"`
	} `json:"bkapp_id_secret"`
}

func loadRuntimeCredentials() (*RuntimeCredentials, error) {
	enabled, err := kms.Enabled()
	if err != nil || !enabled {
		return nil, err
	}

	kmsOptions := kms.LoadOptions{
		CredentialDirEnv: "DB_PRIV_KMS_CREDENTIAL_DIR",
	}

	plaintext, enabled, err := kms.LoadEnvelope(kmsOptions)
	if err != nil || !enabled {
		return nil, err
	}

	var cred RuntimeCredentials
	if err := kms.DecodeJSON(plaintext, &cred); err != nil {
		return nil, err
	}

	for _, field := range []struct{ name, value string }{
		{"mysql.dbPriv.username", cred.MySQL.DbPriv.Username},
		{"mysql.dbPriv.password", cred.MySQL.DbPriv.Password},
		{"bkapp_id_secret.default.app_code", cred.BkAppIdSecret.Default.AppCode},
		{"bkapp_id_secret.default.app_secret", cred.BkAppIdSecret.Default.AppSecret},
	} {
		if err := kms.RequireNonEmpty(field.value, field.name); err != nil {
			return nil, err
		}
	}

	return &cred, nil
}
