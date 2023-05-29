package mysql

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/backup"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/rotate"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path"
	"path/filepath"
	"reflect"

	"github.com/ghodss/yaml"
	"github.com/mitchellh/mapstructure"
	"github.com/pkg/errors"
	"github.com/spf13/cast"
)

// InstallRotateBinlogComp 基本结构
type InstallRotateBinlogComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       InstallRotateBinlogParam `json:"extend"`
	configFile   string
	binPath      string
	installPath  string
}

// InstallRotateBinlogParam 输入参数
type InstallRotateBinlogParam struct {
	components.Medium
	Configs rotate.Config `json:"configs" validate:"required"` // 模板配置
	// 本机的所有实例信息。用户密码将从 general 参数获取
	Instances []*rotate.ServerObj `json:"instances"`
	// 发起执行actor的用户，仅用于审计
	ExecUser string `json:"exec_user"`
}

// Init 初始化
func (c *InstallRotateBinlogComp) Init() (err error) {
	c.Params.Configs.Servers = c.Params.Instances
	for _, s := range c.Params.Configs.Servers {
		s.Username = c.GeneralParam.RuntimeAccountParam.MonitorUser
		s.Password = c.GeneralParam.RuntimeAccountParam.MonitorPwd
		var instObj = native.InsObject{
			Host: s.Host, Port: s.Port, User: s.Username, Pwd: s.Password, Socket: s.Socket,
		}
		if dbw, err := instObj.Conn(); err != nil {
			logger.Error("install mysql-rotatebinlog test connect failed: %s. instance:%+v", err.Error(), *s)
			// return err
		} else {
			dbw.Stop()
		}
	}
	c.installPath = filepath.Join(cst.MYSQL_TOOL_INSTALL_PATH, "mysql-rotatebinlog")
	c.binPath = filepath.Join(c.installPath, string(tools.ToolRotatebinlog))
	return nil
}

// PreCheck 预检查
func (c *InstallRotateBinlogComp) PreCheck() (err error) {
	if err = c.Params.Medium.Check(); err != nil {
		logger.Error("check mysql-rotatebinlog pkg failed: %s", err.Error())
		return err
	}
	return nil
}

// DeployBinary 部署 mysql-rotatebinlog
func (c *InstallRotateBinlogComp) DeployBinary() (err error) {
	err = os.MkdirAll(filepath.Join(c.installPath, "logs"), 0755)
	if err != nil {
		logger.Error("mkdir %s failed: %s", c.installPath, err.Error())
		return err
	}

	decompressCmd := fmt.Sprintf(
		`tar zxf %s -C %s`,
		c.Params.Medium.GetAbsolutePath(), cst.MYSQL_TOOL_INSTALL_PATH,
	)
	_, err = osutil.ExecShellCommand(false, decompressCmd)
	if err != nil {
		logger.Error("decompress rotatebinlog pkg failed: %s", err.Error())
		return err
	}

	chownCmd := fmt.Sprintf(`chown -R mysql %s && chmod +x %s`, c.installPath, c.binPath)
	_, err = osutil.ExecShellCommand(false, chownCmd)
	if err != nil {
		logger.Error("chown %s to mysql failed: %s", c.installPath, err.Error())
		return err
	}

	return nil
}

