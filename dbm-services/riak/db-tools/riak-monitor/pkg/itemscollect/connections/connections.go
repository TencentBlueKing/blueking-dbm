package connections

import (
	"dbm-services/riak/db-tools/riak-monitor/pkg/utils"
	"fmt"
	"strings"

	"golang.org/x/exp/slog"
)

// Connections riak实例上的连接
func Connections() (string, error) {
	localIp, err := utils.GetLocalIP()
	if err != nil {
		errInfo := fmt.Sprintf("get local ip error: %s", err.Error())
		slog.Error(errInfo)
		return "", fmt.Errorf(errInfo)
	}
	// 使用netstat查看端口上的连接
	cmd := `netstat -anpl|grep ':8087' | grep "beam.smp" | grep -E -v '0.0.0.0:*'`
	// 剔除本机上的蓝鲸监控连接，返回连接数
	cmd = fmt.Sprintf(`%s | awk '{ if (index($5,"%s:") == 0) { print $0 } }' | wc -l`, cmd, localIp)
	resp, err := utils.ExecShellCommand(false, cmd)
	if err != nil {
		errInfo := fmt.Sprintf("execute [ %s ] error: %s", cmd, err.Error())
		slog.Error(errInfo)
		return "", fmt.Errorf(errInfo)
	}
	resp = strings.Replace(resp, " ", "", -1)
	resp = strings.Replace(resp, "\n", "", -1)
	return resp, nil
}
