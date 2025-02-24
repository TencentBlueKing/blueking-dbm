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
	Configs       rotate.Config `json:"configs" validate:"required"`
	IP            string        `json:"ip"`
	Ports         []int         `json:"port_list"`
	Role          string        `json:"role"`
	BkBizId       int           `json:"bk_biz_id"`
	ClusterDomain string        `json:"cluster_domain"`
	ClusterId     int           `json:"cluster_id"`
	ExecUser      string        `json:"exec_user"`
}

func (c *MySQLRotateBinlogComp) Init() (err error) {
	for _, port := range c.Params.Ports {
		c.Params.Configs.Servers = append(c.Params.Configs.Servers, &rotate.ServerObj{
			Host:     c.Params.IP,
			Port:     port,
			Username: c.GeneralParam.RuntimeAccountParam.MonitorUser,
			Password: c.GeneralParam.RuntimeAccountParam.MonitorPwd,
			Socket:   "",
			Tags: rotate.InstanceMeta{
				BkBizId:       c.Params.BkBizId,
				ClusterId:     c.Params.ClusterId,
				ClusterDomain: c.Params.ClusterDomain,
				DBRole:        c.Params.Role,
			},
		})

		var instObj = native.InsObject{
			Host: c.Params.IP, Port: port,
			User: c.GeneralParam.RuntimeAccountParam.MonitorUser, Pwd: c.GeneralParam.RuntimeAccountParam.MonitorPwd,
			Socket: "",
		}
		if dbw, err := instObj.Conn(); err != nil {
			logger.Error(
				"install mysql-rotatebinlog test connect failed: %s. instance:%s:%d",
				err.Error(), c.Params.IP, port,
			)

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
	return nil
}
