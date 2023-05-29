// Package main TODO
/*
Copyright © 2022 NAME HERE
*/
package main

import (
	"dbm-services/common/dbha/hadb-api/cmd"
	"dbm-services/common/dbha/hadb-api/initc"
	"dbm-services/common/dbha/hadb-api/log"
	"dbm-services/common/dbha/hadb-api/model"
	"dbm-services/common/dbha/hadb-api/util"
	"fmt"

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
	model.HADB.Init()
	defer model.HADB.Close()

	cmd.Execute()
}
