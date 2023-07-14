package mysql

import (
	"bytes"
	"fmt"
	"os"
	"os/user"
	"path/filepath"

	"github.com/pkg/errors"

	"github.com/BurntSushi/toml"

	"dbm-services/common/go-pubpkg/backupclient"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/netutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// InstallBackupClientComp 基本结构
type InstallBackupClientComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       InstallBackupClientParam `json:"extend"`
	configFile   string
	binPath      string
	installPath  string
}

// InstallBackupClientParam 输入参数
type InstallBackupClientParam struct {
	components.Medium
	Config  backupclient.CosClientConfig `json:"config" validate:"required"` // 模板配置
	CosInfo backupclient.CosInfo         `json:"cosinfo" validate:"required"`
	// 发起执行actor的用户，仅用于审计
	ExecUser string `json:"exec_user"`
}

// Init 初始化
func (c *InstallBackupClientComp) Init() (err error) {
	c.installPath = cst.BackupClientInstallPath
	c.binPath = filepath.Join(c.installPath, "bin/backup_client")
	return nil
}

// PreCheck 预检查
func (c *InstallBackupClientComp) PreCheck() (err error) {
	ipList := netutil.GetAllIpAddr()
	if !cmutil.StringsHas(ipList, c.Params.Config.Cfg.NetAddr) {
		return errors.Errorf("ipaddr %s is not in host net address list", c.Params.Config.Cfg.NetAddr)
	}
	if err = c.Params.Medium.Check(); err != nil {
		logger.Error("check backup_client pkg failed: %s", err.Error())
		return err
	}
	return nil
}

// DeployBinary 部署 backup_client 二进制
func (c *InstallBackupClientComp) DeployBinary() (err error) {
	decompressCmd := fmt.Sprintf(
		`tar zxf %s -C %s`,
		c.Params.Medium.GetAbsolutePath(), "/usr/local",
	)
	_, err = osutil.ExecShellCommand(false, decompressCmd)
	if err != nil {
		logger.Error("decompress backup_client pkg failed: %s", err.Error())
		return err
	}
	chownCmd := fmt.Sprintf(`chown -R root.root %s && chmod +x %s`, c.installPath, c.binPath)
	_, err = osutil.ExecShellCommand(false, chownCmd)
	if err != nil {
		logger.Error("chown %s to root failed: %s", c.installPath, err.Error())
		return err
	}
	return nil
}

// GenerateBinaryConfig 生成 mysql-rotatebinlog 配置文件
func (c *InstallBackupClientComp) GenerateBinaryConfig() (err error) {
	c.configFile = filepath.Join(c.installPath, "conf/config.toml")
	buf := bytes.NewBuffer([]byte{})
	if err = toml.NewEncoder(buf).Encode(&c.Params.Config); err != nil {
		return errors.Wrapf(err, "write config file")
	}

	if err := os.WriteFile(c.configFile, buf.Bytes(), 0644); err != nil {
		return err
	}
	return nil
}

func (c *InstallBackupClientComp) GenerateBucketConfig() (err error) {
	mysqlUser, err := user.Lookup("mysql")
	if err != nil {
		return err
	}
	userHome := mysqlUser.HomeDir
	if userHome != "" && cmutil.IsDirectory(userHome) {

	}
	configFile := filepath.Join(userHome, ".cosinfo.toml")
	buf := bytes.NewBuffer([]byte{})
	if err := toml.NewEncoder(buf).Encode(&c.Params.CosInfo); err != nil {
		return err
	}
	if err := os.WriteFile(configFile, buf.Bytes(), 0644); err != nil {
		return err
	}
	return nil
}

// InstallCrontab 注册crontab
func (c *InstallBackupClientComp) InstallCrontab() (err error) {
	err = osutil.RemoveSystemCrontab("backup_client upload")
	if err != nil {
		logger.Error("remove old 'backup_client upload' crontab failed: %s", err.Error())
		return err
	}
	uploadCrontabCmd := fmt.Sprintf("%s addcrontab -u root >/dev/null", c.binPath)
	str, err := osutil.ExecShellCommand(false, uploadCrontabCmd)
	if err != nil {
		logger.Error(
			"failed add '%s' to crond: %s(%s)", uploadCrontabCmd, str, err.Error(),
		)
	}
	return err
}

// Example 样例
func (c *InstallBackupClientComp) Example() interface{} {
	return InstallBackupClientComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Params: InstallBackupClientParam{
			Medium: components.Medium{
				Pkg:    "backup_client.tar.gz",
				PkgMd5: "12345",
			},
			Config: backupclient.CosClientConfig{
				Base: backupclient.BaseLimit{
					BlockSize:       100,
					LocalFileLimit:  100,
					LocalTotalLimit: 100,
				},
				Cfg: backupclient.UploadConfig{
					FileTagAllowed: "MYSQL_FULL_BACKUP,REDIS_FULL....",
					NetAddr:        "x.x.x.x",
				},
			},
			CosInfo: backupclient.CosInfo{
				Cos: &backupclient.CosAuth{
					Region:     "xxx",
					BucketName: "yyy",
					SecretId:   "sid encrypted",
					SecretKey:  "skey encrypted",
					CosServer:  "urlxxx",
				},
				AppAttr: &backupclient.AppAttr{
					BkBizId:   3,
					BkCloudId: 0,
				},
			},
			ExecUser: "sys",
		},
	}
}
