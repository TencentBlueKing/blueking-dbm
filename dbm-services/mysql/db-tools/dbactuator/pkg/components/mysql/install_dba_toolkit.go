package mysql

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// InstallDBAToolkitComp 基本结构
type InstallDBAToolkitComp struct {
	Params InstallDBAToolkitParam `json:"extend"`
}

// InstallDBAToolkitParam 输入参数
type InstallDBAToolkitParam struct {
	components.Medium
	// 发起执行actor的用户，仅用于审计
	ExecUser string `json:"exec_user"`
}

// Init 初始化
func (c *InstallDBAToolkitComp) Init() (err error) {
	return nil
}

// PreCheck 预检查
func (c *InstallDBAToolkitComp) PreCheck() (err error) {
	if err = c.Params.Medium.Check(); err != nil {
		logger.Error("check dbatoolkit pkg failed: %s", err.Error())
		return err
	}
	return nil
}

// DeployBinary 部署 rotate_binlog
func (c *InstallDBAToolkitComp) DeployBinary() (err error) {
	decompressCmd := fmt.Sprintf(
		`tar zxf %s -C %s`,
		c.Params.Medium.GetAbsolutePath(), cst.MYSQL_TOOL_INSTALL_PATH,
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

// Example 样例
func (c *InstallDBAToolkitComp) Example() interface{} {
	return InstallDBAToolkitComp{
		Params: InstallDBAToolkitParam{
			Medium: components.Medium{
				Pkg:    "dba-toolkit.tar.gz",
				PkgMd5: "12345",
			},
			ExecUser: "sys",
		},
	}
}
