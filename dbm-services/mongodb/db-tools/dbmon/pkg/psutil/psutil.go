package psutil

import (
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mycmd"
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

	cmdCode, cmdStdOut, cmdStdErr, cmdErr := lsofCmd.Run(time.Second * 60)

	logger.Info(fmt.Sprintf("lsofCmd: %s, code: %d, stdout: %s, stderr: %s, err: %v",
		lsofCmd.GetCmdLine2(true), cmdCode, cmdStdOut, cmdStdErr, cmdErr))

	if cmdStdOut == "" {
		return 0, fmt.Errorf("failed to get pid")
	}
	cmdStdOut = strings.TrimSuffix(cmdStdOut, "\n")
	if pid, err = strconv.Atoi(cmdStdOut); err != nil {
		return 0, errors.Wrap(err, "failed to convert pid")
	}
	if pid == 0 {
		return 0, fmt.Errorf("invalid pid")
	}
	return pid, nil
}
