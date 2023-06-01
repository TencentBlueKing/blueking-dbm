package service_test

import (
	"testing"

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
	ps.SpiderImage = config.GAppConfig.Image.SpiderImg
	if err := ps.CreateClusterPod(); err != nil {
		t.Fatalf(err.Error())
		return
	}
	t.Log("ending..")
}
