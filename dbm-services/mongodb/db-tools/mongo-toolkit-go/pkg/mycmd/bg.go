package mycmd

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"strings"
	"time"
)

// ExecResult 执行结果
type ExecResult struct {
	Start          time.Time
	End            time.Time
	Cmdline        string
	OutBuf, ErrBuf *bytes.Buffer
	Stdout, Stderr io.Writer
	Err            error
}

// String return ExecResult string
func (e ExecResult) String() string {
	return fmt.Sprintf("Cmdline:%s\nStdout:%s\nStderr:%s\n", e.Cmdline, e.Stdout, e.Stderr)
}

// NewExecResult return ExecResult
func NewExecResult(out, err *bytes.Buffer) *ExecResult {
	o := &ExecResult{
		OutBuf: out,
		ErrBuf: err,
	}
	o.Stdout = o.OutBuf
	o.Stderr = o.ErrBuf
	return o
}

// ExecCmdBg Exec cmd at background
type ExecCmdBg struct {
	PidChan  chan int
	DoneChan chan struct{}
	Ret      *ExecResult
}

// NewExecCmdBg return ExecCmdBg
func NewExecCmdBg() *ExecCmdBg {
	ret := NewExecResult(bytes.NewBuffer(nil), bytes.NewBuffer(nil))

	return &ExecCmdBg{
		PidChan:  make(chan int, 1),
		DoneChan: make(chan struct{}, 1),
		Ret:      ret,
	}
}

func newFileWriter(f string) io.Writer {
	if f == "" {
		return nil
	}
	fh, err := os.OpenFile(f, os.O_CREATE|os.O_WRONLY, 0666)
	if err != nil {
		log.Printf("OpenFile %v", err)
		return nil
	}
	return fh
}

// SetOutputFile set output file
func (e *ExecCmdBg) SetOutputFile(out, err string) {
	e.Ret.Stdout = newFileWriter(out)
	e.Ret.Stderr = newFileWriter(err)
}

// SetOutput set output
func (e *ExecCmdBg) SetOutput(out, err io.Writer) {
	e.Ret.Stdout = out
	e.Ret.Stderr = err
}

func (e *ExecCmdBg) run(timeoutSecond int, bin string, args []string) {
	e.Ret.Start = time.Now()
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeoutSecond)*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, bin, args...)
	cmd.Stdout = e.Ret.Stdout
	cmd.Stderr = e.Ret.Stderr
	if e.Ret.Err = cmd.Start(); e.Ret.Err != nil {
		e.PidChan <- 0
		e.DoneChan <- struct{}{}
		return
	}
	e.PidChan <- cmd.Process.Pid // 传递pid给调用者.
	e.Ret.Err = cmd.Wait()
	e.Ret.End = time.Now()
	e.Ret.Cmdline = fmt.Sprintf("%s %s", bin, strings.Join(args, " "))
	e.DoneChan <- struct{}{}
	return
}

// Run run cmd at background
func (e *ExecCmdBg) Run(timeoutSecond int, bin string, args []string) {
	go e.run(timeoutSecond, bin, args)
}

// Wait wait for cmd exit
func (e *ExecCmdBg) Wait() {
	<-e.DoneChan
}

// WaitForStart wait for cmd start
func (e *ExecCmdBg) WaitForStart() {
	<-e.PidChan
}
