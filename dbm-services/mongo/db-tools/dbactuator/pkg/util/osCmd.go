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

	"dbm-services/mongo/db-tools/dbactuator/mylog"
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
			mylog.Logger.Error("RunLocalCmd create outfile fail,err:%v,outFile:%s", err, outFile)
			return "", fmt.Errorf("RunLocalCmd create outfile fail,err:%v,outFile:%s", err, outFile)
		}
		defer outFileHandler.Close()
		mylog.Logger.Info("RunLocalCmd create outfile(%s) success ...", outFile)
		cmdCtx.Stdout = outFileHandler
	}
	cmdCtx.Stderr = &errBuffer
	mylog.Logger.Debug("Running a new local cmd:%s,opts:%+v", cmd, opts)

	if err = cmdCtx.Start(); err != nil {
		mylog.Logger.Error("RunLocalCmd cmd Start fail,err:%v,cmd:%s,opts:%+v", err, cmd, opts)
		return "", fmt.Errorf("RunLocalCmd cmd Start fail,err:%v", err)
	}
	if dealPidMethod != nil {
		dealPidMethod.DealProcessPid(cmdCtx.Process.Pid)
	}
	if err = cmdCtx.Wait(); err != nil {
		mylog.Logger.Error("RunLocalCmd cmd wait fail,err:%v,errBuffer:%s,retBuffer:%s,cmd:%s,opts:%+v", err,
			errBuffer.String(), retBuffer.String(), cmd, opts)
		return "", fmt.Errorf("RunLocalCmd cmd wait fail,err:%v,detail:%s", err, errBuffer.String())
	}
	retStr = retBuffer.String()

	if strings.TrimSpace(errBuffer.String()) != "" {
		mylog.Logger.Error("RunLocalCmd fail,err:%v,cmd:%s,opts:%+v", errBuffer.String(), cmd, opts)
		err = fmt.Errorf("RunLocalCmd fail,err:%s", retBuffer.String()+"\n"+errBuffer.String())
	} else {
		err = nil
	}
	retStr = strings.TrimSpace(retStr)
	return
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
