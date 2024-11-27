package cmd

import (
	"context"
	"dbm-services/mongodb/db-tools/dbmon/cmd/logparserjob"
	"dbm-services/mongodb/db-tools/dbmon/cmd/mongojob"
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/mylog"
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
	ParseMongoLogCmd = &cobra.Command{
		Use:   "parselog",
		Short: "parselog",
		Long:  `parselog`,
		Run: func(cmd *cobra.Command, args []string) {
			parseMongoLog()
		},
	}
)
var instancePort int
var msgType string
var msgVal int // for ts type
var msgEventName, msgEventMsg, msgEventLevel, msgTargetIp string

var logFilePattern string
var outputDir string
var outputFile string
var follow bool

func init() {
	sendMsgCmd.Flags().StringVar(&msgType, "type", "event|ts", "msg type")
	sendMsgCmd.Flags().IntVar(&msgVal, "val", 1, "the value or content of msg")
	sendMsgCmd.Flags().IntVar(&instancePort, "port", 27017, "port")
	sendMsgCmd.Flags().StringVar(&msgEventName, "name", "redis_login", "")
	sendMsgCmd.Flags().StringVar(&msgEventMsg, "msg", "msg", "")
	sendMsgCmd.Flags().StringVar(&msgEventLevel, "level", "warning", "warning|critical|error")
	sendMsgCmd.Flags().StringVar(&msgTargetIp, "targetIp", "", "default: servers[port].Ip")
	ParseMongoLogCmd.Flags().StringVar(&logFilePattern, "pattern", "", "log file")
	ParseMongoLogCmd.Flags().StringVar(&outputDir, "output", "", "output dir")
	ParseMongoLogCmd.Flags().StringVar(&outputFile, "outputFile", "", "output fileName prefix")
	ParseMongoLogCmd.Flags().BoolVar(&follow, "follow", false, "tail -f logFile")
	debugCmd.AddCommand(sendMsgCmd)
	debugCmd.AddCommand(ParseMongoLogCmd)
}

// debugCmdMain go run main.go debug
func debugMain() {
	fmt.Println("debugMain")
}

// sendmsgCmdMain go run main.go debug sendmsg --type=event --name=event_name --msg="msg" --level=warning --port=27017
func sendmsgCmdMain() {
	preRun(true)

	servers := dbmonConf.Config.Servers
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
	beatConfig := &dbmonConf.Config.BkMonitorBeat
	msgH, err := mongojob.GetBkMonitorBeatSender(beatConfig, &server)
	if err != nil {
		fmt.Printf("fatal err %s", err)
		os.Exit(1)
	}
	if msgType == "event" {
		msgH.SendEventMsg(
			beatConfig.EventConfig.DataID,
			beatConfig.EventConfig.Token,
			msgEventName, msgEventMsg, msgEventLevel, msgTargetIp, mylog.Logger)
	} else if msgType == "ts" {
		msgH.SendTimeSeriesMsg(
			beatConfig.MetricConfig.DataID,
			beatConfig.MetricConfig.Token,
			msgTargetIp, msgEventName, float64(msgVal), mylog.Logger)
	} else {
		fmt.Printf("bad msgType %q", msgType)
		os.Exit(1)
	}
}

func parseMongoLog() {
	fmt.Printf("logFilePattern:%s, outputDir:%s\n", logFilePattern, outputDir)
	succ, fail, err := logparserjob.ParseFile(logFilePattern, outputDir, outputFile, follow,
		context.TODO(), context.TODO(), nil, mylog.Logger)
	fmt.Printf("succ %d fail %d err %v\n", succ, fail, err)
}
