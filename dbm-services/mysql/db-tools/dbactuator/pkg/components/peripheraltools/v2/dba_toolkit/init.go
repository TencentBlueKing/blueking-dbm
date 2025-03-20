package dba_toolkit

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
)

func DeployBinary(medium *components.Medium) (err error) {
	decompressCmd := fmt.Sprintf(
		`tar zxf %s -C %s`,
		medium.GetAbsolutePath(), cst.MYSQL_TOOL_INSTALL_PATH,
	)
	_, err = osutil.ExecShellCommand(false, decompressCmd)
	if err != nil {
		logger.Error("decompress dbatoolkit pkg failed: %s", err.Error())
		return err
	}

	chownCmd := fmt.Sprintf(`chown -R mysql %s`, cst.DBAToolkitPath)
	_, err = osutil.ExecShellCommand(false, chownCmd)
	if err != nil {
		logger.Error("chown %s to mysql failed: %s", cst.DBAToolkitPath, err.Error())
		return err
	}

	return nil
}
