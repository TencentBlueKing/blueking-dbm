package crond

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"os"
)

func DeployBinary(medium *components.Medium) (err error) {
	err = os.MkdirAll(cst.MySQLCrondInstallPath, 0755)
	if err != nil {
		logger.Error("mkdir %s failed: %s", cst.MySQLCrondInstallPath, err.Error())
		return err
	}

	decompressCmd := fmt.Sprintf(
		`tar zxf %s -C %s`,
		medium.GetAbsolutePath(), cst.MySQLCrondInstallPath,
	)
	_, err = osutil.ExecShellCommand(false, decompressCmd)
	if err != nil {
		logger.Error("decompress mysql-crond pkg failed: %s", err.Error())
		return err
	}

	chownCmd := fmt.Sprintf(`chown -R mysql %s`, cst.MySQLCrondInstallPath)
	_, err = osutil.ExecShellCommand(false, chownCmd)
	if err != nil {
		logger.Error("chown %s to mysql failed: %s", cst.MySQLCrondInstallPath, err.Error())
		return err
	}
	return nil
}
