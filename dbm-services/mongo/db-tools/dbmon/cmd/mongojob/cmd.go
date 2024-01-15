package mongojob

import (
	"bytes"
	"context"
	"fmt"
	"os/exec"
	"strings"
	"time"

	log "dbm-services/mongo/db-tools/dbmon/mylog"
)

// ExecResult DoCommandWithTimeout 的返回结果
type ExecResult struct {
	Start   time.Time
	End     time.Time
	Cmdline string
	Stdout  bytes.Buffer
	Stderr  bytes.Buffer
}

// DoCommandWithTimeout do command with timeout
func DoCommandWithTimeout(timeout int, bin string, args ...string) (*ExecResult, error) {
	ctx := context.Background()
	if timeout > 0 {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(context.Background(), time.Duration(timeout)*time.Second)
		defer cancel()
	}
	var ret = ExecResult{}
	ret.Start = time.Now()
	cmd := exec.CommandContext(ctx, bin, args...)
	cmd.Stdout = &ret.Stdout
	cmd.Stderr = &ret.Stderr
	err := cmd.Run()
	ret.End = time.Now()
	ret.Cmdline = fmt.Sprintf("%s %s", bin, strings.Join(args, " "))
	return &ret, err
}

// ExecJs 执行Mongodb脚本
func ExecJs(bin string, timeout int, host, port, user, pass, authDB, scriptContent string) ([]byte, []byte, error) {
	args := []string{"--quiet", "--host", host, "--port", port}
	if user != "" {
		args = append(args, "--username", user, "--password", pass, "--authenticationDatabase", authDB)
	}
	args = append(args, "--eval", scriptContent)
	out, err := DoCommandWithTimeout(timeout, bin, args...)
	argLen := len(args)
	log.Logger.Debug(fmt.Sprintf("exec %s %s return %s\n", bin, args[:argLen-2], out.Stdout.Bytes()))
	log.Logger.Debug(fmt.Sprintf("scriptContent %s\n", scriptContent))
	return out.Stdout.Bytes(), out.Stderr.Bytes(), err
}

// ExecLoginJs 执行脚本, 用户密码在eval传入
func ExecLoginJs(bin string, timeout int, host, port, user, pass, authDB, scriptContent string) ([]byte, []byte,
	error) {
	args := []string{"--quiet", "--host", host, "--port", port}
	args = append(args, "--eval", fmt.Sprintf("var user='%s';var pwd='%s';%s", user, pass, scriptContent))
	out, err := DoCommandWithTimeout(timeout, bin, args...)
	argLen := len(args)
	log.Logger.Debug(fmt.Sprintf("exec %s %s return %s\n", bin, args[:argLen-2], out.Stdout.Bytes()))
	// log.Logger.Debug(fmt.Sprintf("scriptContent %s\n", scriptContent))
	return out.Stdout.Bytes(), out.Stderr.Bytes(), err
}
