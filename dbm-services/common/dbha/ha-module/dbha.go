package main

import (
	"flag"
	"fmt"
	"os"
	"time"

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
	flag.StringVar(&dbhaType, "type", "", `Input dbha type, ["agent","gm","monitor"]`)
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

	switch dbhaType {
	case constvar.Agent:
		// new agent for each db type
		for _, clusterType := range conf.AgentConf.ActiveClusterType {
			go func(clusterType string) {
				Agent, err := agent.NewMonitorAgent(conf, clusterType)
				if err != nil {
					log.Logger.Errorf("agent init failed. clustertype:%s err:%s", clusterType, err.Error())
				}

				err = Agent.Run()
				if err != nil {
					log.Logger.Fatalf("agent run failed. clustertype:%s err:%s", clusterType, err.Error())
				}
			}(clusterType)
		}
		select {}
	case constvar.GM:
		GM := gm.NewGM(conf)
		if err = GM.Run(); err != nil {
			log.Logger.Fatalf("GM run failed. err:%s", err.Error())
			os.Exit(1)
		}
	case constvar.MONITOR:
		for {
			if monInfo, err := monitor.CheckHAComponent(conf); err != nil {
				if err = monitor.MonitorSend(err.Error(), monInfo); err != nil {
					log.Logger.Fatalf("global monitor run failed. err:%s", err.Error())
					os.Exit(1)
				}
			}
			time.Sleep(time.Duration(conf.Monitor.MonitorInterval) * time.Second)
		}

	default:
		log.Logger.Fatalf("unknow dbha type")
		os.Exit(1)
	}
}
