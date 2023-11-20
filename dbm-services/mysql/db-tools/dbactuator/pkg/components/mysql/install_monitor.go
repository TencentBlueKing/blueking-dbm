package mysql

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"strconv"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"

	"github.com/pkg/errors"
	"gopkg.in/yaml.v2"
)

// InstallMySQLMonitorComp 安装 mysql monitor
type InstallMySQLMonitorComp struct {
	GeneralParam *components.GeneralParam  `json:"general"`
	Params       *InstallMySQLMonitorParam `json:"extend"`
	tools        *tools.ToolSet
}

// InstallMySQLMonitorParam 参数
type InstallMySQLMonitorParam struct {
	components.Medium
	SystemDbs     []string       `json:"system_dbs"`
	ExecUser      string         `json:"exec_user"`
	ApiUrl        string         `json:"api_url"`
	InstancesInfo []InstanceInfo `json:"instances_info"`
	MachineType   string         `json:"machine_type"`
	BkCloudId     int            `json:"bk_cloud_id"`
	ItemsConfig   map[string]struct {
		Enable      *bool    `json:"enable" yaml:"enable"`
		Schedule    *string  `json:"schedule" yaml:"schedule"`
		MachineType []string `json:"machine_type" yaml:"machine_type"`
		Role        []string `json:"role" yaml:"role"`
		Name        string   `json:"name" yaml:"name"`
	} `json:"items_config"`
}

type monitorItem struct {
	Name        string   `json:"name" yaml:"name"`
	Enable      *bool    `json:"enable" yaml:"enable"`
	Schedule    *string  `json:"schedule" yaml:"schedule"`
	MachineType []string `json:"machine_type" yaml:"machine_type"`
	Role        []string `json:"role" yaml:"role"`
}

type connectAuth struct {
	User     string `yaml:"user" validate:"required"`
	Password string `yaml:"password" validate:"required"`
}

type authCollect struct {
	Mysql      *connectAuth `yaml:"mysql"`
	Proxy      *connectAuth `yaml:"proxy"`
	ProxyAdmin *connectAuth `yaml:"proxy_admin"`
}

type monitorConfig struct {
	BkBizId         int           `yaml:"bk_biz_id"`
	Ip              string        `yaml:"ip" validate:"required,ipv4"`
	Port            int           `yaml:"port" validate:"required,gt=1024,lte=65535"`
	BkInstanceId    int64         `yaml:"bk_instance_id" validate:"required,gt=0"`
	ImmuteDomain    string        `yaml:"immute_domain"`
	MachineType     string        `yaml:"machine_type"`
	Role            *string       `yaml:"role"`
	BkCloudId       *int          `yaml:"bk_cloud_id" validate:"required,gte=0"`
	DBModuleID      *int          `yaml:"db_module_id" validate:"required"`
	Log             *_logConfig   `yaml:"log"`
	ItemsConfigFile string        `yaml:"items_config_file" validate:"required"`
	ApiUrl          string        `yaml:"api_url" validate:"required"`
	Auth            authCollect   `yaml:"auth"`
	DBASysDbs       []string      `yaml:"dba_sys_dbs" validate:"required"`
	InteractTimeout time.Duration `yaml:"interact_timeout" validate:"required"`
	DefaultSchedule string        `yaml:"default_schedule" validate:"required"`
}

// Init 初始化
func (c *InstallMySQLMonitorComp) Init() (err error) {
	c.tools = tools.NewToolSetWithPickNoValidate(tools.ToolMySQLMonitor)
	return nil
}

// Precheck 预检查
func (c *InstallMySQLMonitorComp) Precheck() (err error) {
	if err = c.Params.Medium.Check(); err != nil {
		logger.Error("check monitor pkg failed: %s", err.Error())
		return err
	}
	return nil
}

