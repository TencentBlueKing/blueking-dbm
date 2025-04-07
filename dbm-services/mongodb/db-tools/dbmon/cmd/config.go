package cmd

import (
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/mylog"
	"fmt"
	"slices"
	"strconv"
	"strings"

	"github.com/pkg/errors"
	"go.uber.org/zap"

	"github.com/spf13/cobra"
)

var (
	configCmd = &cobra.Command{
		Use:   "config",
		Short: "config",
		Long:  `config`,
		Run: func(cmd *cobra.Command, args []string) {
			cmd.Help()
		},
	}

	getConfigCmd = &cobra.Command{
		Use:   "get",
		Short: "get",
		Long:  `get`,
		Run: func(cmd *cobra.Command, args []string) {
			getConfigCmdMain()
		},
	}
	getAllConfigCmd = &cobra.Command{
		Use:   "get-all",
		Short: "get-all",
		Long:  `get-all`,
		Run: func(cmd *cobra.Command, args []string) {
			getAllConfigCmdMain()
		},
	}

	setConfigCmd = &cobra.Command{
		Use:   "set",
		Short: "set",
		Long:  `set`,
		Run: func(cmd *cobra.Command, args []string) {
			setConfigCmdMain()
		},
	}
)

var portList string
var segment string
var key string
var value string // value for set

func init() {
	getConfigCmd.Flags().StringVarP(&segment, "segment", "s", "", "segment, empty for all")
	getConfigCmd.Flags().StringVarP(&key, "key", "k", "", "key, empty for all")

	setConfigCmd.Flags().StringVarP(&segment, "segment", "s", "", "segment, empty for all")
	setConfigCmd.Flags().StringVarP(&key, "key", "k", "", "key, empty for all")
	setConfigCmd.Flags().StringVarP(&value, "value", "V", "", "value to set")

	configCmd.PersistentFlags().StringVarP(&portList, "port", "p", "all",
		"port or port list split by comma")
	configCmd.AddCommand(getConfigCmd)
	configCmd.AddCommand(getAllConfigCmd)
	configCmd.AddCommand(setConfigCmd)

}

// parsePortArg 解析端口参数.
// --port 27017 => []int{27017} 单个端口
// --port 27017,27018 => []int{27017, 27018}
// --port 0 => []int{0} 0 表示所有端口
// --port all => []int{0} all 表示所有端口
// --port 0,27017 => error
func parsePortArg(portList string) ([]int, error) {
	if portList == "all" || portList == "0" {
		return []int{0}, nil
	}

	if portList == "" {
		return nil, errors.New("portList is empty")
	}

	ports := strings.Split(portList, ",")
	portInts := make([]int, 0, len(ports))
	for _, p := range ports {
		port, err := strconv.Atoi(p)
		if err != nil {
			return nil, err
		}
		if port <= 0 {
			return nil, errors.New("bad port")
		}
		portInts = append(portInts, port)
	}
	return portInts, nil
}

// getServerList 通过端口参数获取server列表
func getServerList(portsStr string, servers []config.ConfServerItem) ([]config.ConfServerItem, error) {
	ports, err := parsePortArg(portsStr)
	if err != nil {
		return nil, errors.Wrap(err, "parsePortArg fail")
	}
	if len(ports) == 1 && ports[0] == 0 {
		return servers, nil
	}
	matchServers := make([]config.ConfServerItem, 0, len(ports))
	for _, port := range ports {
		idx := slices.IndexFunc(servers, func(s config.ConfServerItem) bool {
			return s.Port == port
		})
		if idx < 0 {
			continue
		}
		matchServers = append(matchServers, servers[idx])
	}
	return matchServers, nil
}

// getAllConfigCmdMain  go run main.go config get
func getAllConfigCmdMain() {
	preRun(true)
	servers, err := getServerList(portList, dbmonConf.Config.Servers)
	if err != nil {
		mylog.Logger.Fatal("getServerList fail", zap.Error(err))
	}
	if len(servers) == 0 {
		mylog.Logger.Warn("no servers match", zap.String("portList", portList))
		return
	}
	// get all config segment.key
	allConfig := config.GetAllClusterConfigRows()
	var v string
	for _, server := range servers {
		for _, row := range allConfig {
			v, err = config.ClusterConfig.GetOne(&server, row.Segment, row.Key)
			if err != nil {
				mylog.Logger.Error(fmt.Sprintf("get config failed, segment:%s key:%s err:%v", segment, key, err))
				continue
			}
			fmt.Printf("%s\t%6d\t%32s = %s\n", server.IP, server.Port, fmt.Sprintf("%s.%s", row.Segment, row.Key), v)
		}
	}
}

// getConfigCmdMain  go run main.go config get
func getConfigCmdMain() {
	preRun(true)
	mylog.Logger.Info(fmt.Sprintf("%+v", dbmonConf.Config.Servers))

	// get port list
	servers, err := getServerList(portList, dbmonConf.Config.Servers)
	if err != nil {
		mylog.Logger.Fatal("getServerList fail", zap.Error(err))
	}
	if len(servers) == 0 {
		mylog.Logger.Warn("no servers match", zap.String("portList", portList))
	}

	var v string
	for _, server := range servers {
		v, err = config.ClusterConfig.GetOne(&server, segment, key)
		if err != nil {
			mylog.Logger.Error(fmt.Sprintf("get config failed, segment:%s key:%s err:%v", segment, key, err))
			continue
		}
		// mylog.Logger.Info(fmt.Sprintf("get %s.%s success, value: %s", segment, key, v))
		fmt.Printf("%s\t%d\t%s\t%s\t%s\n", server.IP, server.Port, segment, key, v)
	}
}

// setConfigCmdMain  go run main.go config get
func setConfigCmdMain() {
	preRun(true)
	// get port list
	servers, err := getServerList(portList, dbmonConf.Config.Servers)
	if err != nil {
		mylog.Logger.Fatal("getServerList fail", zap.Error(err))
	}
	if len(servers) == 0 {
		mylog.Logger.Warn("no servers match", zap.String("portList", portList))
	}

	if segment == "" || key == "" {
		mylog.Logger.Fatal("segment or key is empty")
	}

	var updateCount int
	var oldValue string
	for _, server := range servers {
		oldValue, err = config.ClusterConfig.UpdateOne(&server, segment, key, value)
		if err != nil {
			mylog.Logger.Error(fmt.Sprintf("get config failed, segment:%s key:%s err:%v", segment, key, err))
			continue
		}
		updateCount += 1
		fmt.Printf("%s\t%d\t%s\t%s\t%q=>%q)\n", server.IP, server.Port, segment, key, oldValue, value)
	}

	if updateCount > 0 {
		if err := config.ClusterConfig.RewriteConfigFile(); err != nil {
			mylog.Logger.Error(fmt.Sprintf("write cluster config failed, err:%v", err))
		} else {
			mylog.Logger.Info("write cluster config success", zap.String("clusterConfigFile", clusterConfigFile))
		}
	}

}
