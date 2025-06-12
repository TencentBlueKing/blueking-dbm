package mycmd

import (
	"context"
	"errors"
	"io"
	"os"
	"os/exec"
	"time"
)

// MyExec a exec wrapper
type MyExec struct {
	StartTime  time.Time
	EndTime    time.Time
	CmdBuilder *CmdBuilder
	ExecHandle *exec.Cmd
	CancelFunc context.CancelFunc
}

// NewMyExec creates a MyExec object
// cmdBuilder: command line builder
// timeout: timeout duration
// stdout: standard output
// stderr: standard error
// returns MyExec object and error
func NewMyExec(cmdBuilder *CmdBuilder, timeout time.Duration, stdout, stderr any, appendLog bool) (*MyExec, error) {
	e := &MyExec{
		CmdBuilder: cmdBuilder,
	}
	err := e.Prepare(timeout, stdout, stderr, appendLog)
	if err != nil {
		return nil, err
	}
	return e, nil
}

// Prepare prepares the command
// timeout: timeout duration
// stdout: standard output
// stderr: standard error
// returns error
func (e *MyExec) Prepare(timeout time.Duration, stdout, stderr any, appendLog bool) error {
	cmd, args := e.CmdBuilder.GetCmd()
	e.ExecHandle = exec.Command(cmd, args...)
	if timeout > 0 {
		ctx, cancel := context.WithTimeout(context.Background(), timeout)
		e.CancelFunc = cancel
		e.ExecHandle = exec.CommandContext(ctx, cmd, args...)
	}
	e.SetStdout(stdout, appendLog)
	e.SetStderr(stderr, appendLog)
	return nil
}

// SetStdout sets standard output
// stdout: standard output
// supports string(filePath), io.Writer, nil
// returns error
func (e *MyExec) SetStdout(stdout any, appendLog bool) error {
	if stdout == nil {
		return errors.New("stdout is nil")
	}
	switch v := stdout.(type) {
	case string:
		oFlag := os.O_CREATE | os.O_WRONLY
		if appendLog {
			oFlag |= os.O_APPEND
		}
		stdoutFile, err := os.OpenFile(v, oFlag, 0644)
		if err != nil {
			return err
		}
		e.ExecHandle.Stdout = stdoutFile

	case io.Writer:
		e.ExecHandle.Stdout = v
	default:
		return errors.New("stdout is not a valid type")
	}
	return nil
}

// SetStderr sets standard error
// stderr: standard error
// supports string(filePath), io.Writer, nil
// returns error
func (e *MyExec) SetStderr(stderr any, appendLog bool) error {
	if stderr == nil {
		return errors.New("stderr is nil")
	}
	switch v := stderr.(type) {
	case string:
		oFlag := os.O_CREATE | os.O_WRONLY
		if appendLog {
			oFlag |= os.O_APPEND
		}
		stderrFile, err := os.OpenFile(v, oFlag, 0644)
		if err != nil {
			return err
		}
		e.ExecHandle.Stderr = stderrFile
	case io.Writer:
		e.ExecHandle.Stderr = v
	default:
		return errors.New("stderr is not a valid type")
	}
	return nil
}

// SetStdin sets standard input
// stdin: standard input
// supports io.Reader, nil
// returns error
func (e *MyExec) SetStdin(stdin any) error {
	if stdin == nil {
		return errors.New("stdin is nil")
	}
	switch v := stdin.(type) {
	case io.Reader:
		e.ExecHandle.Stdin = v
	default:
		return errors.New("stdin is not a valid type")
	}
	return nil
}

// Start starts the command
// returns error
func (e *MyExec) Start() error {
	e.StartTime = time.Now()
	return e.ExecHandle.Start()
}

// Wait waits for the command to complete
// returns error
func (e *MyExec) Wait() error {
	err := e.ExecHandle.Wait()
	e.EndTime = time.Now()
	return err
}

// Run executes the command
// returns error
func (e *MyExec) Run() error {
	err := e.ExecHandle.Run()
	e.EndTime = time.Now()
	return err
}
