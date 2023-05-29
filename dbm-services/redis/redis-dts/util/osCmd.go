package util

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"

	"go.uber.org/zap"
)

// DealLocalCmdPid 处理本地命令得到pid
type DealLocalCmdPid interface {
	DealProcessPid(pid int) error
}

// RunLocalCmd 运行本地命令并得到命令结果
func RunLocalCmd(
	cmd string, opts []string, outFile string,
	dealPidMethod DealLocalCmdPid,
	timeout time.Duration, logger *zap.Logger) (retStr string, err error) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
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
			logger.Error("RunLocalCmd create outfile fail", zap.Error(err), zap.String("outFile", outFile))
			return "", fmt.Errorf("RunLocalCmd create outfile fail,err:%v,outFile:%s", err, outFile)
		}
		defer outFileHandler.Close()
		logger.Info("RunLocalCmd create outfile success ...", zap.String("outFile", outFile))
		cmdCtx.Stdout = outFileHandler
	}
	cmdCtx.Stderr = &errBuffer
	logger.Debug("Running a new local command", zap.String("cmd", cmd), zap.Strings("opts", opts))

	if err = cmdCtx.Start(); err != nil {
		logger.Error("RunLocalCmd cmd Start fail", zap.Error(err), zap.String("cmd", cmd), zap.Strings("opts", opts))
		return "", fmt.Errorf("RunLocalCmd cmd Start fail,err:%v", err)
	}
	if dealPidMethod != nil {
		dealPidMethod.DealProcessPid(cmdCtx.Process.Pid)
	}
	if err = cmdCtx.Wait(); err != nil {
		logger.Error("RunLocalCmd cmd wait fail", zap.Error(err),
			zap.String("errBuffer", errBuffer.String()),
			zap.String("retBuffer", retBuffer.String()),
			zap.String("cmd", cmd), zap.Strings("opts", opts))
		return "", fmt.Errorf("RunLocalCmd cmd wait fail,err:%v", err)
	}
	retStr = retBuffer.String()
	if len(errBuffer.String()) > 0 {
		logger.Error("RunLocalCmd fail", zap.String("err", errBuffer.String()),
			zap.String("cmd", cmd), zap.Strings("opts", opts))
		err = fmt.Errorf("RunLocalCmd fail,err:%s", retBuffer.String()+"\n"+errBuffer.String())
	} else {
		err = nil
	}
	retStr = strings.TrimSpace(retStr)
	return
}
