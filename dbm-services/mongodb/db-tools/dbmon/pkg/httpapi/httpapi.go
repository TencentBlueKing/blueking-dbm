// Package httpapi 用于启动http服务
package httpapi

import (
	"dbm-services/mongodb/db-tools/dbmon/mylog"
	"fmt"
	"io"
	"net/http"
	"os"

	"dbm-services/mongodb/db-tools/dbmon/config"

	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"

	"github.com/gin-gonic/gin"
)

// health 返回健康状态
func health(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"message": "ok",
	})
}

// version 返回版本号
func version(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"verion": consts.BkDbmonVersion,
	})
}

// StartListen http开始监听
func StartListen(conf *config.Configuration) {
	if conf.HttpAddress == "" {
		return
	}
	gin.SetMode(gin.ReleaseMode)
	gin.DefaultWriter = io.Discard
	r := gin.Default()
	r.Use(mylog.GinLogger(), mylog.GinRecovery(true))
	r.GET("/health", health)
	r.GET("/version", version)
	mylog.Logger.Info(fmt.Sprintf("start listen %s", conf.HttpAddress))
	err := r.Run(conf.HttpAddress)
	if err != nil {
		msg := fmt.Sprintf("start listen %s error:%v", conf.HttpAddress, err)
		mylog.Logger.Error(msg)
		fmt.Println(msg)
		os.Exit(1)
	}

}
