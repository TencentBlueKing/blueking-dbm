package upgrade

import (
	"fmt"
	"os"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

// MysqlUpgradeComp TODO
type MysqlUpgradeComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       MysqlUpgradeParam        `json:"extend"`
	runtimeCtx   `json:"-"`
}

// MysqlUpgradeParam TODO
type MysqlUpgradeParam struct {
	Host string `json:"host"  validate:"required,ip"`
	Port int    `json:"port"`
	components.Medium
	// 只做升级检查
	Run bool `json:"run"`
}

// VersionInfo TODO
type VersionInfo struct {
	Version       string
	MysqlVersion  uint64
	TmysqlVersion uint64
	IsToku        bool
}

// 运行时上下文
type runtimeCtx struct {
	dbConn                   *native.DbWorker
	versionInfo              VersionInfo
	sysUsers                 []string
	newVersion               VersionInfo
	socket                   string
	adminUser                string
	adminPwd                 string
	port                     int
	myCnf                    *util.CnfFile
	isSameMajorTmysqlVersion bool
}

// Init prepare run env
func (m *MysqlUpgradeComp) Init() (err error) {
	m.sysUsers = m.GeneralParam.GetAllSysAccount()
	m.adminUser = m.GeneralParam.RuntimeAccountParam.AdminUser
	m.adminPwd = m.GeneralParam.RuntimeAccountParam.AdminPwd
	m.port = m.Params.Port
	m.newVersion = VersionInfo{
		Version:       m.Params.Pkg,
		MysqlVersion:  cmutil.MySQLVersionParse(m.Params.Pkg),
		TmysqlVersion: cmutil.TmysqlVersionParse(m.Params.Pkg),
	}
	if m.newVersion.MysqlVersion <= 0 {
		return fmt.Errorf("mysql version %s is invalid", m.Params.Pkg)
	}
	dbConn, err := native.InsObject{
		Host: m.Params.Host,
		Port: m.Params.Port,
		User: m.adminUser,
		Pwd:  m.adminPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect %d failed:%s", m.Params.Port, err.Error())
		return err
	}
	m.dbConn = dbConn
	ver, err := dbConn.SelectVersion()
	if err != nil {
		logger.Error("Get version failed:%s", err.Error())
		return err
	}
	isTokudb := false
	isTokudb, err = dbConn.HasTokudb()
	if err != nil {
		logger.Error("query %d engine  failed:%s", m.port, err.Error())
		return err
	}
	currentVer := VersionInfo{
		Version:       ver,
		MysqlVersion:  cmutil.MySQLVersionParse(ver),
		TmysqlVersion: cmutil.TmysqlVersionParse(ver),
		IsToku:        isTokudb,
	}
	m.versionInfo = currentVer
	if err = currentVer.canUpgrade(m.newVersion); err != nil {
		logger.Error("upgrade version check failed %s", err.Error())
		return err
	}
	m.isSameMajorTmysqlVersion = (m.newVersion.TmysqlVersion / cmutil.Billion) ==
		(m.versionInfo.TmysqlVersion / cmutil.Billion)
	logger.Info("mysql upgrade init ok,new version:%d", m.newVersion.MysqlVersion)
	// 获取配置文件路径
	cf := util.GetMyCnfFileName(m.Params.Port)
	cff, err := util.LoadMyCnfForFile(cf)
	if err != nil {
		logger.Error("load %s file failed: %s", cf, err.Error())
		return err
	}
	m.myCnf = cff
	sck, err := cff.GetMySQLSocket()
	if err != nil {
		logger.Error("get mysql socket failed: %s", err.Error())
		return err
	}
	m.socket = sck
	return nil
}

// StartInit just for  start init
func (m *MysqlUpgradeComp) StartInit() (err error) {
	m.sysUsers = m.GeneralParam.GetAllSysAccount()
	m.adminUser = m.GeneralParam.RuntimeAccountParam.AdminUser
	m.adminPwd = m.GeneralParam.RuntimeAccountParam.AdminPwd
	m.port = m.Params.Port
	cf := util.GetMyCnfFileName(m.Params.Port)
	cff, err := util.LoadMyCnfForFile(cf)
	if err != nil {
		logger.Error("load %s file failed: %s", cf, err.Error())
		return err
	}
	m.myCnf = cff
	sck, err := cff.GetMySQLSocket()
	if err != nil {
		logger.Error("get mysql socket failed: %s", err.Error())
		return err
	}
	m.socket = sck
	return nil
}

func prepareNewConfigFile(newfile string) error {
	if cmutil.FileExists(newfile) {
		if err := os.Remove(newfile); err != nil {
			logger.Error("remove exist tmp my.cnf failed: %s", err.Error())
			return err
		}
	}
	return nil
}

func (current *VersionInfo) canUpgrade(newVersion VersionInfo) (err error) {
	logger.Info("newvesion is %v", newVersion)
	logger.Info("currentvesion MysqlVersion  is %v", current.MysqlVersion)
	logger.Info("currentvesion TmysqlVersion is %v", current.TmysqlVersion)
	logger.Info("currentvesion IsToku is %v", current.IsToku)
	switch {
	case current.MysqlVersion < native.MYSQL_5P5P24:
		return fmt.Errorf("don't support current version: %d lower than mysql-5.5.24 to upgrade", current.MysqlVersion)
	case current.MysqlVersion > newVersion.MysqlVersion:
		return fmt.Errorf("don't allow to decrease mysql version: current version: %s,  new version: %s", current.Version,
			newVersion.Version)
	case (newVersion.MysqlVersion == current.MysqlVersion && newVersion.TmysqlVersion < current.TmysqlVersion):
		return fmt.Errorf("don't allow to decrease tmysql version: current version: %s,  new version: %s", current.Version,
			newVersion.Version)
	case newVersion.TmysqlVersion < native.TMYSQL_1P1:
		return fmt.Errorf("don't allow to upgrade to NON-TMYSQL: current version: %s, new version: %s", current.Version,
			newVersion.Version)
	case (newVersion.TmysqlVersion/1000000)-(current.TmysqlVersion/1000000) > 1:
		return fmt.Errorf("don't allow to upgrade across big version: current version: %s, new version: %s",
			current.Version, newVersion.Version)
	case newVersion.TmysqlVersion >= native.TMYSQL_1 && current.MysqlVersion < native.MYSQL_5P1P24:
		return fmt.Errorf("don't allow to upgrade, current version: %s, new version: %s", current.Version,
			newVersion.Version)
	case newVersion.TmysqlVersion >= native.TMYSQL_2 && current.TmysqlVersion < native.TMYSQL_1:
		return fmt.Errorf("don't allow to upgrade tmysql 2.x: current version: %s, new version: %s", current.Version,
			newVersion.Version)
	case newVersion.MysqlVersion >= native.MYSQL_8P0 && current.MysqlVersion < native.MYSQL_5P70:
		return fmt.Errorf("upgrading to MySQL 8 from MySQL version <5.7 is not allowed: current version: %d, new version: %d",
			current.MysqlVersion, newVersion.MysqlVersion)
	}
	if current.IsToku && (newVersion.TmysqlVersion >= native.TMYSQL_3 || newVersion.TmysqlVersion <= native.TMYSQL_2P1P1) {
		return fmt.Errorf("current version: %s have enable tokudb, but newversion: %s don't support", current.Version,
			newVersion.Version)
	}
	if newVersion.MysqlVersion > native.MYSQL_5P5P1 && current.MysqlVersion > native.MYSQL_5P0P48 {
		return nil
	}
	return fmt.Errorf("don't allow to upgrade, current version: %s, new version: %s", current.Version,
		newVersion.Version)
}
