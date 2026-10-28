// Package main TODO
/*
Copyright © 2022 NAME HERE
*/
package main

import (
	"fmt"

	"dbm-services/common/dbha/hadb-api/cmd"
	"dbm-services/common/dbha/hadb-api/initc"
	"dbm-services/common/dbha/hadb-api/log"
	"dbm-services/common/dbha/hadb-api/model"
	"dbm-services/common/dbha/hadb-api/util"

	"github.com/spf13/viper"
)

func main() {
	fmt.Printf("try to start service...")
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("./conf")
	if err := viper.ReadInConfig(); err != nil {
		fmt.Printf("read config file failed:%s", err.Error())
		return
	}
	initc.GlobalConfig = &initc.Config{}
	if err := viper.Unmarshal(initc.GlobalConfig); err != nil {
		log.Logger.Errorf("unmarshal configure failed:%s", err.Error())
	}
	fmt.Printf("%+v", initc.GlobalConfig)

	util.InitTimezone(initc.GlobalConfig.TimezoneInfo.Local)

	log.InitLog(initc.GlobalConfig.LogInfo)
	// KMS：加载并校验运行时凭证；成功后无条件覆盖内存配置中的账号密码。
	// 开启 KMS 后加载失败即停止启动，不回退 ConfigMap 中的旧凭证。
	credentials, err := initc.LoadRuntimeCredentials()
	if err != nil {
		log.Logger.Fatalf("load KMS runtime credentials failed: %s", err.Error())
		return
	}
	if credentials != nil {
		initc.ApplyRuntimeCredentials(initc.GlobalConfig, credentials)
	}
	model.HADB.Init()
	defer model.HADB.Close()

	cmd.Execute()
}
