package psutil

import (
	"dbm-services/common/go-pubpkg/mycmd"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/pkg/errors"
	"go.uber.org/zap"
)

func GetPidByPort(port int, logger *zap.Logger) (pid int, err error) {
	lsofCmd := mycmd.NewCmdBuilder().Append("lsof", "-i",
		fmt.Sprintf(":%d", port), "-t", "-sTCP:LISTEN")

	o, err := lsofCmd.Run(time.Second * 60)
	if err != nil {
		return 0, errors.Wrap(err, "failed to get pid")
	}
	if logger != nil {
		logger.Info(fmt.Sprintf("lsofCmd: %s, code: %d, stdout: %s, stderr: %s, err: %v",
			lsofCmd.GetCmdLine2(true), o.ExitCode, o.GetStdout(), o.GetStderr(), o.Err))
	}

	if o.GetStdout() == "" {
		return 0, fmt.Errorf("failed to get pid")
	}
	cmdStdOut := strings.TrimSuffix(o.GetStdout(), "\n")
	if pid, err = strconv.Atoi(cmdStdOut); err != nil {
		return 0, errors.Wrap(err, "failed to convert pid")
	}
	if pid == 0 {
		return 0, fmt.Errorf("invalid pid")
	}
	return pid, nil
}
