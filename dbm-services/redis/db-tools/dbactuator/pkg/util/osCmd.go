package util

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/mylog"
)

// DealLocalCmdPid 处理本地命令得到pid
type DealLocalCmdPid interface {
	DealProcessPid(pid int) error
}

// RunBashCmd bash -c "$cmd" 执行命令并得到命令结果
func RunBashCmd(cmd, outFile string, dealPidMethod DealLocalCmdPid,
	timeout time.Duration) (retStr string, err error) {
	return NewSafeOsCmd(cmd, nil, outFile, dealPidMethod, timeout).RunBashCmd()
}

// RunLocalCmd 运行本地命令并得到命令结果
/*
 *参数:
 * outFile: 不为空,则将标准输出结果打印到outFile中;
 * dealPidMethod: 不为空,则将命令pid传给dealPidMethod.DealProcessPid()函数;
 * logger: 用于打印日志;
 */
func RunLocalCmd(
	cmd string, opts []string, outFile string,
	dealPidMethod DealLocalCmdPid, timeout time.Duration) (retStr string, err error) {
	return NewSafeOsCmd(cmd, opts, outFile, dealPidMethod, timeout).RunLocalCmd()
}

func RunBashCmdReplacePkey(cmd, pkey, outFile string, dealPidMethod DealLocalCmdPid,
	timeout time.Duration) (retStr string, err error) {
	return NewSafeOsCmd(cmd, nil, outFile, dealPidMethod, timeout).SetPKey(pkey).RunBashCmd()
}

func RunLocalCmdReplacePkey(
	cmd string, opts []string, pkey string, outFile string,
	dealPidMethod DealLocalCmdPid, timeout time.Duration) (retStr string, err error) {
	return NewSafeOsCmd(cmd, opts, outFile, dealPidMethod, timeout).SetPKey(pkey).RunLocalCmd()
}

// SetOSUserPassword run set user password by chpasswd
func SetOSUserPassword(user, password string) error {
	exec.Command("/bin/bash", "-c", "")
	cmd := exec.Command("chpasswd")
	stdin, err := cmd.StdinPipe()
	if err != nil {
		return fmt.Errorf("new pipe failed, err:%w", err)
	}
	go func() {
		_, err := io.WriteString(stdin, fmt.Sprintf("%s:%s", user, password))
		if err != nil {
			mylog.Logger.Warn("write into pipe failed, err:%s", err.Error())
		}
		if err := stdin.Close(); err != nil {
			mylog.Logger.Warn("colse stdin failed, err:%s", err.Error())
		}
	}()
	if output, err := cmd.CombinedOutput(); err != nil {
		err = fmt.Errorf("run chpasswd failed, output:%s, err:%w", string(output), err)
		mylog.Logger.Error(err.Error())
		return err
	}
	return nil
}

type SafeOsCmd struct {
	cmd           string
	opts          []string
	outFile       string
	dealPidMethod DealLocalCmdPid
	timeout       time.Duration

	// 替换关键字
	replaceKey string
	logOpts    []string
}

func NewSafeOsCmd(cmd string, opts []string, outFile string,
	dealPidMethod DealLocalCmdPid, timeout time.Duration) *SafeOsCmd {
	return &SafeOsCmd{
		cmd:           cmd,
		opts:          opts,
		outFile:       outFile,
		dealPidMethod: dealPidMethod,
		timeout:       timeout,
	}
}

func (safeCmd *SafeOsCmd) replace() {
	if safeCmd.replaceKey == "" {
		safeCmd.logOpts = safeCmd.opts
		return
	}
	for _, s := range safeCmd.opts {
		safeCmd.logOpts = append(safeCmd.logOpts, strings.ReplaceAll(s, safeCmd.replaceKey, "xxxxxx"))
	}
}

func (safeCmd *SafeOsCmd) SetCmd(cmd string) {
	safeCmd.cmd = cmd
}

func (safeCmd *SafeOsCmd) SetOpts(opts []string) {
	safeCmd.opts = opts
}

func (safeCmd *SafeOsCmd) SetPKey(passwordKey string) *SafeOsCmd {
	safeCmd.replaceKey = passwordKey
	return safeCmd
}

func (safeCmd *SafeOsCmd) RunBashCmd() (retStr string, err error) {
	safeCmd.SetOpts([]string{"-c", safeCmd.cmd})
	safeCmd.SetCmd("bash")
	return safeCmd.RunLocalCmd()
}

func (safeCmd *SafeOsCmd) RunLocalCmd() (retStr string, err error) {
	safeCmd.replace()
	ctx, cancel := context.WithTimeout(context.TODO(), safeCmd.timeout)
	defer cancel()

	cmdCtx := exec.CommandContext(ctx, safeCmd.cmd, safeCmd.opts...)
	var retBuffer bytes.Buffer
	var errBuffer bytes.Buffer
	var outFileHandler *os.File
	if len(strings.TrimSpace(safeCmd.outFile)) == 0 {
		cmdCtx.Stdout = &retBuffer
	} else {
		outFileHandler, err = os.Create(safeCmd.outFile)
		if err != nil {
			mylog.Logger.Error("RunLocalCmd create outfile fail,err:%v,outFile:%s", err, safeCmd.outFile)
			return "", fmt.Errorf("RunLocalCmd create outfile fail,err:%v,outFile:%s", err, safeCmd.outFile)
		}
		defer outFileHandler.Close()
		mylog.Logger.Info("RunLocalCmd create outfile(%s) success ...", safeCmd.outFile)
		cmdCtx.Stdout = outFileHandler
	}
	cmdCtx.Stderr = &errBuffer
	mylog.Logger.Debug("Running a new local cmd:%s,opts:%+v", safeCmd.cmd, safeCmd.logOpts)

	if err = cmdCtx.Start(); err != nil {
		mylog.Logger.Error("RunLocalCmd cmd Start fail,err:%v,cmd:%s,opts:%+v", err, safeCmd.cmd, safeCmd.logOpts)
		return "", fmt.Errorf("RunLocalCmd cmd Start fail,err:%v", err)
	}
	if safeCmd.dealPidMethod != nil {
		safeCmd.dealPidMethod.DealProcessPid(cmdCtx.Process.Pid)
	}
	if err = cmdCtx.Wait(); err != nil {
		mylog.Logger.Error("RunLocalCmd cmd wait fail,err:%v,errBuffer:%s,retBuffer:%s,cmd:%s,opts:%+v", err,
			errBuffer.String(), retBuffer.String(), safeCmd.cmd, safeCmd.logOpts)
		return "", fmt.Errorf("RunLocalCmd cmd wait fail,err:%v,detail:%s", err, errBuffer.String())
	}
	retStr = retBuffer.String()

	if strings.TrimSpace(errBuffer.String()) != "" {
		mylog.Logger.Error("RunLocalCmd fail,err:%v,cmd:%s,opts:%+v", errBuffer.String(), safeCmd.cmd, safeCmd.logOpts)
		err = fmt.Errorf("RunLocalCmd fail,err:%s", retBuffer.String()+"\n"+errBuffer.String())
	} else {
		err = nil
	}
	retStr = strings.TrimSpace(retStr)
	return
}