// GenerateBinaryConfig 生成 mysql-rotatebinlog 配置文件
func (c *InstallRotateBinlogComp) GenerateBinaryConfig() (err error) {
	for k, val := range c.Params.Configs.BackupClient {
		if k == "ibs" {
			ibsClient := backup.IBSBackupClient{}
			if reflect.TypeOf(val).Kind() == reflect.Map {
				// backup_client.ibs 返回的是 json map,比如 {"enable": true,"ibs_mode": "hdfs","with_md5": true,"file_tag": "INCREMENT_BACKUP","tool_path": "backup_client"}
				if err := mapstructure.Decode(val, &ibsClient); err != nil {
					return errors.Wrapf(err, "fail to decode backup_client.ibs value:%v", val)
				} else {
					c.Params.Configs.BackupClient[k] = ibsClient
				}
			} else {
				// backup_client.ibs 返回的是 string, 比如：{\"enable\": true,\"ibs_mode\": \"hdfs\",\"with_md5\": true,\"file_tag\": \"INCREMENT_BACKUP\",\"tool_path\": \"backup_client\"}
				if err := json.Unmarshal([]byte(cast.ToString(val)), &ibsClient); err != nil {
					return errors.Wrapf(err, "fail to parse backup_client.ibs value:%v", val)
				} else {
					c.Params.Configs.BackupClient[k] = ibsClient
				}
			}
		} else {
			mapObj := make(map[string]interface{})
			if reflect.TypeOf(val).Kind() == reflect.Map {
				mapObj = val.(map[string]interface{})
			} else if err := json.Unmarshal([]byte(cast.ToString(val)), &mapObj); err != nil {
				return errors.Wrapf(err, "fail to parse backup_client value:%v", val)
			}
			c.Params.Configs.BackupClient[k] = mapObj
		}
	}
	yamlData, err := yaml.Marshal(c.Params.Configs) // use json tag
	if err != nil {
		return err
	}
	c.configFile = filepath.Join(c.installPath, "config.yaml")
	if err := ioutil.WriteFile(c.configFile, yamlData, 0644); err != nil {
		return err
	}
	return nil
}

// InstallCrontab 注册crontab
func (c *InstallRotateBinlogComp) InstallCrontab() (err error) {
	err = osutil.RemoveSystemCrontab("mysql-rotatebinlog")
	if err != nil {
		logger.Error("remove old mysql-rotatebinlog crontab failed: %s", err.Error())
		return err
	}
	registerCmd := fmt.Sprintf("%s -c %s --addSchedule", c.binPath, c.configFile)
	str, err := osutil.ExecShellCommand(false, registerCmd)
	if err != nil {
		logger.Error(
			"failed to register mysql-rotatebinlog to crond: %s(%s)", str, err.Error(),
		)
	}
	return err
}

// Example 样例
func (c *InstallRotateBinlogComp) Example() interface{} {
	ibsExample := `{
  "enable": true,
  "ibs_mode": "hdfs",
  "with_md5": true,
  "file_tag": "INCREMENT_BACKUP",
  "tool_path": "backup_client"
}`
	return InstallRotateBinlogComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Params: InstallRotateBinlogParam{
			Medium: components.Medium{
				Pkg:    "mysql-rotatebinlog.tar.gz",
				PkgMd5: "12345",
			},
			Configs: rotate.Config{
				Public: rotate.PublicCfg{
					KeepPolicy:         "most",
					MaxBinlogTotalSize: "200g",
					MaxDiskUsedPct:     80,
					MaxKeepDuration:    "61d",
					PurgeInterval:      "4h",
					RotateInterval:     "10m",
				},
				Crond: rotate.ScheduleCfg{
					Schedule: "*/10 * * * *",
					ApiUrl:   "http://127.0.0.1:9999",
					ItemName: "mysql-rotatebinlog",
				},
				Servers: nil,
				Report: rotate.ReportCfg{
					Enable:     true,
					Filepath:   path.Join(cst.DBAReportBase, "mysql/binlog"),
					LogMaxsize: 5, LogMaxbackups: 10, LogMaxage: 30,
				},
				Encrypt: rotate.EncryptCfg{Enable: false},
				BackupClient: map[string]interface{}{
					"ibs": json.RawMessage([]byte(ibsExample)),
				},
			},
			Instances: []*rotate.ServerObj{
				{
					Host: "1.1.1.1", Port: 3306,
					Tags: rotate.InstanceMeta{
						BkBizId: 100, ClusterId: 10, ClusterDomain: "a.b.c", DBRole: "master",
					},
				},
			},
			ExecUser: "sys",
		},
	}
}
