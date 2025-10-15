package mycmd

import (
	"bytes"
	"fmt"
	"io"
	"os"
	"time"

	"github.com/pkg/errors"
)

// ExecResult 用于记录mycmd.Run的执行结果
type ExecResult struct {
	Start          time.Time
	End            time.Time
	Cmdline        string
	Stdout, Stderr io.Writer
	ExitCode       int
	Err            error
}

func (e *ExecResult) GetStdout() string {
	switch v := e.Stdout.(type) {
	case *bytes.Buffer:
		return v.String()
	case *os.File:
		data, err := _readFile(v)
		if err != nil {
			return err.Error()
		}
		return string(data)
	default:
		return errors.New("type not supported").Error()
	}
}

func (e *ExecResult) GetStderr() string {
	switch v := e.Stderr.(type) {
	case *bytes.Buffer:
		return v.String()
	case *os.File:
		data, err := _readFile(v)
		if err != nil {
			return err.Error()
		}
		return string(data)
	default:
		return errors.New("type not supported").Error()
	}
}

// _readFile read file from os.File directly
// seek to 0
// read all
// return string, error
func _readFile(v *os.File) (string, error) {
	_, err := v.Seek(0, io.SeekStart)
	if err != nil {
		return "", errors.Wrap(err, "seek file failed from file "+v.Name())
	}
	bs, err := io.ReadAll(v)
	if err != nil {
		return "", errors.Wrap(err, "read file failed from file "+v.Name())
	}
	return string(bs), nil
}

// String return ExecResult string
func (e ExecResult) String() string {
	return fmt.Sprintf("Cmdline:%s\nStdout:%s\nStderr:%s\n", e.Cmdline, e.Stdout, e.Stderr)
}

// NewExecResult return ExecResult
func NewExecResult(out, err io.Writer) *ExecResult {
	o := &ExecResult{}
	o.Stdout = out
	o.Stderr = err
	return o
}
