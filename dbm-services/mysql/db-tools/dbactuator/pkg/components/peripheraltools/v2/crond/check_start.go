package crond

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"fmt"
	"os"
	"os/exec"
	"path"
	"time"

	"github.com/pkg/errors"
)

func (c *MySQLCrondComp) CheckStart() (err error) {
	/*
	   EXIT STATUS
	          0      One or more processes matched the criteria. For pkill the process must also have been successfully signalled.
	          1      No processes matched or none of them could be signalled.
	          2      Syntax error in the command line.
	          3      Fatal error: out of memory etc.
	*/
	for i := 0; i < 10; i++ {
		time.Sleep(5 * time.Second)

		cmd := exec.Command(
			"su", "mysql", "-c", "pgrep -x 'mysql-crond'")

		err = cmd.Run()
		if err != nil {
			var exitErr *exec.ExitError
			if errors.As(err, &exitErr) {
				if exitErr.ExitCode() == 1 {
					err = errors.Errorf("%d time check: mysql-crond process not found", i+1)
					logger.Warn(err.Error())
					continue // 没找到就重试
				} else {
					err = fmt.Errorf("run %s failed, exit code: %d",
						cmd.String(), exitErr.ExitCode())
					logger.Error(err.Error())
					return err
				}
			} else {
				logger.Error("find mysql-crond process failed: %s", err.Error())
				return err
			}
		}

		return nil // 如果能走到这里, 说明正常启动了
	}

	err = errors.Errorf("mysql-crond check start failed")

	startErrFilePath := path.Join(cst.MySQLCrondInstallPath, "start-crond.err")
	_, err = os.Stat(startErrFilePath)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			sterr := errors.Errorf("start mysql-crond failed without start-crond.err file")
			return sterr
		} else {
			sterr := errors.Wrapf(err, "get start-crond.err stat failed")
			logger.Error(sterr.Error())
			return sterr
		}
	}

	content, err := os.ReadFile(startErrFilePath)
	if err != nil {
		logger.Error("read mysql-crond.err", err.Error())
		return err
	}
	if len(content) > 0 {
		ferr := errors.Errorf("start-crond.err content: %s", string(content))
		logger.Error(ferr.Error())
		return ferr
	} else {
		err := errors.Errorf("start mysql-crond failed with empty start-crond.err")
		logger.Error(err.Error())
		return err
	}
}
