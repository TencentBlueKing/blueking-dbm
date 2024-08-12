package backup_client

import (
	"dbm-services/common/go-pubpkg/backupclient"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/netutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"path/filepath"

	"github.com/pkg/errors"
)

type BackupClientComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       BackupClientParam        `json:"extend"`
	configFile   string
	binPath      string
	installPath  string
}

type BackupClientParam struct {
	components.Medium
	Config  backupclient.CosClientConfig `json:"config" validate:"required"` // 模板配置
	CosInfo backupclient.CosInfo         `json:"cosinfo" validate:"required"`
	// 发起执行actor的用户，仅用于审计
	ExecUser string `json:"exec_user"`
}

func (c *BackupClientComp) Init() (err error) {
	c.installPath = cst.BackupClientInstallPath
	c.binPath = filepath.Join(c.installPath, "bin/backup_client")
	return nil
}

func (c *BackupClientComp) PreCheck() (err error) {
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
