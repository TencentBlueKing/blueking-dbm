package process

import (
	"errors"
	"os"
	"syscall"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

type StopOptions struct {
	PidFile  string
	ProcName string
	Timeout  time.Duration
	Force    bool
}

var (
	ErrProcessNotRunning = gerrors.Newf(gerrors.NotExist, "process is not running")
)

// StopWithPidFile gracefully stops a process identified by pid file
func StopWithPidFile(opt StopOptions) error {
	pid, err := ReadPid(opt.PidFile)
	if err != nil {
		if errors.Is(err, ErrPidFileNotExist) || errors.Is(err, ErrInvalidFile) {
			return ErrProcessNotRunning
		}
		return err
	}

	alive, err := IsAliveWithProcessName(pid, opt.ProcName)
	if err != nil {
		return err
	}

	if !alive {
		return ErrProcessNotRunning
	}

	proc, err := os.FindProcess(int(pid))
	if err != nil {
		return gerrors.NewE(gerrors.Failure, err)
	}

	if err := proc.Signal(syscall.SIGTERM); err != nil {
		return gerrors.NewE(gerrors.Failure, err)
	}

	deadline := time.Now().Add(opt.Timeout)

	for {
		time.Sleep(200 * time.Millisecond)

		alive, err := IsAliveWithProcessName(pid, opt.ProcName)
		if err != nil {
			return err
		}

		if !alive {
			return nil
		}

		if time.Now().After(deadline) {
			break
		}
	}

	if !opt.Force {
		return gerrors.Newf(gerrors.Timeout, "stop process timeout after %s, pid=%d", opt.Timeout.String(), pid)
	}

	if err := proc.Signal(syscall.SIGKILL); err != nil {
		return gerrors.NewE(gerrors.Failure, err)
	}

	if opt.PidFile != "" {
		if err := os.Remove(opt.PidFile); err != nil && !os.IsNotExist(err) {
			return gerrors.NewE(gerrors.Failure, err)
		}
	}

	return nil
}
