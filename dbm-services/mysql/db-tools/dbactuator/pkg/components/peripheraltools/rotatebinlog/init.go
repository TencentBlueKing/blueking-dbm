package rotatebinlog

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	rcst "dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/rotate"
	"path/filepath"

	"github.com/pkg/errors"
	"github.com/samber/lo"
)

type MySQLRotateBinlogComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       MySQLRotateBinlogParam   `json:"extend"`
	configFile   string
	binPath      string
	installPath  string
}

type MySQLRotateBinlogParam struct {
	components.Medium
	Configs   rotate.Config       `json:"configs" validate:"required"`
	Instances []*rotate.ServerObj `json:"instances"`
	ExecUser  string              `json:"exec_user"`
}

func (c *MySQLRotateBinlogComp) Init() (err error) {
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

		if !lo.Contains(rcst.BackupEnableAllowed, c.Params.Configs.Public.BackupEnable) {
			return errors.Errorf("public.backup_enable value only true/false/auto")
		}
	}

	c.installPath = cst.MysqlRotateBinlogInstallPath
	c.binPath = filepath.Join(c.installPath, string(tools.ToolMysqlRotatebinlog))
	return nil
}

func (c *MySQLRotateBinlogComp) PreCheck() (err error) {
	if err = c.Params.Medium.Check(); err != nil {
		logger.Error("check mysql-rotatebinlog pkg failed: %s", err.Error())
		return err
	}
	return nil
}
