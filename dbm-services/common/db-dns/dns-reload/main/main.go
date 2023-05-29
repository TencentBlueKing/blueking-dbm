// Package main TODO
package main

import (
	"dnsReload/config"
	"dnsReload/logger"
	"dnsReload/service"
	"dnsReload/util"
	"flag"
	"fmt"
	"os"
	"strconv"
	"time"
)

func main() {

	localIp, err := util.GetClientIp()
	if err != nil {
		logger.Error.Printf("GetClientIp Error[%+v]", err)
	}

	interval := config.GetConfig("interval")
	intervalTime, err := strconv.Atoi(interval)
	if err != nil {
		intervalTime = 3
	}
	for {
		err := service.Reload(localIp)
		if err != nil {
			//	TODO 发送告警、通知。。
		}
		time.Sleep(time.Duration(intervalTime) * time.Second)
		// 重新读取一下配置。避免修改配置文件不生效
		config.InitConfig(configFile)
	}
}

func init() {
	initFlag()
	config.InitConfig(configFile)
	logger.InitLogger()
	// dao.InitDB()
}

// 读取参数
var configFile string

func initFlag() {
	flag.StringVar(&configFile, "c", "", "config file")
	flag.Parse()

	if configFile == "" {
		fmt.Println("arg -c [configFile] is must")
		os.Exit(2)
	}
}
