package checksum

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"os"
	"path/filepath"
)

func DeployBinary(medium *components.Medium) (err error) {
	err = os.MkdirAll(cst.ChecksumInstallPath, 0755)
	if err != nil {
		logger.Error("mkdir %s failed: %s", cst.ChecksumInstallPath, err.Error())
		return err
	}

	decompressCmd := fmt.Sprintf(
		`tar zxf %s -C %s`,
		medium.GetAbsolutePath(), cst.ChecksumInstallPath,
	)
	_, err = osutil.ExecShellCommand(false, decompressCmd)
	if err != nil {
		logger.Error("decompress checksum pkg failed: %s", err.Error())
		return err
	}

	chownCmd := fmt.Sprintf(`chown -R mysql %s`, cst.ChecksumInstallPath)
	_, err = osutil.ExecShellCommand(false, chownCmd)
	if err != nil {
		logger.Error("chown %s to mysql failed: %s", cst.ChecksumInstallPath, err.Error())
		return err
	}

	chmodCmd := fmt.Sprintf(`chmod +x %s`, filepath.Join(cst.ChecksumInstallPath, "pt-table-checksum"))
	_, err = osutil.ExecShellCommand(false, chmodCmd)
	if err != nil {
		logger.Error("chmod pt-table-checksum failed: %s", err.Error())
		return err
	}

	chmodCmd = fmt.Sprintf(`chmod +x %s`, filepath.Join(cst.ChecksumInstallPath, "pt-table-sync"))
	_, err = osutil.ExecShellCommand(false, chmodCmd)
	if err != nil {
		logger.Error("chmod pt-table-sync failed: %s", err.Error())
		return err
	}

	chmodCmd = fmt.Sprintf(`chmod +x %s`, filepath.Join(cst.ChecksumInstallPath, "mysql-table-checksum"))
	_, err = osutil.ExecShellCommand(false, chmodCmd)
	if err != nil {
		logger.Error("chmod mysql-table-checksum failed: %s", err.Error())
		return err
	}

	return nil
}
