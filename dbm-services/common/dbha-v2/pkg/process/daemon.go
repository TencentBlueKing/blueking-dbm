package process

import (
	"os"
	"os/exec"
	"syscall"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

type DaemonOptions struct {
	Executable string
	Args       []string
	Env        []string
}

var (
	ErrExecutableEmpty = gerrors.Newf(gerrors.Failure, "Executable is empty")
)

// StartDaemon starts a new background process using the given executable
func StartDaemon(opt DaemonOptions) (*os.Process, error) {
	if opt.Executable == "" {
		return nil, ErrExecutableEmpty
	}

	cmd := exec.Command(opt.Executable, opt.Args...)

	if len(opt.Env) > 0 {
		cmd.Env = append(os.Environ(), opt.Env...)
	}

	cmd.SysProcAttr = &syscall.SysProcAttr{Setsid: true}

	if err := cmd.Start(); err != nil {
		return nil, err
	}

	return cmd.Process, nil
}
