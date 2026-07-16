package process

import (
	"os"
	"os/exec"
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

	// gracefulDrainTimeout bounds how long the guard waits for the child to exit
	// gracefully after a stop request before falling back to ensureChildDead.
	gracefulDrainTimeout = 3 * time.Second
)

var (
	ErrExecutableEmpty = gerrors.Newf(gerrors.Failure, "Executable is empty")
)

// DaemonOptions configures StartDaemon.
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

type childWaitResult struct {
	state *os.ProcessState
	err   error
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

	cmd.SysProcAttr = newDetachedSysProcAttr()

	if err := cmd.Start(); err != nil {
		return nil, err
	}

	return cmd.Process, nil
}

func spawnChildWait(proc *os.Process) <-chan childWaitResult {
	waitDone := make(chan childWaitResult, 1)
	go func() {
		state, waitErr := proc.Wait()
		waitDone <- childWaitResult{state: state, err: waitErr}
	}()
	return waitDone
}

func ensureChildDead(childProc *os.Process) {
	for i := 0; i < 15; i++ {
		alive, _ := IsAlive(int32(childProc.Pid))
		if !alive {
			break
		}
		time.Sleep(200 * time.Millisecond)
	}
	alive, _ := IsAlive(int32(childProc.Pid))
	if alive {
		_ = childProc.Kill()
	}
}

// drainChildWait waits for the child's Wait() result up to timeout. On timeout it
// returns and lets the caller force-kill via ensureChildDead; the spawnChildWait
// goroutine still delivers to the buffered channel later, so no goroutine leaks.
func drainChildWait(waitDone <-chan childWaitResult, timeout time.Duration) {
	select {
	case <-waitDone:
	case <-time.After(timeout):
	}
}

func guardWaitForChild(
	waiter *StopWaiter,
	childProc *os.Process,
	waitDone <-chan childWaitResult,
) (state *os.ProcessState, waitErr error, stopRequested bool) {
	for {
		select {
		case result := <-waitDone:
			return result.state, result.err, false

		case <-waiter.Reload:
			// Forward reload to child (SIGHUP on Unix; no-op on Windows where
			// the worker listens on the reload event directly); keep waiting.
			if childProc != nil {
				forwardReloadToChild(childProc)
			}
			continue

		case <-waiter.Shutdown:
			// Stop requested: nudge child toward graceful shutdown, wait for
			// it to exit (bounded), force kill as a last resort, then exit the guard.
			guardStopChild(childProc)
			drainChildWait(waitDone, gracefulDrainTimeout)
			ensureChildDead(childProc)
			return nil, nil, true
		}
	}
}

// RunWithGuard runs a guard process that starts the target, monitors it, and restarts on abnormal exit.
// It blocks until a shutdown is requested (SIGTERM/SIGINT on Unix, the named stop event on Windows).
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

	// waiter delivers shutdown/reload notifications: POSIX signals on Unix, the
	// shared named stop/reload events on Windows (keyed off the pid file so the
	// stop command and this guard agree on the event names).
	waiter, err := NewStopWaiter(EventKeyFromPidFile(opt.PidFile))
	if err != nil {
		return err
	}
	defer waiter.Close()

	if err := SavePid(opt.PidFile); err != nil {
		return err
	}
	defer func() {
		_ = os.Remove(opt.PidFile)
	}()

	restartCount := 0
	eventKey := EventKeyFromPidFile(opt.PidFile)

	for {
		// Restart-race guard: if a stop was already requested (e.g. arrived
		// during the restart delay), do not relaunch; exit immediately.
		if isShutdownPending(waiter, eventKey) {
			return nil
		}

		proc, err := StartDaemon(daemonOpt)
		if err != nil {
			return err
		}

		state, waitErr, stopRequested := guardWaitForChild(waiter, proc, spawnChildWait(proc))
		if stopRequested {
			return nil
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
