package cmd

import (
	"dbm-services/mongodb/db-tools/dbmon/cmd/mongojob"
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/mylog"
	"encoding/json"
	"fmt"
	"os"
	"slices"

	log "github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
)

var (
	debugCmd = &cobra.Command{
		Use:   "debug",
		Short: "debug",
		Long:  `debug`,
		Run: func(cmd *cobra.Command, args []string) {
			debugMain()
		},
	}

	sendMsgCmd = &cobra.Command{
		Use:   "sendmsg",
		Short: "sendmsg",
		Long:  `sendmsg`,
		Run: func(cmd *cobra.Command, args []string) {
			sendmsgCmdMain()
		},
	}
)
var instancePort int
var msgType string
var msgVal int // for ts type
var msgEventName, msgEventMsg, msgEventLevel, msgTargetIp string

func init() {
	sendMsgCmd.Flags().StringVar(&msgType, "type", "event|ts", "msg type")
	sendMsgCmd.Flags().IntVar(&msgVal, "val", 1, "the value or content of msg")
	sendMsgCmd.Flags().IntVar(&instancePort, "port", 27017, "port")
	sendMsgCmd.Flags().StringVar(&msgEventName, "name", "redis_login", "")
	sendMsgCmd.Flags().StringVar(&msgEventMsg, "msg", "msg", "")
	sendMsgCmd.Flags().StringVar(&msgEventLevel, "level", "warning", "warning|critical|error")
	sendMsgCmd.Flags().StringVar(&msgTargetIp, "targetIp", "", "default: servers[port].Ip")
	debugCmd.AddCommand(sendMsgCmd)
}

// debugCmdMain go run main.go debug
func debugMain() {
	// do nothing
}

// sendmsgCmdMain go run main.go debug sendmsg --type=event --name=event_name --msg="msg" --level=warning --port=27017
func sendmsgCmdMain() {
	config.InitConfig(cfgFile, mylog.Logger)
	mylog.InitRotateLoger()
	jsonTxt, _ := json.Marshal(config.GlobalConf)
	log.Printf("cfgFile:\n%s\n", jsonTxt)
	servers := config.GlobalConf.Servers
	idx := slices.IndexFunc(servers, func(s config.ConfServerItem) bool {
		return s.Port == instancePort
	})
	if idx < 0 {
		log.Fatalf("config文件:%q中不存在port==%d的server\n", cfgFile, instancePort)
	}
	server := servers[idx]
	if msgTargetIp == "" {
		msgTargetIp = server.IP
	}
	beatConfig := &config.GlobalConf.BkMonitorBeat
	if msgType == "event" {
		msgH, err := mongojob.GetBkMonitorEventSender(beatConfig, &server)
		if err != nil {
			fmt.Printf("fatal err %s", err)
			os.Exit(1)
		}
		msgH.SendEventMsg(
			beatConfig.EventConfig.DataID,
			beatConfig.EventConfig.Token,
			msgEventName, msgEventMsg, msgEventLevel, msgTargetIp)
	} else if msgType == "ts" {
		msgH, err := mongojob.GetBkMonitorMetricSender(beatConfig, &server)
		if err != nil {
			fmt.Printf("fatal err %s", err)
			os.Exit(1)
		}
		msgH.SendTimeSeriesMsg(
			beatConfig.MetricConfig.DataID,
			beatConfig.MetricConfig.Token,
			msgTargetIp, msgEventName, float64(msgVal))
	} else {
		fmt.Printf("bad msgType %q", msgType)
		os.Exit(1)
	}

}
