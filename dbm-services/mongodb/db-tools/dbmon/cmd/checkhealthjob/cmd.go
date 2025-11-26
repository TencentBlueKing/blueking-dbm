package checkhealthjob

import (
	"bytes"
	"dbm-services/common/go-pubpkg/mycmd"
	"fmt"
	"time"

	"go.uber.org/zap"
)

// ExecResult DoCommandWithTimeout 的返回结果
type ExecResult struct {
	Start   time.Time
	End     time.Time
	Cmdline string
	Stdout  bytes.Buffer
	Stderr  bytes.Buffer
}

// ExecLoginJsNoDb 执行脚本, 用户密码在eval传入, 不进行数据库认证
func ExecLoginJsNoDb(bin string, timeout int, host, port, user, pass, authDB, scriptContent string,
	logger *zap.Logger) (string, string, error) {
	jsCmd := mycmd.New(bin, "--quiet", "--nodb", "--eval",
		fmt.Sprintf("var addr='%s:%s';var user='%s';var pwd='%s';%s", host, port, user, pass, scriptContent))
	out, err := jsCmd.Run(time.Duration(timeout) * time.Second)
	logger.Debug(fmt.Sprintf("exec %s %s return stdout: %s, stderr: %s, err: %v",
		bin, jsCmd.GetCmdLine("", false), out.GetStdout(), out.GetStderr(), err))
	return out.GetStdout(), out.GetStderr(), err
}
