// Package redistest redis test
package redistest

import (
	"fmt"
	"strconv"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// CheckPortUntilNotUse 检查端口直到其关闭
func CheckPortUntilNotUse(ip string, port int) {
	var isUse bool
	for {
		isUse, _ = util.CheckPortIsInUse(ip, strconv.Itoa(port))
		if isUse {
			fmt.Printf("%s:%d is using\n", ip, port)
			time.Sleep(time.Second)
			continue
		}
		break
	}
}

// StopRedisProcess 停止redis进程
func StopRedisProcess(ip string, port int, password, serverName string) (err error) {
	var stopCmd string
	var isUsing bool
	isUsing, _ = util.CheckPortIsInUse(ip, strconv.Itoa(port))
	if !isUsing {
		return nil
	}
	if util.FileExists("/usr/local/bin/stop-redis.sh") {
		stopCmd = fmt.Sprintf("cd /usr/local/redis && ./bin/stop-redis.sh %d %s", port, password)
		fmt.Println(stopCmd)
		util.RunBashCmd(stopCmd, "", nil, 10*time.Second)
	} else {
		killCmd := fmt.Sprintf("ps -ef | grep -w %s | grep %d | grep -v grep | awk '{print $2}'|xargs kill -9", serverName,
			port)
		fmt.Println(killCmd)
		util.RunBashCmd(killCmd, "", nil, 10*time.Second)
	}
	CheckPortUntilNotUse(ip, port)
	return nil
}
