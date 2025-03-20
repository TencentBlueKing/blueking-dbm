// Package httpapi 用于启动http服务
package httpapi

import (
	"context"
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/mylog"
	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"sync"
	"syscall"

	"go.uber.org/zap"

	"github.com/gin-gonic/gin"
)

// health 返回健康状态
func health(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"pid":     os.Getpid(),
		"message": "ok",
	})
}

// version 返回版本号
func version(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"verion": consts.BkDbmonVersion,
	})
}

// stop 发送停止信号
func stop(c *gin.Context) {
	pid := os.Getpid()
	mylog.Logger.Info("send stop signal to process", zap.Int32("pid", int32(pid)))
	syscall.Kill(pid, syscall.SIGUSR2)
	c.JSON(http.StatusOK, gin.H{
		"msg": "send stop signal to process",
	})
}

// StartListen http开始监听
func StartListen(conf *config.Configuration, wg *sync.WaitGroup, osCtx context.Context) {
	defer wg.Done()
	if conf.HttpAddress == "" {
		return
	}
	gin.SetMode(gin.ReleaseMode)
	gin.DefaultWriter = io.Discard
	r := gin.Default()
	r.Use(mylog.GinLogger(), mylog.GinRecovery(true))
	r.GET("/health", health)
	r.GET("/version", version)
	r.GET("/stop", stop)

	srv := &http.Server{
		Addr:    conf.HttpAddress,
		Handler: r.Handler(),
	}
	go func() {
		// service connections
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			msg := fmt.Sprintf("listen: %s error:%v", conf.HttpAddress, err)
			mylog.Logger.Error(msg)
			fmt.Println(msg)
			os.Exit(1)
		}
	}()
	// wait for stop signal
	<-osCtx.Done()
	srv.Shutdown(context.TODO())
}
