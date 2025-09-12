package upgrade

import (
	"errors"
	"fmt"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

type MysqlUpgradeCheckComp struct {
	GeneralParam    *components.GeneralParam `json:"general"`
	Params          MysqlUpgradeCheckParam   `json:"extend"`
	upgradeCheckRtx `json:"-"`
}

type MysqlUpgradeCheckParam struct {
	Host  string `json:"host"  validate:"required,ip"`
	Ports []int  `json:"ports"`
	components.Medium
}

type Port = int

type upgradeCheckRtx struct {
	dbConns                  map[Port]*native.DbWorker
	verMap                   map[Port]VersionInfo
	sysUsers                 []string
	newVersion               VersionInfo
	socketMaps               map[Port]string
	adminUser                string
	adminPwd                 string
	isSameMajorTmysqlVersion bool
}

func (m *MysqlUpgradeCheckComp) Init() (err error) {
	m.dbConns = make(map[Port]*native.DbWorker)
	m.verMap = make(map[Port]VersionInfo)
	m.socketMaps = make(map[Port]string)
	m.sysUsers = m.GeneralParam.GetAllSysAccount()
	m.adminUser = m.GeneralParam.RuntimeAccountParam.AdminUser
	m.adminPwd = m.GeneralParam.RuntimeAccountParam.AdminPwd
	m.newVersion = VersionInfo{
		Version:       m.Params.Pkg,
		MysqlVersion:  cmutil.MySQLVersionParse(m.Params.Pkg),
		TmysqlVersion: cmutil.TmysqlVersionParse(m.Params.Pkg),
	}
	if m.newVersion.MysqlVersion <= 0 {
		return fmt.Errorf("mysql version %s is invalid", m.Params.Pkg)
	}
	for _, port := range m.Params.Ports {
		dbConn, err := native.InsObject{
			Host: m.Params.Host,
			Port: port,
			User: m.adminUser,
			Pwd:  m.adminPwd,
		}.Conn()
		if err != nil {
			logger.Error("Connect %d failed:%s", port, err.Error())
			return err
		}
		m.dbConns[port] = dbConn
		ver, err := dbConn.SelectVersion()
		if err != nil {
			logger.Error("Get version failed:%s", err.Error())
			return err
		}
		isTokudb := false
		isTokudb, err = dbConn.HasTokudb()
		if err != nil {
			logger.Error("query %d engine  failed:%s", port, err.Error())
			return err
		}
		currentVer := VersionInfo{
			Version:       ver,
			MysqlVersion:  cmutil.MySQLVersionParse(ver),
			TmysqlVersion: cmutil.TmysqlVersionParse(ver),
			IsToku:        isTokudb,
		}
		m.verMap[port] = currentVer
		if err = currentVer.canUpgrade(m.newVersion); err != nil {
			logger.Error("upgrade version check failed %s", err.Error())
			return err
		}
	}

	logger.Info("mysql upgrade init ok,new version:%d", m.newVersion.MysqlVersion)
	return nil
}

// MysqlUpgradeCheck start upgrade check
func (m *MysqlUpgradeCheckComp) MysqlUpgradeCheck() (err error) {
	for port, conn := range m.dbConns {
		currentVer := m.verMap[port]
		if currentVer.TmysqlVersion > native.TMYSQL_3 && currentVer.TmysqlVersion < native.TMySQL_3P15 {
			if err = conn.CheckInstantAddColumn(); err != nil {
				// 当前版本是tmysql 3, 且低于3.1.15。检查是否有非法在线加字段
				if !errors.Is(err, native.ErrorUsedInstantAddColumnButValid) {
					return err
				}
			}
		}
		if m.newVersion.MysqlVersion >= native.MYSQL_8P0 {
			if err = conn.CheckInstantAddColumn(); err != nil {
				return fmt.Errorf(
					"CheckInstantAddColumn failed, upgrade to %s cannot go on due to incompatibility of data dictionary: %s",
					m.newVersion.Version, err.Error())
			}
		}
		// table check
		if currentVer.TmysqlVersion/cmutil.Billion == m.newVersion.TmysqlVersion/cmutil.Billion {
			logger.Info("same big tmysql version, skip check table upgrade")
			continue
		}
		errs := conn.CheckTableUpgrade(currentVer.MysqlVersion, m.newVersion.MysqlVersion)
		if len(errs) > 0 {
			for _, err := range errs {
				logger.Error("port:[%d]: check table upgrade error: %s", port, err.Error())
			}
			return fmt.Errorf("check table upgrade failed, port: %d, errors: %v", port, errs)
		}
	}
	return nil
}