// DeployBinary 二进制部署
func (c *InstallMySQLMonitorComp) DeployBinary() (err error) {
	err = os.MkdirAll(cst.MySQLMonitorInstallPath, 0755)
	if err != nil {
		logger.Error("mkdir %s failed: %s", cst.MySQLCrondInstallPath, err.Error())
		return err
	}

	decompressCmd := fmt.Sprintf(
		`tar zxf %s -C %s`,
		c.Params.Medium.GetAbsolutePath(), cst.MySQLMonitorInstallPath,
	)
	_, err = osutil.ExecShellCommand(false, decompressCmd)
	if err != nil {
		logger.Error("decompress monitor pkg failed: %s", err.Error())
		return err
	}

	chownCmd := fmt.Sprintf(`chown -R mysql %s`, cst.MySQLMonitorInstallPath)
	_, err = osutil.ExecShellCommand(false, chownCmd)
	if err != nil {
		logger.Error("chown %s to mysql failed: %s", cst.MySQLMonitorInstallPath, err.Error())
		return err
	}

	chmodCmd := fmt.Sprintf(`chmod +x %s`, filepath.Join(cst.MySQLMonitorInstallPath, "pt-config-diff"))
	_, err = osutil.ExecShellCommand(false, chmodCmd)
	if err != nil {
		logger.Error("chmod pt-config-diff failed: %s", err.Error())
		return err
	}

	chmodCmd = fmt.Sprintf(`chmod +x %s`, filepath.Join(cst.MySQLMonitorInstallPath, "pt-summary"))
	_, err = osutil.ExecShellCommand(false, chmodCmd)
	if err != nil {
		logger.Error("chmod pt-summary failed: %s", err.Error())
		return err
	}

	chmodCmd = fmt.Sprintf(`chmod +x %s`, filepath.Join(cst.MySQLMonitorInstallPath, "mysql-monitor"))
	_, err = osutil.ExecShellCommand(false, chmodCmd)
	if err != nil {
		logger.Error("chmod mysql-monitor failed: %s", err.Error())
		return err
	}
	return nil
}

// GenerateBinaryConfig 生成 runtime 配置
func (c *InstallMySQLMonitorComp) GenerateBinaryConfig() (err error) {
	var configFs []*os.File
	defer func() {
		for _, f := range configFs {
			_ = f.Close()
		}
	}()

	logDir := path.Join(cst.MySQLMonitorInstallPath, "logs")
	for _, instance := range c.Params.InstancesInfo {
		if instance.BkInstanceId <= 0 {
			err := errors.Errorf(
				"%s:%d invalid bk_instance_id: %d",
				instance.Ip,
				instance.Port,
				instance.BkInstanceId,
			)
			return err
		}

		cfg := monitorConfig{
			Ip:           instance.Ip,
			Port:         instance.Port,
			BkInstanceId: instance.BkInstanceId,
			ImmuteDomain: instance.ImmuteDomain,
			Role:         &instance.Role,
			BkBizId:      instance.BkBizId,
			BkCloudId:    &c.Params.BkCloudId,
			DBModuleID:   &instance.DBModuleId,
			MachineType:  c.Params.MachineType,
			Log: &_logConfig{
				Console:    false,
				LogFileDir: &logDir,
				Debug:      false,
				Source:     true,
				Json:       true,
			},
			ItemsConfigFile: path.Join(
				cst.MySQLMonitorInstallPath,
				fmt.Sprintf("items-config_%d.yaml", instance.Port),
			),
			ApiUrl:          c.Params.ApiUrl,
			DBASysDbs:       c.Params.SystemDbs,
			InteractTimeout: 5 * time.Second,
			DefaultSchedule: "@every 1m",
		}

		switch c.Params.MachineType {
		case "backend":
			cfg.Auth = authCollect{
				Mysql: &connectAuth{
					User:     c.GeneralParam.RuntimeAccountParam.MonitorUser,
					Password: c.GeneralParam.RuntimeAccountParam.MonitorPwd,
				},
			}
		case "proxy":
			cfg.Auth = authCollect{
				ProxyAdmin: &connectAuth{
					User:     c.GeneralParam.RuntimeAccountParam.ProxyAdminUser,
					Password: c.GeneralParam.RuntimeAccountParam.ProxyAdminPwd,
				},
				Proxy: &connectAuth{
					User:     c.GeneralParam.RuntimeAccountParam.MonitorAccessAllUser,
					Password: c.GeneralParam.RuntimeAccountParam.MonitorAccessAllPwd,
				},
			}
		case "single":
			cfg.Auth = authCollect{
				Mysql: &connectAuth{
					User:     c.GeneralParam.RuntimeAccountParam.MonitorUser,
					Password: c.GeneralParam.RuntimeAccountParam.MonitorPwd,
				},
			}
		case "remote":
			cfg.Auth = authCollect{
				Mysql: &connectAuth{
					User:     c.GeneralParam.RuntimeAccountParam.MonitorUser,
					Password: c.GeneralParam.RuntimeAccountParam.MonitorPwd,
				},
			}
		case "spider":
			cfg.Auth = authCollect{
				Mysql: &connectAuth{
					User:     c.GeneralParam.RuntimeAccountParam.MonitorUser,
					Password: c.GeneralParam.RuntimeAccountParam.MonitorPwd,
				},
			}
		default:
			err := errors.Errorf("not support machine type: %s", c.Params.MachineType)
			logger.Error(err.Error())
			return err
		}

		yamlData, err := yaml.Marshal(&cfg)
		if err != nil {
			logger.Error("marshal monitor config for %d failed", instance.Port, err.Error())
			return err
		}

		f, err := os.OpenFile(
			path.Join(cst.MySQLMonitorInstallPath, fmt.Sprintf("monitor-config_%d.yaml", instance.Port)),
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
				path.Join(
					cst.MySQLMonitorInstallPath, fmt.Sprintf("monitor-config_%d.yaml", instance.Port),
				),
			),
		)
		if err != nil {
			logger.Error("chown config file for %d failed: %s", instance.Port, err.Error())
			return err
		}
	}
	return err
}

