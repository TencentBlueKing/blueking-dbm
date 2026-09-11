//

package mysql

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path"
	"strings"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
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
	// ClearDBHAProbeConfig 是否执行清理 dbha 探针端口配置的逻辑，默认 false 表示跳过
	// 仅当置为 true 时，DoClearDBHAProbeConfig 才会真正执行清理动作
	ClearDBHAProbeConfig bool `json:"clear_dbha_probe_config"`
	// DBHAAdminEndpoints dbha 探针 gen-config 使用的 admin-endpoints，多个用逗号分隔
	// 仅在 ClearDBHAProbeConfig=true 时使用
	DBHAAdminEndpoints string `json:"dbha_admin_endpoints"`
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
	c.clearMySQLMonitor()

	err = c.clearChecksum()
	if err != nil {
		logger.Error("clear backend checksum failed: %s", err.Error())
		//return err
	}
	logger.Info("clear backend checksum success")

	err = c.clearRotateBinlog()
	if err != nil {
		logger.Error("clear backend rotate binlog failed: %s", err.Error())
		//return err
	}
	logger.Info("clear backend rotate binlog success")

	err = c.clearDbBackup()
	if err != nil {
		logger.Error("clear backend dbbackup failed: %s", err.Error())
		//return err
	}
	logger.Info("clear backend dbbackup success")

	return nil
}

func (c *ClearInstanceConfigComp) clearSingle() (err error) {
	c.clearMySQLMonitor()

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
	c.clearMySQLMonitor()
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
	installPath := cst.MysqlRotateBinlogInstallPath
	binPath := path.Join(installPath, string(tools.ToolMysqlRotatebinlog))
	configFile := path.Join(installPath, "main.yaml")

	if !cmutil.FileExists(binPath) {
		logger.Info("%s not exists, skip", binPath)
		return nil
	}
	clearPortString := util.IntSlice2String(c.Params.ClearPorts, ",")
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

func (c *ClearInstanceConfigComp) clearMySQLMonitor() {
	mysqlMonitor, err := c.tools.Get(tools.ToolMySQLMonitor)
	if err != nil {
		logger.Error("get %s failed: %s", tools.ToolMySQLMonitor, err.Error())
		return
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
			return
		}
		logger.Info("run %s success: %s", unInstallMySQLMonitorCmd, stdout.String())
	}

	logger.Info("remove mysql monitor config finish")
	return
}

// DoClearDBHAProbeConfig 清理 dbha 探针指定端口的配置
// 0. 若 ClearDBHAProbeConfig 开关未打开，则直接跳过（默认行为）
// 1. 若探针目录不存在，则跳过
// 2. 若 ClearPorts 为空，则跳过
// 3. 执行 ./bin/dbha-probe gen-config --clear-port <ports> 清理指定端口的配置
func (c *ClearInstanceConfigComp) DoClearDBHAProbeConfig() (err error) {
	if !c.Params.ClearDBHAProbeConfig {
		logger.Info("clear_dbha_probe_config is disabled, skip clear dbha probe config")
		return nil
	}

	probeDir := cst.DBHAProbeInstallDir
	if !cmutil.FileExists(probeDir) {
		logger.Info("probe not deployed on this host [%s], skip clear probe config", probeDir)
		return nil
	}

	if len(c.Params.ClearPorts) == 0 {
		logger.Info("clear_ports is empty, skip clear dbha probe config")
		return nil
	}

	if strings.TrimSpace(c.Params.DBHAAdminEndpoints) == "" {
		err = errors.Errorf("dbha_admin_endpoints is required for clearing dbha probe config")
		logger.Error(err.Error())
		return err
	}

	// 将端口列表转成逗号分隔的字符串，例如 [10000 20000] -> "10000,20000"
	clearPortString := util.IntSlice2String(c.Params.ClearPorts, ",")

	// 直接使用 argv 方式调用，避免走 shell 拼接导致 admin-endpoints 出现特殊字符时被截断/注入
	probeBin := path.Join(probeDir, "bin", "dbha-probe")
	probeCmd := exec.Command(
		probeBin,
		"gen-config",
		"--admin-endpoints", c.Params.DBHAAdminEndpoints,
		"--clear-port", clearPortString,
	)
	probeCmd.Dir = probeDir

	var stdout, stderr bytes.Buffer
	probeCmd.Stdout = &stdout
	probeCmd.Stderr = &stderr

	if err = probeCmd.Run(); err != nil {
		logger.Error("clear dbha probe config failed: %s, stderr: %s, stdout: %s",
			err.Error(), stderr.String(), stdout.String())
		return err
	}
	logger.Info("clear dbha probe config success [%s], output: %s",
		clearPortString, stdout.String())
	return nil
}
