package process

import (
	"os"
	"os/exec"
	"os/signal"
	"syscall"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

const (
	// EnvUnderGuard is set when the child process is started by the guard.
	// When set, SavePid skips writing to avoid overwriting the guard's pid file.
	EnvUnderGuard = "DBHA_UNDER_GUARD"
	// EnvGuardProcess is set when the process is the forked guard (not the launcher).
	// When set, DaemonStartCmdRunE runs RunWithGuard directly instead of forking again.
	EnvGuardProcess = "DBHA_GUARD_PROCESS"
)

var (
	ErrExecutableEmpty = gerrors.Newf(gerrors.Failure, "Executable is empty")
)

type DaemonOptions struct {
	Executable string
	Args       []string
	Env        []string
}

// GuardOptions extends DaemonOptions with guard-specific settings.
type GuardOptions struct {
	DaemonOptions
	PidFile      string
	ProcName     string
	RestartDelay time.Duration
	OnRestart    func(exitCode int, restartCount int)
}

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

// RunWithGuard runs a guard process that starts the target, monitors it, and restarts on abnormal exit.
// It blocks until the guard receives SIGTERM or SIGINT.
func RunWithGuard(opt GuardOptions) error {
	if opt.Executable == "" {
		return ErrExecutableEmpty
	}
	if opt.PidFile == "" {
		return gerrors.Newf(gerrors.InvalidParameter, "PidFile is required for guard mode")
	}
	if opt.RestartDelay <= 0 {
		opt.RestartDelay = 3 * time.Second
	}

	// Inject DBHA_UNDER_GUARD so child skips SavePid
	env := append(opt.Env, EnvUnderGuard+"=1")
	daemonOpt := DaemonOptions{
		Executable: opt.Executable,
		Args:       opt.Args,
		Env:        env,
	}

	if err := SavePid(opt.PidFile); err != nil {
		return err
	}
	defer func() {
		_ = os.Remove(opt.PidFile)
	}()

	sigC := make(chan os.Signal, 1)
	signal.Notify(sigC, syscall.SIGTERM, syscall.SIGINT, syscall.SIGHUP)

	var childProc *os.Process
	restartCount := 0

	for {
		proc, err := StartDaemon(daemonOpt)
		if err != nil {
			return err
		}
		childProc = proc

		// Wait for either child exit or stop signal
		waitDone := make(chan struct {
			state *os.ProcessState
			err   error
		}, 1)
		go func() {
			state, waitErr := proc.Wait()
			waitDone <- struct {
				state *os.ProcessState
				err   error
			}{state, waitErr}
		}()

		var state *os.ProcessState
		var waitErr error
	waitLoop:
		for {
			select {
			case result := <-waitDone:
				state = result.state
				waitErr = result.err
				break waitLoop
			case sig := <-sigC:
				if sig == syscall.SIGHUP {
					// Forward SIGHUP to child for config reload; keep waiting
					if childProc != nil {
						_ = childProc.Signal(syscall.SIGHUP)
					}
					continue
				}
				// SIGTERM or SIGINT: kill child and exit
				_ = childProc.Signal(syscall.SIGTERM)
				<-waitDone // drain Wait

				// Ensure child is gone
				for i := 0; i < 15; i++ {
					alive, _ := IsAlive(int32(childProc.Pid))
					if !alive {
						break
					}
					time.Sleep(200 * time.Millisecond)
				}

				alive, _ := IsAlive(int32(childProc.Pid))
				if alive {
					_ = childProc.Signal(syscall.SIGKILL)
				}
				return nil
			}
		}

		exitCode := -1
		if state != nil {
			exitCode = state.ExitCode()
		}

		if waitErr != nil {
			exitCode = -1
		}

		restartCount++
		if opt.OnRestart != nil {
			opt.OnRestart(exitCode, restartCount)
		}

		time.Sleep(opt.RestartDelay)
	}
}
