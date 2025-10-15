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
	"time"
)

type Password string
type Val string

// CmdBuilder 用于生成给sh执行的命令行, 生成命令行时，Password和Val会添加单引号
type CmdBuilder struct {
	Args []interface{}
}

// New NewCmdBuilder and append v
func New(v ...any) *CmdBuilder {
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
	if len(c.Args) == 0 {
		return "", nil
	}
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
	return RunCmdByBash(cmdLine, nil, timeout)
}

// Run2 Exec with timeout. and return ExecResult. set stdout, stderr to bytes.buffer
// stdout: bytes.Buffer, stderr: bytes.Buffer
// ret.GetStdout() return stdout.String()
// ret.GetStderr() return stderr.String()
func (c *CmdBuilder) Run(timeout time.Duration) (*ExecResult, error) {
	return c.Run3(timeout, bytes.NewBuffer(nil), bytes.NewBuffer(nil))
}

// Run3 Exec with timeout, stdout, stderr. and return ExecResult. set stdout, stderr to
func (c *CmdBuilder) Run3(timeout time.Duration, stdout, stderr io.Writer) (*ExecResult, error) {
	bin, args := c.GetCmd()
	ctx := context.Background()
	if timeout > 0 {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(context.Background(), timeout)
		defer cancel()
	}
	if stdout == nil {
		stdout = os.Stdout
	}
	if stderr == nil {
		stderr = os.Stderr
	}
	var ret = NewExecResult(stdout, stderr)
	ret.Start = time.Now()
	cmd := exec.CommandContext(ctx, bin, args...)
	cmd.Stdout = stdout
	cmd.Stderr = stderr
	err := cmd.Run()
	ret.End = time.Now()
	ret.Cmdline = c.GetCmdLine("", false)
	if cmd.ProcessState != nil {
		ret.ExitCode = cmd.ProcessState.ExitCode()
	} else {
		ret.ExitCode = -1
	}
	ret.Err = err
	return ret, err
}
