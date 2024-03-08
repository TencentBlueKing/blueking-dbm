// Package mycmd  常用命令行工具
package mycmd

import (
	"bytes"
	"context"
	"fmt"
	"github.com/pkg/errors"
	"io"
	"os"
	"os/exec"
	"strings"
	"syscall"
	"time"
)

type arg struct {
	v     string
	isPwd bool
}

type Password string

// CmdBuilder 用于生成给sh执行的命令行,支持标记密码参数，用于生成不带密码的命令行
type CmdBuilder struct {
	Args []arg
}

// New NewCmdBuilder and append v
func New(v ...interface{}) *CmdBuilder {
	return NewCmdBuilder().AppendArg(v...)
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

// AppendArg Append interface arg
func (c *CmdBuilder) AppendArg(v ...interface{}) *CmdBuilder {
	for _, vv := range v {
		switch vv.(type) {
		case Password:
			_ = c.appendOne(string(vv.(Password)), true)
		case string:
			_ = c.appendOne(vv.(string), false)
		default:
			// 只接受string和Password类型。 不应该出现其他类型
			_ = c.appendOne(fmt.Sprintf("%v", vv), false)
		}

	}
	return c
}

// Append Append string arg
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

// GetCmdLine Get cmd line with suUser
// replacePassword 是否替换密码
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

// GetCmdLine2 Get cmd line 2
func (c *CmdBuilder) GetCmdLine2(replacePassword bool) string {
	return c.GetCmdLine("", replacePassword)
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

// RunBg run in background
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
