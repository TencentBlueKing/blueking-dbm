package util

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

	"dbm-services/redis/db-tools/dbmon/mylog"
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

// watchTimeoutKillGroup 超时后 kill 整个进程组.
// bash -c 启动的 grandchildren(如 tendis-key-lifecycle 工具 fork 出的 monitor 子进程)
// 不会随父进程被 exec.CommandContext 一起杀掉, 会残留并持有文件锁(flock),
// 导致当天后续所有分析全部拿锁失败; 故子进程以独立进程组启动, 超时时对整组 SIGKILL
func watchTimeoutKillGroup(ctx context.Context, cmdCtx *exec.Cmd) {
	go func() {
		<-ctx.Done()
		// 仅在真正超时(而非命令正常结束后的 cancel)时清理进程组
		if ctx.Err() != context.DeadlineExceeded {
			return
		}
		if cmdCtx.Process != nil {
			if err := syscall.Kill(-cmdCtx.Process.Pid, syscall.SIGKILL); err != nil {
				mylog.Logger.Warn(fmt.Sprintf("kill process group(-%d) failed:%v", cmdCtx.Process.Pid, err))
			}
		}
	}()
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
	// 独立进程组启动, 配合 watchTimeoutKillGroup 超时整组清理
	cmdCtx.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	if err = cmdCtx.Start(); err != nil {
		mylog.Logger.Error(fmt.Sprintf("RunLocalCmd cmd Start fail,err:%v,cmd:%s", err, cmd))
		return "", fmt.Errorf("RunLocalCmd cmd Start fail,err:%v", err)
	}
	watchTimeoutKillGroup(ctx, cmdCtx)
	if dealPidMethod != nil {
		dealPidMethod.DealProcessPid(cmdCtx.Process.Pid)
	}
	if err = cmdCtx.Wait(); err != nil {
		mylog.Logger.Error(fmt.Sprintf("RunLocalCmd cmd wait fail,err:%v,errBuffer:%s,retBuffer:%s,cmd:%s",
			err, errBuffer.String(), retBuffer.String(), cmd))
		return "", fmt.Errorf("RunLocalCmd cmd wait fail,err:%v", err)
	}
	retStr = retBuffer.String()
	if len(errBuffer.String()) > 0 {
		mylog.Logger.Error(fmt.Sprintf("RunLocalCmd fail,err:%v,cmd:%s", errBuffer.String(), cmd))
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
			mylog.Logger.Warn(fmt.Sprintf("write into pipe failed, err:%v", err))
		}
		if err := stdin.Close(); err != nil {
			mylog.Logger.Warn(fmt.Sprintf("colse stdin failed, err:%v", err))
		}
	}()
	if output, err := cmd.CombinedOutput(); err != nil {
		err = fmt.Errorf("run chpasswd failed, output:%s, err:%v", string(output), err)
		mylog.Logger.Error(err.Error())
		return err
	}
	return nil
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
			return "", fmt.Errorf("RunLocalCmd create outfile fail,err:%v,outFile:%s", err, outFile)
		}
		defer outFileHandler.Close()
		cmdCtx.Stdout = outFileHandler
	}
	cmdCtx.Stderr = &errBuffer
	// 独立进程组启动, 配合 watchTimeoutKillGroup 超时整组清理
	cmdCtx.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	if err = cmdCtx.Start(); err != nil {
		return "", fmt.Errorf("RunLocalCmd cmd Start fail,err:%v", err)
	}
	watchTimeoutKillGroup(ctx, cmdCtx)
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
