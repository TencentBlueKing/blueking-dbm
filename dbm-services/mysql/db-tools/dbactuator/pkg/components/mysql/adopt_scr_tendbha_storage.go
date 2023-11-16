package mysql

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/rollback"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

type AdoptScrTenDBHAStorageComp struct {
	GeneralParam *components.GeneralParam      `json:"general"`
	Params       *AdoptScrTenDBHAStorageParams `json:"extend"`
	inner        *InstallMySQLComp             `json:"-"`
	workers      map[int]*native.DbWorker      `json:"-"`
}

type AdoptScrTenDBHAStorageParams struct {
	components.Medium
	IP           string            `json:"ip" validate:"required"`
	Ports        []int             `json:"ports" validate:"required"`
	SuperAccount AdditionalAccount `json:"super_account"`
	DBHAAccount  AdditionalAccount `json:"dbha_account"`
}

func (c *AdoptScrTenDBHAStorageComp) Init() error {
	c.inner = &InstallMySQLComp{
		GeneralParam: c.GeneralParam,
		Params: &InstallMySQLParams{
			MyCnfConfigs:             nil,
			MysqlVersion:             "",
			CharSet:                  "",
			Ports:                    c.Params.Ports,
			InstMem:                  0,
			Host:                     "",
			SuperAccount:             c.Params.SuperAccount,
			DBHAAccount:              c.Params.DBHAAccount,
			SpiderAutoIncrModeMap:    nil,
			AllowDiskFileSystemTypes: nil,
		},
		RollBackContext: rollback.RollBackObjects{},
		TimeZone:        "",
	}
	c.inner.Params.Medium = c.Params.Medium
	c.inner.Params.Host = c.Params.IP
	c.inner.InsPorts = c.Params.Ports
	c.inner.WorkUser = c.GeneralParam.RuntimeAccountParam.AdminUser
	c.inner.WorkPassword = c.GeneralParam.RuntimeAccountParam.AdminPwd
	c.inner.AvoidReset = true
	c.inner.InsSockets = make(map[Port]string)
	c.workers = make(map[int]*native.DbWorker)

	for _, port := range c.inner.InsPorts {
		dbWork, err := native.NewDbWorker(
			native.DsnByTcp(
				fmt.Sprintf("%s:%d", c.Params.IP, port),
				c.inner.WorkUser,
				c.inner.WorkPassword,
			),
		)
		if err != nil {
			logger.Error("connect %d failed: %s", port, err.Error())
			return err
		}

		c.workers[port] = dbWork

		var socketPath string
		err = dbWork.Queryxs(&socketPath, `select @@socket`)
		if err != nil {
			logger.Error("execute select @@socket on %d failed: %s", port, err.Error())
			return err
		}
		c.inner.InsSockets[port] = socketPath

		// 这里取重复了, 不过问题不大
		var dbVersion string
		err = dbWork.Queryxs(&dbVersion, `select @@version`)
		if err != nil {
			logger.Error("execute select @@version on %d failed: %s", port, err.Error())
			return err
		}
		c.inner.Params.MysqlVersion = dbVersion
	}

	return nil
}

func (c *AdoptScrTenDBHAStorageComp) ClearOldCrontab() error {
	err := osutil.RemoveUserCrontab("mysql")
	if err != nil {
		logger.Error("clear mysql crontab failed: %s", err.Error())
	} else {
		logger.Info("clear mysql crontab success")
	}
	return nil
}

func (c *AdoptScrTenDBHAStorageComp) DropOldAccounts() error {
	accountsToDrop := []string{
		c.GeneralParam.RuntimeAccountParam.MonitorUser,
		c.GeneralParam.RuntimeAccountParam.MonitorAccessAllUser,
		c.GeneralParam.RuntimeAccountParam.YwUser,
		c.GeneralParam.RuntimeAccountParam.DbBackupUser,
		c.Params.SuperAccount.User,
		c.Params.DBHAAccount.User,
	}
	logger.Info("accounts: %s will be drop", accountsToDrop)

	for _, port := range c.inner.InsPorts {
		dbWork := c.workers[port]
		for _, account := range accountsToDrop {
			var hosts []string
			err := dbWork.Queryx(&hosts, `select host from mysql.user where user = ?`, account)
			if err != nil {
				logger.Error("query %s hosts on %d failed: %s", account, port, err.Error())
				return err
			}
			logger.Info("%s have hosts %s on %d", account, hosts, port)

			for _, host := range hosts {
				user := fmt.Sprintf("'%s'@'%s'", account, host)
				_, err := dbWork.Exec(fmt.Sprintf("drop user %s", user))
				if err != nil {
					logger.Error("drop user %s on %d failed: %s", user, port, err.Error())
					return err
				}
				logger.Info("drop %s on %d success", user, port)
			}
		}
		logger.Info("old account cleared on %d", port)
	}

	logger.Info("all old account cleared")
	return nil
}

func (c *AdoptScrTenDBHAStorageComp) InitDefaultPrivAndSchema() error {
	err := c.inner.InitDefaultPrivAndSchemaWithResetMaster()
	if err != nil {
		logger.Error("init default priv and schema failed: %s", err.Error())
		return err
	}
	logger.Info("init default priv and schema success")
	return nil
}

func (c *AdoptScrTenDBHAStorageComp) Example() interface{} {
	return AdoptScrTenDBHAStorageComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Params: &AdoptScrTenDBHAStorageParams{
			Medium: components.Medium{
				Pkg:    "mysql-5.7.20-linux-x86_64-tmysql-3.3-gcs.tar.gz",
				PkgMd5: "12345",
			},
			IP:    "x.x.x.x",
			Ports: []int{6666, 7777},
			SuperAccount: AdditionalAccount{
				User:        "fake_super_user",
				Pwd:         "fake_super_pwd",
				AccessHosts: []string{"x.x.x.x", "y.y.y.y"},
			},
			DBHAAccount: AdditionalAccount{
				User:        "fake_dbha_user",
				Pwd:         "fake_dbha_pwd",
				AccessHosts: []string{"x.x.x.x", "y.y.y.y"},
			},
		},
	}
}
