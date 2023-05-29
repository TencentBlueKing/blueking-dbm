// Package httpapi TODO
package httpapi

import (
	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"fmt"
	"io/ioutil"
	"net/http"

	"github.com/gin-gonic/gin"
)

func health(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"message": "ok",
	})
}

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
	gin.DefaultWriter = ioutil.Discard
	r := gin.Default()
	r.Use(mylog.GinLogger(), mylog.GinRecovery(true))
	r.GET("/health", health)
	r.GET("/version", version)
	mylog.Logger.Info(fmt.Sprintf("start listen %s", conf.HttpAddress))
	r.Run(conf.HttpAddress)
}
