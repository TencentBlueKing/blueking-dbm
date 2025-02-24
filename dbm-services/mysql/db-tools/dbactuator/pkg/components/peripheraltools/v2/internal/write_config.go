package internal

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"os"
)

func WriteConfig(cfgFilePath string, content []byte) error {
	f, err := os.OpenFile(
		cfgFilePath,
		os.O_CREATE|os.O_TRUNC|os.O_WRONLY,
		0644,
	)
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	defer func() {
		_ = f.Close()
	}()

	_, err = f.Write(content)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	_, err = osutil.ExecShellCommand(false, fmt.Sprintf(`chown mysql %s`, cfgFilePath))
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	return nil
}
