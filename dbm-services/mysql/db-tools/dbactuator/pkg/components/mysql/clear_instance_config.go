//

package mysql

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"

	"github.com/pkg/errors"
)

// ClearInstanceConfigComp 清理实例配置
type ClearInstanceConfigComp struct {
	GeneralParam *components.GeneralParam  `json:"general"`
	Params       *ClearInstanceConfigParam `json:"extend"`
	tools        *tools.ToolSet
}

// ClearInstanceConfigParam 定义原子任务的入参属性
type ClearInstanceConfigParam struct {
	ClearPorts  []int  `json:"clear_ports" validate:"required,gt=0,dive"`
	MachineType string `json:"machine_type"`
}

// Example 样例
func (c *ClearInstanceConfigComp) Example() interface{} {
	comp := ClearInstanceConfigComp{
		Params: &ClearInstanceConfigParam{
			ClearPorts: []int{20000, 20001},
		},
	}
	return comp
}

// Init 初始化工具集
func (c *ClearInstanceConfigComp) Init() (err error) {
	c.tools = tools.NewToolSetWithPickNoValidate(tools.ToolMysqlTableChecksum, tools.ToolMySQLMonitor)
	return nil
}

// DoClear 清理配置
func (c *ClearInstanceConfigComp) DoClear() (err error) {
	if c.Params.MachineType == "backend" || c.Params.MachineType == "remote" {
		return c.clearBackend()
	} else if c.Params.MachineType == "proxy" {
		return c.clearProxy()
	} else if c.Params.MachineType == "single" {
		return c.clearSingle()
	} else {
		err = errors.Errorf("unsupported machine type %s", c.Params.MachineType)
		logger.Error(err.Error())
		return err
	}
}

func (c *ClearInstanceConfigComp) clearBackend() (err error) {
	err = c.clearMySQLMonitor()
	if err != nil {
		logger.Error("clear backend monitor failed: %s", err.Error())
		return err
	}
	logger.Info("clear backed monitor success")

	err = c.clearChecksum()
	if err != nil {
		logger.Error("clear backend checksum failed: %s", err.Error())
		return err
	}
	logger.Info("clear backend checksum success")

	err = c.clearRotateBinlog()
	if err != nil {
		logger.Error("clear backend rotate binlog failed: %s", err.Error())
		return err
	}
	logger.Info("clear backend rotate binlog success")

	err = c.clearDbBackup()
	if err != nil {
		logger.Error("clear backend dbbackup failed: %s", err.Error())
		return err
	}
	logger.Info("clear backend dbbackup success")

	return nil
}

func (c *ClearInstanceConfigComp) clearSingle() (err error) {
	err = c.clearMySQLMonitor()
	if err != nil {
		logger.Error("clear backend monitor failed: %s", err.Error())
		return err
	}
	logger.Info("clear backed monitor success")

	err = c.clearRotateBinlog()
	if err != nil {
		logger.Error("clear backend rotate binlog failed: %s", err.Error())
		return err
	}
	logger.Info("clear backend rotate binlog success")

	err = c.clearDbBackup()
	if err != nil {
		logger.Error("clear backend dbbackup failed: %s", err.Error())
		return err
	}
	logger.Info("clear backend dbbackup success")

	return nil
}

func (c *ClearInstanceConfigComp) clearProxy() (err error) {
	err = c.clearMySQLMonitor()
	if err != nil {
		logger.Error("clear proxy monitor failed: %s", err.Error())
		return err
	}
	logger.Info("clear proxy monitor success")

	return nil
}

func (c *ClearInstanceConfigComp) clearDbBackup() (err error) {
	// 删除实例的备份配置
	installBackupPath := path.Join(cst.MYSQL_TOOL_INSTALL_PATH, cst.BackupDir)

	for _, port := range c.Params.ClearPorts {
		backupFile := path.Join(installBackupPath, cst.GetNewConfigByPort(port))
		err := os.Remove(backupFile)
		if os.IsNotExist(err) {
			// 检测文件是否存在，如果不存在则跳过
			logger.Warn("检测文件已不存在，跳过 %s", backupFile)
			continue
		}
		if err != nil {
			logger.Error("删除文件失败[%s]:%s", backupFile, err.Error())
			return err
		}
		logger.Info("备份文件已移除 [%s]", backupFile)
	}
	return nil
}

func (c *ClearInstanceConfigComp) clearChecksum() (err error) {
	mysqlTableChecksum, err := c.tools.Get(tools.ToolMysqlTableChecksum)
	if err != nil {
		logger.Warn("get %s failed: %s", tools.ToolMysqlTableChecksum, err.Error())
		return nil
	}

	for _, port := range c.Params.ClearPorts {
		unInstallTableChecksum := exec.Command(
			mysqlTableChecksum,
			"clean",
			"--config", path.Join(
				cst.ChecksumInstallPath,
				fmt.Sprintf("checksum_%d.yaml", port),
			),
		)
		var stdout, stderr bytes.Buffer
		unInstallTableChecksum.Stdout = &stdout
		unInstallTableChecksum.Stderr = &stderr

		err = unInstallTableChecksum.Run()
		if err != nil {
			logger.Error(
				"run %s failed: %s, %s",
				unInstallTableChecksum, err.Error(), stderr.String(),
			)
			return err
		}
		logger.Info("run %s success: %s", unInstallTableChecksum, stdout.String())
	}
	return nil
}

func (c *ClearInstanceConfigComp) clearRotateBinlog() (err error) {
	// 删除实例的rotate_binlog配置
	installPath := path.Join(cst.MYSQL_TOOL_INSTALL_PATH, "rotate_binlog")
	binPath := path.Join(installPath, string(tools.ToolRotatebinlog))
	configFile := path.Join(installPath, "config.yaml")

	clearPortString := strings.Replace(strings.Trim(fmt.Sprint(c.Params.ClearPorts), "[]"), " ", ",", -1)
	cmd := fmt.Sprintf(
		`%s -c %s --removeConfig %s`, binPath, configFile, clearPortString,
	)

	_, err = osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("remove rotate binlog config failed: %s", err.Error())
		return err
	}
	logger.Info("remove rotate binlog config success [%s]", clearPortString)
	return nil
}

func (c *ClearInstanceConfigComp) clearMySQLMonitor() (err error) {
	mysqlMonitor, err := c.tools.Get(tools.ToolMySQLMonitor)
	if err != nil {
		logger.Error("get %s failed: %s", tools.ToolMySQLMonitor, err.Error())
		return err
	}

	for _, port := range c.Params.ClearPorts {
		unInstallMySQLMonitorCmd := exec.Command(
			mysqlMonitor,
			"clean",
			"--config", path.Join(
				cst.MySQLMonitorInstallPath,
				fmt.Sprintf("monitor-config_%d.yaml", port),
			),
		)
		var stdout, stderr bytes.Buffer
		unInstallMySQLMonitorCmd.Stdout = &stdout
		unInstallMySQLMonitorCmd.Stderr = &stderr

		err = unInstallMySQLMonitorCmd.Run()
		if err != nil {
			logger.Error(
				"run %s failed: %s, %s",
				unInstallMySQLMonitorCmd, err.Error(), stderr.String(),
			)
			return err
		}
		logger.Info("run %s success: %s", unInstallMySQLMonitorCmd, stdout.String())
	}
	return nil
}
