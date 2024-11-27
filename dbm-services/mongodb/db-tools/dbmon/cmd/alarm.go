package cmd

import (
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/mylog"
	"fmt"
	"time"

	"github.com/spf13/cobra"
	"go.uber.org/zap"
)

var (
	alarmCmd = &cobra.Command{
		Use:   "alarm",
		Short: "alarm",
		Long:  `alarm`,
		Run: func(cmd *cobra.Command, args []string) {
			cmd.Help()
		},
	}
	showShieldCmd = &cobra.Command{
		Use:   "list",
		Short: "list",
		Long:  `list`,
		Run: func(cmd *cobra.Command, args []string) {
			showAlarmMain()
		},
	}

	shieldCmd = &cobra.Command{
		Use:   "shield",
		Short: "shield",
		Long:  `shield`,
		Run: func(cmd *cobra.Command, args []string) {
			shieldConfigMain()
		},
	}

	unblockCmd = &cobra.Command{
		Use:   "unblock",
		Short: "unblock",
		Long:  `unblock`,
		Run: func(cmd *cobra.Command, args []string) {
			unblockAlarmMain()
		},
	}
)

var shieldTime int64

func init() {
	shieldCmd.Flags().Int64Var(&shieldTime, "second", 0,
		"shieldTime, seconds to shield, 0 for forever")

	alarmCmd.PersistentFlags().StringVarP(&portList, "port", "p", "all",
		"port or port list split by comma")
	alarmCmd.AddCommand(showShieldCmd)
	alarmCmd.AddCommand(shieldCmd)
	alarmCmd.AddCommand(unblockCmd)
}

// showAlarmMain    show alarm list
func showAlarmMain() {
	preRun(true)
	servers, err := getServerList(portList, dbmonConf.Config.Servers)
	if err != nil {
		mylog.Logger.Fatal("getServerList fail", zap.Error(err))
	}
	if len(servers) == 0 {
		mylog.Logger.Warn("no servers match", zap.String("portList", portList))
	}

	alarmConfig := config.NewAlarmConfig(config.ClusterConfig)
	for _, server := range servers {
		shield, endTime, isShiled, err := alarmConfig.GetOne(&server)
		if err != nil {
			mylog.Logger.Fatal(fmt.Sprintf("show server %s failed", server.Addr()), zap.Error(err))
		}
		mylog.Logger.Info(fmt.Sprintf("server %s, shield:%v, endTime:%s, isShield:%v",
			server.Addr(), shield, endTime, isShiled))
	}
	mylog.Logger.Info(fmt.Sprintf("list %d servers's alarm config success", len(servers)))

}

// unblockAlarmMain   unblock alarm
func unblockAlarmMain() {
	preRun(true)

	servers, err := getServerList(portList, dbmonConf.Config.Servers)
	if err != nil {
		mylog.Logger.Fatal("getServerList fail", zap.Error(err))
	}
	if len(servers) == 0 {
		mylog.Logger.Warn("no servers match", zap.String("portList", portList))
	}
	var updateCount int
	alarmConfig := config.NewAlarmConfig(config.ClusterConfig)
	for _, server := range servers {
		err = alarmConfig.Unblock(&server)
		if err != nil {
			mylog.Logger.Fatal(fmt.Sprintf("shield server %s failed", server.Addr()), zap.Error(err))
		}
		updateCount += 1
	}

	if err := config.ClusterConfig.RewriteConfigFile(); err != nil {
		mylog.Logger.Error(fmt.Sprintf("write cluster config failed, err:%v", err))
	} else {
		mylog.Logger.Info("write cluster config success", zap.String("clusterConfigFile", clusterConfigFile))
	}
	mylog.Logger.Info(fmt.Sprintf("alarm unblock %d servers success", updateCount))
}

// shieldConfigMain   go run main.go config get
func shieldConfigMain() {
	preRun(true)
	servers, err := getServerList(portList, dbmonConf.Config.Servers)
	if err != nil {
		mylog.Logger.Fatal("getServerList fail", zap.Error(err))
	}
	if len(servers) == 0 {
		mylog.Logger.Warn("no servers match", zap.String("portList", portList))
	}
	var shieldEndTime string
	if shieldTime > 0 {
		shieldEndTime = time.Now().Add(time.Duration(shieldTime) * time.Second).Format(config.ShieldEndTimeFormat)
	}

	alarmConfig := config.NewAlarmConfig(config.ClusterConfig)
	var updateCount int
	for _, server := range servers {
		mylog.Logger.Info("update server", zap.String("server", server.Addr()))
		err = alarmConfig.Shield(&server, shieldEndTime)
		if err != nil {
			mylog.Logger.Fatal(fmt.Sprintf("shield server %s failed", server.Addr()), zap.Error(err))
		}
		updateCount += 1
	}

	if err := config.ClusterConfig.RewriteConfigFile(); err != nil {
		mylog.Logger.Fatal(fmt.Sprintf("write cluster config failed"), zap.Error(err))
	} else {
		mylog.Logger.Info("write cluster config success", zap.String("clusterConfigFile", clusterConfigFile))
	}

	mylog.Logger.Info(fmt.Sprintf("alarm shield %d servers success", updateCount),
		zap.String("portList", portList), zap.String("end-time", shieldEndTime))

}
