package mycmd

import (
	"bytes"
	"context"
	"os"
	"os/exec"
	"strings"
	"syscall"
	"time"

	"github.com/pkg/errors"
)

const defaultExitCode = 1

// DealLocalCmdPid 处理本地命令得到pid
type DealLocalCmdPid interface {
	DealProcessPid(pid int) error
}

/*RunCmd 参数:
 * outFile: 不为空,则将标准输出结果打印到outFile中;
 * dealPidMethod: 不为空,则将命令pid传给dealPidMethod.DealProcessPid()函数;
 * exitCode https://stackoverflow.com/questions/10385551/get-exit-code-go
 */
func RunCmd(cmd string, opts []string, outFile string,
	dealPidMethod DealLocalCmdPid, timeout time.Duration) (exitCode int, stdout string, stderr string, err error) {
	exitCode = defaultExitCode
	ctx, cancel := context.WithTimeout(context.TODO(), timeout)
	defer cancel()

	cmdCtx := exec.CommandContext(ctx, cmd, opts...)
	var retBuffer bytes.Buffer
	var errBuffer bytes.Buffer
	var outFileHandler *os.File
	var useOutFile bool
	if len(strings.TrimSpace(outFile)) == 0 {
		cmdCtx.Stdout = &retBuffer
	} else {
		outFileHandler, err = os.Create(outFile)
		if err != nil {
			err = errors.Wrap(err, "CreateFile")
			return
		}
		defer outFileHandler.Close()
		cmdCtx.Stdout = outFileHandler
		useOutFile = true
	}
	cmdCtx.Stderr = &errBuffer

	if err = cmdCtx.Start(); err != nil {
		err = errors.Wrap(err, "Start")
		return
	}

	if dealPidMethod != nil {
		dealPidMethod.DealProcessPid(cmdCtx.Process.Pid)
	}

	if err = cmdCtx.Wait(); err != nil {
		if exitError, ok := err.(*exec.ExitError); ok {
			exitCode = exitError.Sys().(syscall.WaitStatus).ExitStatus()
		} else {
			exitCode = defaultExitCode
		}
	} else {
		ws := cmdCtx.ProcessState.Sys().(syscall.WaitStatus)
		exitCode = ws.ExitStatus()
	}

	if !useOutFile {
		stdout = retBuffer.String()
	}

	stderr = errBuffer.String()
	return
}

// RunCmdByBash bash -c "$cmd" 执行命令并得到命令结果
func RunCmdByBash(cmd, outFile string, dealPidMethod DealLocalCmdPid,
	timeout time.Duration) (exitCode int, stdout, stderr string, err error) {
	opts := []string{"-c", cmd}
	return RunCmd("bash", opts, outFile, dealPidMethod, timeout)
}
