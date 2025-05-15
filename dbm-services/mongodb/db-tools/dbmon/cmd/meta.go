package cmd

import (
	"dbm-services/mongodb/db-tools/dbmon/mylog"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mycmd"
	"fmt"
	"slices"
	"time"

	"github.com/spf13/cobra"
	"go.uber.org/zap"
	"gopkg.in/yaml.v2"
)

var (
	metaCmd = &cobra.Command{
		Use:   "meta",
		Short: "meta",
		Long:  `meta`,
		Run: func(cmd *cobra.Command, args []string) {
			cmd.Help()
		},
	}
	listMetaCmd = &cobra.Command{
		Use:   "list",
		Short: "list",
		Long:  `list`,
		Run: func(cmd *cobra.Command, args []string) {
			listMetaMain()
		},
	}
	delMetaCmd = &cobra.Command{
		Use:   "delete",
		Short: "delete",
		Long:  `delete`,
		Run: func(cmd *cobra.Command, args []string) {
			delMetaMain()
		},
	}
)

func init() {
	metaCmd.PersistentFlags().StringVarP(&portList, "port", "p", "all",
		"port or port list split by comma")
	metaCmd.AddCommand(listMetaCmd)
	metaCmd.AddCommand(delMetaCmd)
}

// listMetaMain    show alarm list
func listMetaMain() {
	preRun(true)
	servers, err := getServerList(portList, dbmonConf.Config.Servers)
	mylog.Logger.Debug("arg portList", zap.Any("portList", portList))
	mylog.Logger.Debug("server list", zap.Any("servers", servers))
	if err != nil {
		mylog.Logger.Fatal("getServerList fail", zap.String("err", err.Error()))
	}
	if len(servers) == 0 {
		mylog.Logger.Warn("no servers match", zap.String("portList", portList))
	}

	data, err := yaml.Marshal(servers)
	if err != nil {
		mylog.Logger.Fatal("yaml.Marshal fail", zap.Error(err))
	}
	fmt.Printf("%s", data)
}

// delMetaMain    show alarm list
func delMetaMain() {
	preRun(true)
	// 在删除meta时，port参数不能是all
	if portList == "all" || portList == "0" {
		mylog.Logger.Fatal("portList can't be all, please use -p to specify port")
	}
	servers, err := getServerList(portList, dbmonConf.Config.Servers)
	mylog.Logger.Debug("arg portList", zap.Any("portList", portList))
	mylog.Logger.Debug("server list", zap.Any("servers", servers))
	if err != nil {
		mylog.Logger.Fatal("getServerList fail", zap.String("err", err.Error()))
	}

	if len(servers) == 0 {
		mylog.Logger.Warn("no servers match", zap.String("portList", portList))
		return
	}

	total := len(dbmonConf.Config.Servers)
	var deletedPortList []int
	var leftPortList []int

	for _, server := range servers {
		for j, s := range dbmonConf.Config.Servers {
			if s.Addr() == server.Addr() {
				deletedPortList = append(deletedPortList, s.Port)
				mylog.Logger.Info("delete server", zap.String("server", s.Addr()))
				dbmonConf.Config.Servers = slices.Delete(dbmonConf.Config.Servers, j, j+1)
				break
			}
		}
	}

	for _, s := range dbmonConf.Config.Servers {
		leftPortList = append(leftPortList, s.Port)
	}
	deleteCount := len(deletedPortList)
	left := len(dbmonConf.Config.Servers)
	mylog.Logger.Info("delete servers",
		zap.String("deletedPortList", fmt.Sprintf("%v", deletedPortList)),
		zap.String("leftPortList", fmt.Sprintf("%v", leftPortList)),
		zap.Int("total", total), zap.Int("deleteCount", deleteCount), zap.Int("left", left))

	if err := dbmonConf.WriteFile(dbmonConf.Config); err != nil {
		mylog.Logger.Fatal("write dbmon-config fail", zap.String("file", cfgFile), zap.Error(err))
	} else {
		mylog.Logger.Info("write dbmon-config success", zap.String("file", cfgFile))
	}

	if left == 0 {
		mylog.Logger.Info("all servers deleted, stop dbmon, please wait for 2 minutes")
		_, stdOut, stdErr, err := mycmd.New("/bin/sh", "/home/mysql/bk-dbmon/stop.sh").Run(2 * time.Minute)
		mylog.Logger.Info("stop dbmon",
			zap.String("stdout", stdOut),
			zap.String("stderr", stdErr),
			zap.Error(err))
	}

}
