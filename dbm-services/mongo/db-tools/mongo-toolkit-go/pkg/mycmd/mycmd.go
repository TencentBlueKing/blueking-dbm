// Package mycmd  常用命令行工具
package mycmd

import (
	"bytes"
	"context"
	"fmt"
	"os/exec"
	"strings"
	"time"
)

type arg struct {
	v     string
	isPwd bool
}

// CmdBuilder 用于生成给sh执行的命令行,支持标记密码参数，用于生成不带密码的命令行
type CmdBuilder struct {
	Args []arg
}

// NewCmdBuilder  New CmdBuilder
func NewCmdBuilder() *CmdBuilder {
	c := CmdBuilder{}
	return &c
}

func (c *CmdBuilder) appendOne(v string, isPwd bool) *CmdBuilder {
	c.Args = append(c.Args, arg{v, isPwd})
	return c
}

// Append Append arg
func (c *CmdBuilder) Append(v ...string) *CmdBuilder {
	for _, vv := range v {
		_ = c.appendOne(vv, false)
	}
	return c
}

// AppendPassword Append password arg
func (c *CmdBuilder) AppendPassword(v string) *CmdBuilder {
	return c.appendOne(v, true)
}

// GetCmdLine Get cmd line
func (c *CmdBuilder) GetCmdLine(suUser string, replacePassword bool) string {
	tmpSlice := make([]string, 0, len(c.Args))
	for _, argItem := range c.Args {
		if replacePassword && argItem.isPwd {
			tmpSlice = append(tmpSlice, "xxx")
		} else {
			tmpSlice = append(tmpSlice, argItem.v)
		}
	}
	cmdLine := strings.Join(tmpSlice, " ")
	if suUser != "" {
		return fmt.Sprintf(`su %s -c "%s"`, suUser, cmdLine)
	}
	return cmdLine
}

// GetCmd Get cmd and args
func (c *CmdBuilder) GetCmd() (bin string, args []string) {
	bin = c.Args[0].v
	args = make([]string, 0, len(c.Args)-1)
	for _, argItem := range c.Args[1:] {
		args = append(args, argItem.v)
	}
	return
}

// RunByBash Exec cmd by bash with timeout. and return exitCode, stdout, stderr, error
func (c *CmdBuilder) RunByBash(suUser string, timeout time.Duration) (exitCode int, stdout, stderr string, err error) {
	cmdLine := c.GetCmdLine(suUser, false)
	return RunCmdByBash(cmdLine, "", nil, timeout)
}

// Run Exec with timeout. and return exitCode, stdout, stderr, error
func (c *CmdBuilder) Run(timeout time.Duration) (exitCode int, stdout, stderr string, err error) {
	cmd, args := c.GetCmd()
	return RunCmd(cmd, args, "", nil, timeout)
}

// Run2 Exec with timeout. and return ExecResult
func (c *CmdBuilder) Run2(timeout time.Duration) (*ExecResult, error) {
	bin, args := c.GetCmd()
	ctx := context.Background()
	if timeout > 0 {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(context.Background(), timeout*time.Second)
		defer cancel()
	}
	stdoutBuffer := bytes.Buffer{}
	stderrBuffer := bytes.Buffer{}
	var ret = NewExecResult(&stdoutBuffer, &stderrBuffer)
	ret.Start = time.Now()
	cmd := exec.CommandContext(ctx, bin, args...)
	cmd.Stdout = ret.Stdout
	cmd.Stderr = ret.Stderr
	err := cmd.Run()
	ret.End = time.Now()
	ret.Cmdline = c.GetCmdLine("", false)
	return ret, err

}
