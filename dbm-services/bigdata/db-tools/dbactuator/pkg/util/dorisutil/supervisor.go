package dorisutil

import (
	"fmt"
	"strings"
	"time"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

const (
	// supervisorCheckRetry 校验组件 RUNNING 的最大重试次数
	supervisorCheckRetry = 3
	// supervisorCheckInterval 每次校验之间的等待间隔
	supervisorCheckInterval = 5 * time.Second
)

// CheckComponentRunning 通过 supervisorctl status 校验指定组件是否处于 RUNNING 状态。
// 策略：每 supervisorCheckInterval 秒检查一次，最多检查 supervisorCheckRetry 次；
// 任一次输出第二列等于 "RUNNING" 即视为通过；全部失败返回 error。
//
// 注意：supervisorctl status <name> 在组件非 RUNNING 时退出码非 0，
// 因此不能因为 err != nil 就直接返回，必须看 stdout 输出再决定。
//
// supervisorctl status 输出格式：`<name> <STATE> <desc...>`，按 fields 取第二列严格匹配，
// 避免组件名/desc 中恰好出现 "RUNNING" 字面量被误判。
func CheckComponentRunning(component string) error {
	cmd := fmt.Sprintf("supervisorctl status %s", component)
	var lastOut string
	for i := 1; i <= supervisorCheckRetry; i++ {
		out, err := osutil.ExecShellCommand(false, cmd)
		lastOut = strings.TrimSpace(out)
		if isSupervisorRunning(lastOut) {
			logger.Info("component %s is RUNNING, status: %s", component, lastOut)
			return nil
		}
		logger.Warn("component %s not RUNNING (attempt %d/%d), status: %q, err: %v",
			component, i, supervisorCheckRetry, lastOut, err)
		if i < supervisorCheckRetry {
			time.Sleep(supervisorCheckInterval)
		}
	}
	return fmt.Errorf("component %s not RUNNING after %d retries, last status: %s",
		component, supervisorCheckRetry, lastOut)
}

// isSupervisorRunning 解析 supervisorctl status 的输出。
// 多行场景下，只要任一行第二列等于 "RUNNING"，即认为目标组件处于 RUNNING。
func isSupervisorRunning(out string) bool {
	for _, line := range strings.Split(out, "\n") {
		fields := strings.Fields(line)
		if len(fields) >= 2 && fields[1] == "RUNNING" {
			return true
		}
	}
	return false
}
