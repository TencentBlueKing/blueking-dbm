package osutil

import (
	"bufio"
	"bytes"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
	"sync"

	"dbm-services/common/go-pubpkg/logger"

	"github.com/pkg/errors"
)

// FileOutputCmd 封装exec.Command，用于执行命令并输出到文件的场景，支持自动将输出文件上传到文件服务器(尽可能上传，如果上传失败则返回原文件)
type FileOutputCmd struct {
	exec.Cmd
	StdOutFile string
	StdErrFile string

	stdOutFile         *os.File
	stdErrFile         *os.File
	stdOutDownloadLink string
	stdErrDownloadLink string
}

// GetStdOutDownloadLink TODO
func (c *FileOutputCmd) GetStdOutDownloadLink() string {
	return c.stdOutDownloadLink
}

// GetStdErrDownloadLink TODO
func (c *FileOutputCmd) GetStdErrDownloadLink() string {
	return c.stdErrDownloadLink
}

func (c *FileOutputCmd) initOutputFile() error {
	if c.StdErrFile == "" {
		c.StdErrFile = c.StdOutFile
	}
	if c.StdOutFile != "" {
		stdOutFile, err := os.OpenFile(c.StdOutFile, os.O_CREATE|os.O_WRONLY, os.ModePerm)
		if err != nil {
			return errors.Wrapf(err, "open std out log file %s failed", c.StdOutFile)
		}
		c.stdOutFile = stdOutFile
		c.Cmd.Stdout = stdOutFile
	}

	if c.StdOutFile == c.StdErrFile {
		c.stdErrFile = nil
		c.Cmd.Stderr = c.stdOutFile
		return nil
	}

	if c.StdErrFile != "" {
		stdErrFile, err := os.OpenFile(c.StdErrFile, os.O_CREATE|os.O_WRONLY, os.ModePerm)
		if err != nil {
			return errors.Wrapf(err, "open std err log file %s failed", c.StdErrFile)
		}
		c.stdErrFile = stdErrFile
		c.Cmd.Stderr = stdErrFile
	}
	return nil
}

func (c *FileOutputCmd) closeOutputFile() {
	if c.stdOutFile != nil {
		if err := c.stdOutFile.Close(); err != nil {
			logger.Warn("close %s failed, err:%s", c.StdOutFile, err.Error())
		}
	}
	if c.stdErrFile != nil {
		if err := c.stdErrFile.Close(); err != nil {
			logger.Warn("close %s failed, err:%s", c.StdErrFile, err.Error())
		}
	}
	// UploadPath?
	return
}

// Run TODO
func (c *FileOutputCmd) Run() error {
	if err := c.initOutputFile(); err != nil {
		return err
	}

	defer func() {
		c.closeOutputFile()
	}()

	return c.Cmd.Run()
}

// Start TODO
func (c *FileOutputCmd) Start() error {
	if err := c.initOutputFile(); err != nil {
		return err
	}

	return c.Cmd.Start()
}

// Wait TODO
func (c *FileOutputCmd) Wait() error {
	defer func() {
		c.closeOutputFile()
	}()

	return c.Cmd.Wait()
}

// RunInBG TODO
func RunInBG(isSudo bool, param string) (pid int, err error) {
	if isSudo {
		param = "sudo " + param
	}
	cmd := exec.Command("bash", "-c", param)
	err = cmd.Start()
	if err != nil {
		return -1, err
	}
	return cmd.Process.Pid, nil
}

// ExecShellCommand 执行 shell 命令
// 如果有 err, 返回 stderr; 如果没有 err 返回的是 stdout
// 后续尽量不要用这个方法,因为通过标准错误来判断有点不靠谱
func ExecShellCommand(isSudo bool, param string) (stdoutStr string, err error) {
	if isSudo {
		param = "sudo " + param
	}
	cmd := exec.Command("bash", "-c", param)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err = cmd.Run()
	if err != nil {
		// return stderr.String(), err
		return stderr.String(), errors.WithMessage(err, stderr.String())
	}

	if len(stderr.String()) > 0 {
		err = fmt.Errorf("execute shell command(%s) has stderr:%s", param, stderr.String())
		return stderr.String(), err
	}
	return stdout.String(), nil
}

// CleanExecShellOutput TODO
func CleanExecShellOutput(s string) string {
	return strings.ReplaceAll(strings.TrimSpace(s), "\n", "")
}

// StandardShellCommand TODO
func StandardShellCommand(isSudo bool, param string) (stdoutStr string, err error) {
	var stdout, stderr bytes.Buffer
	if isSudo {
		param = "sudo " + param
	}
	cmd := exec.Command("bash", "-c", param)
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err = cmd.Run()
	if err != nil {
		return stderr.String(), errors.WithMessage(err, stderr.String())
	}
	return stdout.String(), nil
}

// ComplexCommand 捕获标准错误和标准输出io copy 到需要文件里面
// 不影响正常的输出
type ComplexCommand struct {
	Command     string
	WriteStdout bool
	WriteStderr bool
	StdoutFile  string
	StderrFile  string
	Logger      bool
}

// Run Command Run
func (c *ComplexCommand) Run() (err error) {
	var stderrBuf bytes.Buffer
	var errStdout, errStderr error
	var stderrWs, stdoutWs []io.Writer
	cmd := exec.Command("/bin/bash", "-c", c.Command)
	stdoutIn, _ := cmd.StdoutPipe()
	stderrIn, _ := cmd.StderrPipe()
	// 写入error 文件
	if c.WriteStderr {
		ef, errO := os.OpenFile(c.StderrFile, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
		if errO != nil {
			logger.Warn("打开日志时失败! %s", errO.Error())
			return errO
		}
		defer ef.Close()
		defer ef.Sync()
		stderrWs = append(stderrWs, ef)
	}
	if c.WriteStdout {
		of, errO := os.OpenFile(c.StdoutFile, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
		if errO != nil {
			logger.Warn("打开日志时失败! %s", errO.Error())
			return errO
		}
		defer of.Close()
		defer of.Sync()
		stdoutWs = append(stdoutWs, of)
	}
	if c.Logger {
		reader, writer := io.Pipe()
		stderrWs = append(stderrWs, writer)
		stdoutWs = append(stdoutWs, writer)
		go func() {
			buf := []byte{}
			sc := bufio.NewScanner(reader)
			sc.Buffer(buf, 2048*1024)
			lineNumber := 1
			for sc.Scan() {
				logger.Info(sc.Text())
				lineNumber++
			}
			if err := sc.Err(); err != nil {
				logger.Error("something bad happened in the line %v: %v", lineNumber, err)
				return
			}
		}()
	}
	stdout := io.MultiWriter(stdoutWs...)
	stderr := io.MultiWriter(stderrWs...)

	if err = cmd.Start(); err != nil {
		logger.Error("start command failed:%s", err.Error())
		return err
	}

	var wg sync.WaitGroup
	wg.Add(1)

	go func() {
		_, errStdout = io.Copy(stdout, stdoutIn)
		wg.Done()
	}()

	_, errStderr = io.Copy(stderr, stderrIn)
	wg.Wait()

	if errStdout != nil {
		logger.Error("failed to capture stdout or stderr%v\n", errStdout)
		return errStdout
	}
	if errStderr != nil {
		logger.Error("failed to capture stderr or stderr,%v\n", errStderr)
		return errStderr
	}

	if err = cmd.Wait(); err != nil {
		errStr := string(stderrBuf.Bytes())
		logger.Error("exec failed:%s,stderr: %s", err.Error(), errStr)
		return err
	}

	return nil
}
