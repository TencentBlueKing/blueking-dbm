package test

import (
	"log"
	"testing"
	"time"

	"dbm-services/common/dbha/ha-module/agent"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/gm"
)

func TestAgentNetTransfor(t *testing.T) {
	GlobalConfig, err := config.ParseConfigureFile("../gmInfo.yaml")
	if err != nil {
		log.Println("gmInfo get config failed.")
		return
	}
	ch := make(chan gm.DoubleCheckInstanceInfo, 0)
	gdm := gm.NewGDM(GlobalConfig, ch, nil)
	go func() {
		gdm.Run()
	}()

	time.Sleep(10 * time.Second)

	var d dbutil.DataBaseDetect
	dbIns := newTestInstance()
	d = dbIns
	agentIns := agent.MonitorAgent{
		CityID:           11,
		LastFetchInsTime: time.Unix(0, 0),
	}
	ip, _ := d.GetAddress()
	agentIns.DBInstance[ip] = d
	gmInfo := agent.GMConnection{
		Ip:            "0.0.0.0",
		Port:          50000,
		LastFetchTime: time.Now(),
	}
	err = gmInfo.Init()
	agentIns.GMInstance = map[string]*agent.GMConnection{
		"0.0.0.0": &gmInfo,
	}
	if err != nil {
		t.Errorf("gmInfo init failed.err:%s", err.Error())
		return
	}

	for i := 0; i < 100; i++ {
		switch i % 3 {
		case 0:
			dbIns.Status = constvar.DBCheckFailed
		case 1:
			dbIns.Status = constvar.SSHCheckFailed
		case 2:
			dbIns.Status = constvar.DBCheckSuccess
		}
		switch i % 4 {
		case 0:
			dbIns.App = "APP1"
		case 1:
			dbIns.App = "APP22"
		case 2:
			dbIns.App = "APP333"
		case 3:
			dbIns.App = "APP4444"
		}
		err = agentIns.ReporterGM(d)
		if err != nil {
			t.Errorf("reporter gmInfo failed.err:%s", err.Error())
			return
		}
	}
}
