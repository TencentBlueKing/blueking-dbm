package util

import (
	"fmt"
	"os"
	"strings"

	"dbm-services/common/go-pubpkg/logger"

	"github.com/pkg/errors"
)

const (
	// DefaultErrorExitCode TODO
	DefaultErrorExitCode = 1
)

// CheckErr prints a user friendly error to STDERR and exits with a non-zero
// exit code. Unrecognized errors will be printed with an "error: " prefix.
//
// This method is generic to the command in use and may be used by non-Kubectl
// commands.
func CheckErr(err error) {
	checkErr(err, fatalErrHandler)
}

var fatalErrHandler = fatal

// checkErr formats a given error as a string and calls the passed handleErr
// func with that string and an kubectl exit code.
func checkErr(err error, handleErr func(string, int)) {
	if err == nil {
		return
	}
	switch {
	case errors.Is(err, ErrExit):
		handleErr("", DefaultErrorExitCode)
	default:
		switch err := err.(type) {
		default: // for any other error type
			msg, ok := StandardErrorMessage(err)
			if !ok {
				msg = err.Error()
				if !strings.HasPrefix(msg, "error: ") {
					msg = fmt.Sprintf("error: %s", msg)
				}
			}
			handleErr(msg, DefaultErrorExitCode)
		}
	}
}

// fatal prints the message (if provided) and then exits. If V(99) or greater,
// klog.Fatal is invoked for extended information. This is intended for maintainer
// debugging and out of a reasonable range for users.
func fatal(msg string, code int) {
	// nolint:logcheck // Not using the result of klog.V(99) inside the if
	// branch is okay, we just use it to determine how to terminate.
	// if base.Logger.Level {
	// 	logger-back.Fatal(msg)
	// }

	if len(msg) > 0 {
		// add newline if needed
		if !strings.HasSuffix(msg, "\n") {
			msg += "\n"
		}
		fmt.Fprint(os.Stderr, msg)
	}
	os.Exit(code)
}

// ErrExit may be passed to CheckError to instruct it to output nothing but exit with
// status code 1.
var ErrExit = fmt.Errorf("exit")

type debugError interface {
	DebugError() (msg string, args []interface{})
}

// StandardErrorMessage translates common errors into a human readable message, or returns
// false if the error is not one of the recognized types. It may also log extended
// information to klog.
//
// This method is generic to the command in use and may be used by non-Kubectl
// commands.
func StandardErrorMessage(err error) (string, bool) {
	if debugErr, ok := err.(debugError); ok {
		logger.Info(debugErr.DebugError())
	}
	return "", false
}
