package util

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"

	"dbm-services/mongodb/db-tools/dbmon/mylog"
)

// DealLocalCmdPid 处理本地命令得到pid
type DealLocalCmdPid interface {
	DealProcessPid(pid int) error
}

// RunBashCmd bash -c "$cmd" 执行命令并得到命令结果
func RunBashCmd(cmd, outFile string, dealPidMethod DealLocalCmdPid,
	timeout time.Duration) (retStr string, err error) {
	opts := []string{"-c", cmd}
	return RunLocalCmd("bash", opts, outFile, dealPidMethod, timeout)
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
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	cmdCtx := exec.CommandContext(ctx, cmd, opts...)
	var retBuffer bytes.Buffer
	var errBuffer bytes.Buffer
	defer func() {
		retBuffer.Reset()
		errBuffer.Reset()
	}()
	var outFileHandler *os.File
	if len(strings.TrimSpace(outFile)) == 0 {
		cmdCtx.Stdout = &retBuffer
	} else {
		outFileHandler, err = os.Create(outFile)
		if err != nil {
			mylog.Logger.Error(fmt.Sprintf("RunLocalCmd create outfile fail,err:%v,outFile:%s", err, outFile))
			return "", fmt.Errorf("RunLocalCmd create outfile fail,err:%v,outFile:%s", err, outFile)
		}
		defer outFileHandler.Close()
		mylog.Logger.Info(fmt.Sprintf("RunLocalCmd create outfile(%s) success ...", outFile))
		cmdCtx.Stdout = outFileHandler
	}
	cmdCtx.Stderr = &errBuffer
	mylog.Logger.Debug(fmt.Sprintf("Running a new local cmd:%s,opts:%+v", cmd, opts))

	if err = cmdCtx.Start(); err != nil {
		mylog.Logger.Error(fmt.Sprintf("RunLocalCmd cmd Start fail,err:%v,cmd:%s,opts:%+v", err, cmd, opts))
		return "", fmt.Errorf("RunLocalCmd cmd Start fail,err:%v", err)
	}
	if dealPidMethod != nil {
		dealPidMethod.DealProcessPid(cmdCtx.Process.Pid)
	}
	if err = cmdCtx.Wait(); err != nil {
		mylog.Logger.Error(fmt.Sprintf("RunLocalCmd cmd wait fail,err:%v,errBuffer:%s,retBuffer:%s,cmd:%s,opts:%+v",
			err, errBuffer.String(), retBuffer.String(), cmd, opts))
		return "", fmt.Errorf("RunLocalCmd cmd wait fail,err:%v", err)
	}
	retStr = retBuffer.String()
	if len(errBuffer.String()) > 0 {
		mylog.Logger.Error(fmt.Sprintf("RunLocalCmd fail,err:%v,cmd:%s,opts:%+v", errBuffer.String(), cmd, opts))
		err = fmt.Errorf("RunLocalCmd fail,err:%s", retBuffer.String()+"\n"+errBuffer.String())
	} else {
		err = nil
	}
	retStr = strings.TrimSpace(retStr)
	return
}

// RunBashCmdNoLog bash -c "$cmd" 执行命令并得到命令结果
func RunBashCmdNoLog(cmd, outFile string, dealPidMethod DealLocalCmdPid,
	timeout time.Duration) (retStr string, err error) {
	opts := []string{"-c", cmd}
	return RunLocalCmdNoLog("bash", opts, outFile, dealPidMethod, timeout)
}

// RunLocalCmdNoLog 不打印日志的RunLocalCmd
/*
 *参数:
 * outFile: 不为空,则将标准输出结果打印到outFile中;
 * dealPidMethod: 不为空,则将命令pid传给dealPidMethod.DealProcessPid()函数;
 * logger: 用于打印日志;
 */
func RunLocalCmdNoLog(
	cmd string, opts []string, outFile string,
	dealPidMethod DealLocalCmdPid, timeout time.Duration) (retStr string, err error) {
	ctx, cancel := context.WithTimeout(context.TODO(), timeout)
	defer cancel()

	cmdCtx := exec.CommandContext(ctx, cmd, opts...)
	var retBuffer bytes.Buffer
	var errBuffer bytes.Buffer
	var outFileHandler *os.File
	if len(strings.TrimSpace(outFile)) == 0 {
		cmdCtx.Stdout = &retBuffer
	} else {
		outFileHandler, err = os.Create(outFile)
		if err != nil {
			return "", fmt.Errorf("RunLocalCmd create outfile fail,err:%v,outFile:%s", err, outFile)
		}
		defer outFileHandler.Close()
		cmdCtx.Stdout = outFileHandler
	}
	cmdCtx.Stderr = &errBuffer

	if err = cmdCtx.Start(); err != nil {
		return "", fmt.Errorf("RunLocalCmd cmd Start fail,err:%v", err)
	}
	if dealPidMethod != nil {
		dealPidMethod.DealProcessPid(cmdCtx.Process.Pid)
	}
	if err = cmdCtx.Wait(); err != nil {
		return "", fmt.Errorf("RunLocalCmd cmd wait fail,err:%v", err)
	}
	retStr = retBuffer.String()
	if len(errBuffer.String()) > 0 {
		err = fmt.Errorf("RunLocalCmd fail,err:%s", retBuffer.String()+"\n"+errBuffer.String())
	} else {
		err = nil
	}
	retStr = strings.TrimSpace(retStr)
	return
}
