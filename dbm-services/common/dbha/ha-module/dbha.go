package main

import (
	"flag"
	"fmt"
	"os"

	"dbm-services/common/dbha/ha-module/agent"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/gm"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/monitor"
	"dbm-services/common/dbha/ha-module/util"
)

var dbhaType string
var configFile string

// Init TODO
func Init() {
	flag.StringVar(&dbhaType, "type", "", `Input dbha type, "agent" or "gm"`)
	flag.StringVar(&configFile, "config_file", "", "Input config file path")
}

func main() {
	Init()
	flag.Parse()
	if flag.NFlag() != 2 {
		fmt.Println("args wrong.")
		os.Exit(1)
	}

	conf, err := config.ParseConfigureFile(configFile)
	if err != nil {
		fmt.Printf("parse configure file failed:%s\n", err.Error())
		os.Exit(1)
	}

	err = conf.CheckConfig()
	if err != nil {
		fmt.Printf("check configure file failed:%s\n", err.Error())
		os.Exit(1)
	}
	util.InitTimezone(conf.Timezone)

	err = log.Init(conf.LogConf)
	if err != nil {
		fmt.Printf("init log file failed:%s\n", err.Error())
		os.Exit(1)
	}

	err = monitor.MonitorInit(conf)
	if err != nil {
		fmt.Printf("init monitor failed:%s\n", err.Error())
		os.Exit(1)
	}

	if util.LocalIp, err = util.GetMonIp(); err != nil {
		log.Logger.Fatal("get component machine ip failed.")
		os.Exit(1)
	}
	log.Logger.Debugf("local ip address:%s", util.LocalIp)

	switch dbhaType {
	case constvar.Agent:
		// new agent for each db type
		for _, dbType := range conf.AgentConf.ActiveDBType {
			go func(dbType string) {
				Agent, err := agent.NewMonitorAgent(conf, dbType)
				if err != nil {
					log.Logger.Fatalf("agent init failed. dbtype:%s err:%s", dbType, err.Error())
				}

				err = Agent.Run()
				if err != nil {
					log.Logger.Fatalf("agent run failed. dbtype:%s err:%s", dbType, err.Error())
				}
			}(dbType)
		}
		var c chan struct{}
		<-c
	case constvar.GM:
		GM, err := gm.NewGM(conf)
		if err != nil {
			log.Logger.Fatalf("GM init failed. err:%s", err.Error())
			os.Exit(1)
		}

		if err = GM.Run(); err != nil {
			log.Logger.Fatalf("GM run failed. err:%s", err.Error())
			os.Exit(1)
		}

	default:
		log.Logger.Fatalf("unknow dbha type")
		os.Exit(1)
	}
}
