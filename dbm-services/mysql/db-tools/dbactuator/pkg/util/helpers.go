package util

import (
	"fmt"
	"os"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
)

const (
	// DefaultErrorExitCode TODO
	DefaultErrorExitCode = 1
)

// CheckErr TODO
func CheckErr(err error) {
	if err == nil {
		return
	}
	msg, ok := StandardErrorMessage(err)
	if !ok {
		msg = err.Error()
		if !strings.HasPrefix(msg, "error: ") {
			msg = fmt.Sprintf("error: %s", msg)
		}
	}
	LoggerErrorStack(logger.Error, err)
	fatal(msg, DefaultErrorExitCode)
}

func fatal(msg string, code int) {
	if len(msg) > 0 {
		// add newline if needed
		if !strings.HasSuffix(msg, "\n") {
			msg += "\n"
		}
		fmt.Fprint(os.Stderr, msg)
	}
	os.Exit(code)
}

type debugError interface {
	DebugError() (msg string, args []interface{})
}

// StandardErrorMessage TODO
func StandardErrorMessage(err error) (string, bool) {
	if debugErr, ok := err.(debugError); ok {
		logger.Info(debugErr.DebugError())
	}
	return "", false
}
