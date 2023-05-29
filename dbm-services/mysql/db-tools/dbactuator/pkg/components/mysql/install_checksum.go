package mysql

import (
	"bytes"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"os"
	"os/exec"
	"path"
	"time"

	"gopkg.in/yaml.v2"
)

// InstallMySQLChecksumComp 基本结构
type InstallMySQLChecksumComp struct {
	GeneralParam *components.GeneralParam   `json:"general"`
	Params       *InstallMySQLChecksumParam `json:"extend"`
	tools        *tools.ToolSet
}

// InstanceInfo 实例描述
type InstanceInfo struct {
	BkBizId      int    `json:"bk_biz_id"`
	Ip           string `json:"ip"`
	Port         int    `json:"port"`
	Role         string `json:"role"`
	ClusterId    int    `json:"cluster_id"`
	ImmuteDomain string `json:"immute_domain"`
	BkInstanceId int64  `json:"bk_instance_id,omitempty"` // 0 被视为空, 不序列化
}

// InstallMySQLChecksumParam 输入参数
type InstallMySQLChecksumParam struct {
	components.Medium
	SystemDbs     []string       `json:"system_dbs"`
	InstancesInfo []InstanceInfo `json:"instances_info"`
	ExecUser      string         `json:"exec_user"`
	Schedule      string         `json:"schedule"`
	ApiUrl        string         `json:"api_url"`
}

// Init 初始化
func (c *InstallMySQLChecksumComp) Init() (err error) {
	c.tools = tools.NewToolSetWithPickNoValidate(tools.ToolMysqlTableChecksum, tools.ToolPtTableChecksum)
	return nil
}

// Precheck 预检查
func (c *InstallMySQLChecksumComp) Precheck() (err error) {
	if err = c.Params.Medium.Check(); err != nil {
		logger.Error("check checksum pkg failed: %s", err.Error())
		return err
	}

	return nil
}

// DeployBinary 部署 mysql-table-checksum 和 pt-table-checksum
func (c *InstallMySQLChecksumComp) DeployBinary() (err error) {
	err = os.MkdirAll(cst.ChecksumInstallPath, 0755)
	if err != nil {
		logger.Error("mkdir %s failed: %s", cst.ChecksumInstallPath, err.Error())
		return err
	}

	decompressCmd := fmt.Sprintf(
		`tar zxf %s -C %s`,
		c.Params.Medium.GetAbsolutePath(), cst.ChecksumInstallPath,
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

	return nil
}

// GenerateBinaryConfig 生成 mysql-table-checksum 配置文件
func (c *InstallMySQLChecksumComp) GenerateBinaryConfig() (err error) {
	var configFs []*os.File
	defer func() {
		for _, f := range configFs {
			_ = f.Close()
		}
	}()

	logDir := path.Join(cst.ChecksumInstallPath, "logs")
	for _, instance := range c.Params.InstancesInfo {
		cfg := ChecksumConfig{
			BkBizId: instance.BkBizId,
			Cluster: _cluster{
				Id:           instance.ClusterId,
				ImmuteDomain: instance.ImmuteDomain,
			},
			Ip:         instance.Ip,
			Port:       instance.Port,
			User:       c.GeneralParam.RuntimeAccountParam.MonitorUser,
			Password:   c.GeneralParam.RuntimeAccountParam.MonitorPwd,
			InnerRole:  instance.Role,
			ReportPath: path.Join(cst.DBAReportBase, "checksum"),
			Filter: _ptFilters{
				IgnoreDatabases: c.Params.SystemDbs,
			},
			PtChecksum: _ptChecksum{
				Path:      c.tools.MustGet(tools.ToolPtTableChecksum),
				Replicate: fmt.Sprintf("%s.checksum", native.INFODBA_SCHEMA),
				Switches:  []string{},
				Args: []map[string]interface{}{
					{
						"name":  "run-time",
						"value": time.Hour * 2,
					},
				},
			},
			Log: &_logConfig{
				Console:    false,
				LogFileDir: &logDir,
				Debug:      false,
				Source:     true,
				Json:       true,
			},
			Schedule: c.Params.Schedule,
			ApiUrl:   c.Params.ApiUrl, // "http://127.0.0.1:9999",
		}

		yamlData, err := yaml.Marshal(&cfg)
		if err != nil {
			logger.Error("generate yaml config for %d failed: %s", instance.Port, err.Error())
			return err
		}

		f, err := os.OpenFile(
			path.Join(cst.ChecksumInstallPath, fmt.Sprintf("checksum_%d.yaml", instance.Port)),
			os.O_CREATE|os.O_TRUNC|os.O_WRONLY,
			0644,
		)
		if err != nil {
			logger.Error("create config file for %d failed: %s", instance.Port, err.Error())
			return err
		}
		configFs = append(configFs, f)

		_, err = f.Write(yamlData)
		if err != nil {
			logger.Error("write config file for %d failed: %s", instance.Port, err.Error())
			return err
		}

		_, err = osutil.ExecShellCommand(
			false,
			fmt.Sprintf(
				`chown mysql %s`,
				path.Join(cst.ChecksumInstallPath, fmt.Sprintf("checksum_%d.yaml", instance.Port)),
			),
		)
		if err != nil {
			logger.Error(
				"chown %s failed: %s",
				path.Join(cst.ChecksumInstallPath, fmt.Sprintf("checksum_%d.yaml", instance.Port)),
				err.Error(),
			)
			return err
		}
	}
	return nil
}

// AddToCrond 添加调度
func (c *InstallMySQLChecksumComp) AddToCrond() (err error) {
	mysqlTableChecksum, err := c.tools.Get(tools.ToolMysqlTableChecksum)
	if err != nil {
		logger.Error("get %s failed: %s", tools.ToolMysqlTableChecksum, err.Error())
		return err
	}

	for _, ins := range c.Params.InstancesInfo {
		command := exec.Command(
			mysqlTableChecksum,
			"reschedule",
			"--staff", c.Params.ExecUser,
			"--config",
			path.Join(
				cst.ChecksumInstallPath,
				fmt.Sprintf("checksum_%d.yaml", ins.Port),
			),
		)
		var stdout, stderr bytes.Buffer
		command.Stdout = &stdout
		command.Stderr = &stderr

		err := command.Run()
		if err != nil {
			logger.Error("run %s failed: %s, %s", command, err.Error(), stderr.String())
			return err
		}
		logger.Info("run %s success: %s", command, stdout.String())
	}
	return nil
}

// Example 样例
func (c *InstallMySQLChecksumComp) Example() interface{} {
	return InstallMySQLChecksumComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Params: &InstallMySQLChecksumParam{
			Medium: components.Medium{
				Pkg:    "mysql-table-checksum.tar.gz",
				PkgMd5: "12345",
			},
			SystemDbs: native.DBSys,
			InstancesInfo: []InstanceInfo{
				{
					BkBizId:      1,
					Ip:           "127.0.0.1",
					Port:         20000,
					Role:         "master",
					ClusterId:    12,
					ImmuteDomain: "aaa.bbb.com",
				},
				{
					BkBizId:      1,
					Ip:           "127.0.0.1",
					Port:         20001,
					Role:         "master",
					ClusterId:    12,
					ImmuteDomain: "aaa.bbb.com",
				},
			},
			ExecUser: "rtx",
			Schedule: "@every 5m",
			ApiUrl:   "http://x.x.x.x:yyyy",
		},
	}
}
