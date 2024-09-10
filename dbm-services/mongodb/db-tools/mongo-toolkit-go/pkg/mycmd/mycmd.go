// Package mycmd  常用命令行工具
package mycmd

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
	"syscall"
	"time"

	"github.com/pkg/errors"
)

type Password string
type Val string

// CmdBuilder 用于生成给sh执行的命令行, 生成命令行时，Password和Val会添加单引号
type CmdBuilder struct {
	Args []interface{}
}

// New NewCmdBuilder and append v
func New(v ...interface{}) *CmdBuilder {
	return NewCmdBuilder().Append(v...)
}

// NewCmdBuilder  New CmdBuilder
func NewCmdBuilder() *CmdBuilder {
	c := CmdBuilder{}
	return &c
}

func (c *CmdBuilder) appendOne(v interface{}) *CmdBuilder {
	c.Args = append(c.Args, v)
	return c
}

// Append  string arg
func (c *CmdBuilder) Append(v ...interface{}) *CmdBuilder {
	for _, vv := range v {
		c.appendOne(vv)
	}
	return c
}

// AppendPassword Append password arg
func (c *CmdBuilder) AppendPassword(v string) *CmdBuilder {
	return c.appendOne(Password(v))
}

// argToString 生成命令行内容
// @replacePassword 将密码替换成xxx
// @isCmdLine 生成cmdline给bash调用的，为Val, Password添加”
func argToString(v interface{}, replacePassword bool, isCmdLine bool) string {
	switch v.(type) {
	case string:
		return fmt.Sprintf("%s", v)
	case int, int8, int16, int32, int64:
		return fmt.Sprintf("%d", v)
	case Val:
		if isCmdLine {
			return fmt.Sprintf("'%s'", v)
		} else {
			return fmt.Sprintf("%s", v)
		}
	case Password:
		if isCmdLine {
			if replacePassword {
				return "xxx"
			} else {
				return fmt.Sprintf(`'%s'`, v)
			}
		} else {
			if replacePassword {
				return "xxx"
			} else {
				return fmt.Sprintf(`%s`, v)
			}
		}
	default:
		panic(fmt.Sprintf("mycmd argToString bad type %T", v))
	}
}

// GetCmdLine Get cmd line with suUser
// replacePassword 是否替换密码
func (c *CmdBuilder) GetCmdLine(suUser string, replacePassword bool) string {
	tmpSlice := make([]string, 0, len(c.Args))
	for _, v := range c.Args {
		tmpSlice = append(tmpSlice, argToString(v, replacePassword, true))
	}
	cmdLine := strings.Join(tmpSlice, " ")
	if suUser != "" {
		return fmt.Sprintf(`su %s -c "%s"`, suUser, cmdLine)
	}
	return cmdLine
}

// GetCmdLine2 Get cmd line 2
func (c *CmdBuilder) GetCmdLine2(replacePassword bool) string {
	return c.GetCmdLine("", replacePassword)
}

// GetCmd Get cmd and args
func (c *CmdBuilder) GetCmd() (bin string, args []string) {
	bin = c.Args[0].(string)
	args = make([]string, 0, len(c.Args)-1)
	for _, argItem := range c.Args[1:] {
		args = append(args, argToString(argItem, false, false))
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
		ctx, cancel = context.WithTimeout(context.Background(), timeout)
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

// Run3 Exec with timeout. and return ExecResult
func (c *CmdBuilder) Run3(timeout time.Duration, stdout, stderr io.Writer) (*ExecResult, error) {
	bin, args := c.GetCmd()
	ctx := context.Background()
	if timeout > 0 {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(context.Background(), timeout)
		defer cancel()
	}
	stdoutBuffer := bytes.Buffer{}
	stderrBuffer := bytes.Buffer{}
	var ret = NewExecResult(&stdoutBuffer, &stderrBuffer)
	ret.Start = time.Now()
	cmd := exec.CommandContext(ctx, bin, args...)
	cmd.Stdout = stdout
	cmd.Stderr = stderr
	err := cmd.Run()
	ret.End = time.Now()
	ret.Cmdline = c.GetCmdLine("", false)
	return ret, err

}

// RunBackground run in background
func (c *CmdBuilder) RunBackground(outputFileName string) (pid int, err error) {
	bin, args := c.GetCmd()
	cmd := exec.Command(bin, args...)
	// 设置进程属性，使其在 Go 程序退出后继续运行
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Setpgid: true,
	}

	if outputFileName != "" {
		var outputFile *os.File
		if outputFile, err = os.Create(outputFileName); err != nil {
			err = errors.Wrap(err, "os.Create output.log")
			return
		} else {
			defer outputFile.Close()
			cmd.Stdout = outputFile
			cmd.Stderr = outputFile
		}
	}

	err = cmd.Start()
	if err != nil {
		err = errors.Wrap(err, "cmd.Start")
		return
	}
	pid = cmd.Process.Pid
	// 确保命令在后台运行
	err = cmd.Process.Release()
	if err != nil {
		err = errors.Wrap(err, "cmd.Process.Release")
		return
	}

	return pid, err

}
