package main

import (
	"log"
	"strings"

	"bk-dnsapi/internal/dao"
	"bk-dnsapi/internal/handler"
	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/common/go-pubpkg/apm/trace"

	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"

	"github.com/gin-gonic/gin"
	"github.com/spf13/viper"
)

func main() {
	engine := gin.Default()

	// setup trace
	trace.Setup()
	// apm: add otlgin middleware
	engine.Use(otelgin.Middleware("db_resource"))
	// apm: add prom metrics middleware
	metric.NewPrometheus("").Use(engine)

	RouterGroup(engine)
	InitConfig("config")

	if err := dao.Init(); err != nil {
		log.Fatal(err)
	}

	httpAddr := viper.GetString("http.listenAddress")
	if err := engine.Run(httpAddr); err != nil {
		log.Fatal(err)
	}

	if err := dao.Close(); err != nil {
		log.Println(err.Error())
	}
}

// RouterGroup 注册路由
func RouterGroup(engine *gin.Engine) {
	h := handler.Handler{}
	RegisterRoutes(engine, "/api/v1/dns/", h.Routes())
}

// RegisterRoutes 注册路由
func RegisterRoutes(router *gin.Engine, group string, routesInfo []*gin.RouteInfo) {
	r := router.Group(group)
	for _, route := range routesInfo {
		r.Handle(route.Method, route.Path, route.HandlerFunc)
	}
}

// InitConfig 初始化配置文件
func InitConfig(fileName string) {
	viper.AddConfigPath("conf")
	viper.SetConfigType("yaml")
	viper.SetConfigName(fileName)
	viper.AutomaticEnv() // read in environment variables that match
	// viper.SetEnvPrefix("ACCOUNT")
	replacer := strings.NewReplacer(".", "_")
	viper.SetEnvKeyReplacer(replacer)
	if err := viper.MergeInConfig(); err != nil {
		log.Fatal(err)
	}
}
