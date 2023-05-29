package iocrypt

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"os/exec"
	"time"

	"github.com/pkg/errors"
)

// FileEncrypter file encrypter
type FileEncrypter struct {
	CryptTool    EncryptTool
	CryptTimeout time.Duration
	stdin        io.WriteCloser
	stderr       bytes.Buffer
	cmd          *exec.Cmd
}

// InitWriter 包装 encrypt writer
// 会启动加密命令，等待标准输入。当 InitWriter 执行成功，写入结束后需要调用 Close 关闭 stdin
func (r *FileEncrypter) InitWriter(w io.Writer) error {
	var err error
	if r.cmd == nil {
		//if exec.LookPath(r.CryptTool.Name())
		r.cmd, err = r.CryptTool.BuildCommand(context.Background())
		if err != nil {
			return err
		}
		r.stdin, err = r.cmd.StdinPipe()
		if err != nil {
			return err
		}
		r.cmd.Stdout = w
		r.cmd.Stderr = &r.stderr
		//r.cmd.WaitDelay = 100 * time.Millisecond

		if err := r.cmd.Start(); err != nil {
			return err
		}
		time.Sleep(100 * time.Millisecond)
		go r.cmd.Wait()
		if r.cmd.ProcessState != nil && !r.cmd.ProcessState.Success() {
			return errors.Errorf("fail to start encrypt tool: %s", r.stderr.String())
		}
		// if ProcessState == nil means the process is still running
		if r.CryptTimeout == 0 {
			r.CryptTimeout = 999 * time.Hour
		}
	}
	return errors.WithStack(err)
}

// String for print
func (r *FileEncrypter) String() string {
	// may need to remove sensitive key
	return fmt.Sprintf("FileEncrypter{Cmd:%s, ExecTimeout:%s Suffix:%s}",
		r.cmd.String(), r.CryptTimeout, r.CryptTool.DefaultSuffix())
}

// Write implement io.Write
func (r *FileEncrypter) Write(p []byte) (int, error) {
	var err error
	if r.stdin == nil {
		return 0, errors.New("encrypt has no stdin to read from")
	}
	written, err := r.stdin.Write(p)
	//time.Sleep(0.5 * time.Second)
	return written, errors.WithStack(err)
}

// Close 关闭进程，会检查是否有错误输出
// 用户需要自己关闭外层的 file reader 和 writer, InitWriter 成功了才需要调用 Close
func (r *FileEncrypter) Close() error {
	_ = r.stdin.Close()
	if r.cmd.ProcessState == nil {
		return nil
	}
	if !r.cmd.ProcessState.Exited() {
		if err := r.cmd.Process.Kill(); err != nil {
			time.Sleep(100 * time.Millisecond)
			if !r.cmd.ProcessState.Exited() {
				return errors.Errorf("fail to clean encrypt process pid=%d", r.cmd.ProcessState.Pid())
			}
		} else {
			return nil
		}
	} else if r.cmd.ProcessState.ExitCode() > 0 {
		return errors.Errorf("encrypt tool exited with error: %s", r.stderr.String())
	}
	return nil
}
