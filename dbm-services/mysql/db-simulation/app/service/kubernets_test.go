package service_test

import (
	"os"
	"testing"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/config"
	"dbm-services/mysql/db-simulation/app/service"
)

func TestCreateClusterPod(t *testing.T) {
	ps := service.NewDbPodSets()
	ps.BaseInfo = &service.MySQLPodBaseInfo{
		PodName: "test1",
		RootPwd: "",
		Charset: "utf8",
	}
	ps.DbImage = config.GAppConfig.Image.Tendb57Img
	ps.TdbCtlImage = config.GAppConfig.Image.TdbCtlImg
	// 使用 SpiderPods 切片配置多个 Spider 版本
	ps.SpiderPods = []service.SpiderPodBaseInfo{
		{
			SpiderImage:     config.GAppConfig.Image.SpiderImg,
			SpiderVersion:   "latest",
			SpiderStartArgs: nil,
		},
	}
	xlogger := logger.New(os.Stdout, true, logger.InfoLevel, map[string]string{"pod_name": ps.BaseInfo.PodName})
	if err := ps.CreateClusterPod("", xlogger); err != nil {
		t.Fatalf("%s", err.Error())
		return
	}
	t.Log("ending..")
}