// GenerateItemsConfig 复制监控项配置
func (c *InstallMySQLMonitorComp) GenerateItemsConfig() (err error) {
	var monitorItems []monitorItem
	for k, v := range c.Params.ItemsConfig {
		monitorItems = append(
			monitorItems, monitorItem{
				Name:        k,
				Enable:      v.Enable,
				Schedule:    v.Schedule,
				MachineType: v.MachineType,
				Role:        v.Role,
			},
		)
	}

	content, err := yaml.Marshal(monitorItems)
	if err != nil {
		logger.Error("marshal items config failed: %s", err.Error())
		return err
	}

	for _, instance := range c.Params.InstancesInfo {
		f, err := os.OpenFile(
			path.Join(
				cst.MySQLMonitorInstallPath,
				fmt.Sprintf(`items-config_%d.yaml`, instance.Port),
			),
			os.O_CREATE|os.O_TRUNC|os.O_RDWR,
			0755,
		)
		if err != nil {
			logger.Error("create items-config file failed: %s", err.Error())
			return err
		}

		_, err = f.Write(append(content, []byte("\n")...))
		if err != nil {
			logger.Error("write items-config file faield: %s", err.Error())
			return err
		}
	}
	return nil
}

// CreateExporterCnf 根据mysql部署端口生成对应的exporter配置文件
func (c *InstallMySQLMonitorComp) CreateExporterCnf() (err error) {
	for _, inst := range c.Params.InstancesInfo {
		if c.Params.MachineType == "proxy" { // || inst.Role == ""
			// mysql-proxy 的exporter 还在 proxy-deploy 任务里
			continue
		}
		exporterConfName := fmt.Sprintf("/etc/exporter_%d.cnf", inst.Port)
		if err = util.CreateExporterConf(
			exporterConfName,
			inst.Ip,
			strconv.Itoa(inst.Port),
			c.GeneralParam.RuntimeAccountParam.MonitorUser,
			c.GeneralParam.RuntimeAccountParam.MonitorPwd,
		); err != nil {
			logger.Error("create exporter conf err : %s", err.Error())
			return err
		}
		// /etc/exporter_xxx.args is used to set mysqld_exporter collector args
		exporterArgsName := fmt.Sprintf("/etc/exporter_%d.args", inst.Port)
		if err = util.CreateMysqlExporterArgs(exporterArgsName, c.Params.GetPkgTypeName(), inst.Port); err != nil {
			logger.Error("create exporter collector args err : %s", err.Error())
			return err
		}
		if _, err = osutil.ExecShellCommand(false,
			fmt.Sprintf("chown -R mysql %s %s", exporterConfName, exporterArgsName)); err != nil {
			logger.Error("chown -R mysql %s %s : %s", exporterConfName, exporterArgsName, err.Error())
			return err
		}
	}
	return nil
}

// AddToCrond 添加 crond entry
func (c *InstallMySQLMonitorComp) AddToCrond() (err error) {
	mysqlMonitor, err := c.tools.Get(tools.ToolMySQLMonitor)
	if err != nil {
		logger.Error("get %s failed: %s", tools.ToolMySQLMonitor, err.Error())
		return err
	}

	for _, ins := range c.Params.InstancesInfo {
		command := exec.Command(
			mysqlMonitor,
			"reschedule",
			"--staff", c.Params.ExecUser,
			"--config", path.Join(
				cst.MySQLMonitorInstallPath,
				fmt.Sprintf("monitor-config_%d.yaml", ins.Port),
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
func (c *InstallMySQLMonitorComp) Example() interface{} {
	return InstallMySQLMonitorComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Params: &InstallMySQLMonitorParam{
			Medium: components.Medium{
				Pkg:    "mysql-monitor.tar.gz",
				PkgMd5: "12345",
			},
			SystemDbs: native.DBSys,
			ExecUser:  "whoru",
			ApiUrl:    "http://x.x.x.x:yyyy",
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
			MachineType: "backend",
			BkCloudId:   0,
		},
	}
}
