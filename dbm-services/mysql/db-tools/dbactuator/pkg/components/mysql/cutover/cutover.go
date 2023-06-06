// Package cutover 主故障切换
// 下发到Slave节点的机器 执行
package cutover

import (
	"fmt"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

// CutOverParam TODO
type CutOverParam struct {
	Host    string              `json:"host"  validate:"required,ip"`
	Cluster *MySQLClusterDetail `json:"cluster"`
	IsSafe  bool                `json:"is_safe"`
	// Master 是否已经dead
	IsDeadMaster bool `json:"is_dead_master"`
	// 切换完成，是都需要为源Master,获取其他Slave增加复制账户
	GrantRepl bool `json:"grant_repl"`
	// 是否需要锁表切换
	LockedSwitch bool `json:"locked_switch"`
}

// CutOverToSlaveComp TODO
type CutOverToSlaveComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *CutOverParam            `json:"extend"`
	runCtx       `json:"-"`
}
type runCtx struct {
	checkVars      []string
	proxyAdminUser string
	proxyAdminPwd  string
	adminUser      string
	adminPwd       string
	replUser       string
	replPwd        string
	backupUser     string
	cluster        *MySQLClusterDetail
	// 是否是成对切换
	isCutOverPair bool
}

// Init 初始化
func (m *CutOverToSlaveComp) Init() (err error) {
	m.cluster = m.Params.Cluster
	m.proxyAdminUser = m.GeneralParam.RuntimeAccountParam.ProxyAdminUser
	m.proxyAdminPwd = m.GeneralParam.RuntimeAccountParam.ProxyAdminPwd
	m.adminUser = m.GeneralParam.RuntimeAccountParam.AdminUser
	m.adminPwd = m.GeneralParam.RuntimeAccountParam.AdminPwd
	m.replUser = m.GeneralParam.RuntimeAccountParam.ReplUser
	m.replPwd = m.GeneralParam.RuntimeAccountParam.ReplPwd
	m.backupUser = m.GeneralParam.RuntimeAccountParam.DbBackupUser
	m.checkVars = []string{"character_set_server", "lower_case_table_names"}

	if err = m.cluster.InitProxyConn(m.proxyAdminUser, m.proxyAdminPwd); err != nil {
		logger.Error("connect alt proxies failed,err:%s ", err.Error())
		return err
	}

	if err = m.cluster.InitAltSlaveConn(m.adminUser, m.adminPwd); err != nil {
		logger.Error("connect alt slave  %s failed,err:%s ", m.cluster.AltSlaveIns.Addr(), err.Error())
		return err
	}
	// 如果需要锁表切换的情况下，需要通switch tmp account 去初始化源Master
	// 连接，账户需要有锁表的权限
	if m.Params.LockedSwitch {
		switch_user := m.cluster.MasterIns.SwitchTmpAccount.User
		switch_pwd := m.cluster.MasterIns.SwitchTmpAccount.Pwd
		if err = m.cluster.InitMasterConn(switch_user, switch_pwd); err != nil {
			logger.Error(
				"connect %s from %s use %s account failed %s",
				m.cluster.MasterIns.Addr(), m.Params.Host, switch_user, err.Error(),
			)
			return err
		}
	}
	// 成对迁移的情况下，初始化NewSlave的连接
	if m.cluster.AltSlaveIns.Slave != nil {
		if err = m.cluster.AltSlaveIns.Slave.InitConn(); err != nil {
			logger.Error(
				"connect %s from %s use %s account failed %s",
				m.cluster.AltSlaveIns.Slave.Addr(), m.Params.Host, m.cluster.AltSlaveIns.Slave.User,
			)
			return err
		}
		m.isCutOverPair = true
	}
	return err
}

// Example TODO
func (m *CutOverToSlaveComp) Example() interface{} {
	comp := CutOverToSlaveComp{
		Params: &CutOverParam{
			Host: "1.1.1.2",
			Cluster: &MySQLClusterDetail{
				ProxyInstances: []Proxies{
					{
						Instance: native.Instance{
							Host: "1.1.0.1",
							Port: 10000,
						},
					},
					{
						Instance: native.Instance{
							Host: "1.1.0.2",
							Port: 10000,
						},
					},
				},
				MasterIns: MasterInfo{
					Instance: native.Instance{
						Host: "1.1.1.1",
						Port: 3306,
					},
					SwitchTmpAccount: SwitchTmpAccount{
						User: "",
						Pwd:  "",
					},
				},
				AltSlaveIns: AltSlaveInfo{
					Instance: native.Instance{
						Host: "1.1.1.2",
						Port: 3306,
					},
					Slave: &NewSlaveInfo{
						Instance: native.Instance{
							Host: "1.1.1.5",
							Port: 3306,
						},
						SwitchTmpAccount: SwitchTmpAccount{
							User: "",
							Pwd:  "",
						},
					},
				},
				SlaveInstances: []native.Instance{
					{
						Host: "1.1.1.3",
						Port: 3306,
					},
					{
						Host: "1.1.1.4",
						Port: 3306,
					},
				},
			},
			IsSafe:       true,
			IsDeadMaster: false,
			LockedSwitch: true,
		},
	}
	return comp
}

// PreCheck  预备检查
func (m *CutOverToSlaveComp) PreCheck() (err error) {
	// 以下是强制检查的内容
	// 检查下proxy backend 是不是 源Master
	if err := m.cluster.CheckBackends(m.cluster.MasterIns.Host, m.cluster.MasterIns.Port); err != nil {
		return err
	}
	// 检查alt Slave repl 的地址不是 cluster.MasterIns
	if err := m.cluster.CheckAltSlaveMasterAddr(); err != nil {
		return err
	}

	// 安全模式下，检查下CheckSum,检查业务连接
	if m.Params.IsSafe {
		if err = m.cluster.AltSlaveIns.CheckCheckSum(); err != nil {
			return err
		}
		prcsls, err := m.cluster.AltSlaveIns.dbConn.ShowApplicationProcesslist(
			m.GeneralParam.RuntimeExtend.MySQLSysUsers)
		if err != nil {
			logger.Error("show processlist failed %s", err.Error())
			return err
		}
		if len(prcsls) > 0 {
			return fmt.Errorf("there is a connection for non system users %v", prcsls)
		}
		if m.isCutOverPair {
			if err = m.cluster.AltSlaveIns.Slave.CheckCheckSum(); err != nil {
				return err
			}
		}
	}

	// 如果源Master已经故障，以下检查跳过
	// 如果源主库是故障的，则待切换的从库的复制状态也是一定是异常的
	if m.Params.IsDeadMaster {
		// 如果主库是故障的，一定进行不了锁表切换
		m.Params.LockedSwitch = false
		return nil
	}

	if err = m.cluster.AltSlaveIns.dbConn.CheckSlaveReplStatus(func() (resp native.ShowSlaveStatusResp, err error) {
		return m.cluster.AltSlaveIns.dbConn.ShowSlaveStatus()
	}); err != nil {
		logger.Error("检查主从同步状态出错: %s", err.Error())
		return err
	}

	if m.isCutOverPair {
		if err = m.cluster.AltSlaveIns.Slave.dbConn.CheckSlaveReplStatus(func() (resp native.ShowSlaveStatusResp, err error) {
			return m.cluster.AltSlaveIns.Slave.dbConn.ShowSlaveStatus()
		}); err != nil {
			return err
		}
	}
	// 初始化只读连接,在Slave从Repl 账户去获取Master实例的变量
	if err = m.cluster.InitMasterOnlyReadConn(m.replUser, m.replPwd); err != nil {
		logger.Error("connect alt slave  %s failed,err:%s ", m.cluster.MasterIns.Addr(), err.Error())
		return err
	}
	// 主从参数配置对比
	if err = m.cluster.MSVarsCheck(m.checkVars); err != nil {
		return err
	}
	// 主从版本对比
	if err = m.cluster.MSVersionCheck(); err != nil {
		return err
	}
	// 如果需要锁表切换，则进行锁表切换前置检查
	if m.Params.LockedSwitch {
		return m.cluster.MasterIns.LockTablesPreCheck(m.backupUser)
	}
	return err
}

// CutOver 切换
func (m *CutOverToSlaveComp) CutOver() (binPos string, err error) {
	defer func() {
		if m.Params.LockedSwitch {
			m.cluster.MasterIns.UnlockTables()
		}
		if err != nil {
			e := m.cluster.UpdateProxiesBackend(m.cluster.MasterIns.Host, m.cluster.MasterIns.Port)
			if e != nil {
				logger.Warn("rollback proxy backends failed  %s", err.Error())
				return
			}
			logger.Info("rollback proxy backend to %ssuccessfully", m.cluster.MasterIns.Addr())
		}
	}()
	// proxy switch 1.1.1.1:3306
	logger.Info("proxy backend switch to 1.1.1.1:3306")
	if err = m.cluster.SetProxiesDefaultBackend(); err != nil {
		logger.Error(
			"update proxies[%#v] backend to %s failed:%s",
			m.cluster.ProxyInstances,
			"1.1.1.1:3306",
			err.Error(),
		)
		return "{}", err
	}
	//  尝试在源主库加锁
	if m.Params.LockedSwitch {
		if err = m.cluster.MasterIns.FlushTablesWithReadLock(); err != nil {
			logger.Error("locked %s tables failed:%s", m.cluster.MasterIns.Addr(), err.Error())
			return "", err
		}
	}

	if !m.Params.IsDeadMaster {
		if err = m.cluster.AltSlaveIns.dbConn.CheckSlaveReplStatus(func() (resp native.ShowSlaveStatusResp, err error) {
			return m.cluster.AltSlaveIns.dbConn.ShowSlaveStatus()
		}); err != nil {
			logger.Error("再次检查下主从状态 %s", err.Error())
			return "", err
		}
		fn := func() error {
			return CompareMSBinPos(m.cluster.MasterIns, m.cluster.AltSlaveIns)
		}
		err = util.Retry(util.RetryConfig{Times: 10, DelayTime: 100 * time.Millisecond}, fn)
		if err != nil {
			logger.Error("主从binlog位点有差异 %s", err.Error())
			return "", err
		}
	}

	// record cutover bin pos
	if binPos, err = m.cluster.AltSlaveIns.RecordBinPos(); err != nil {
		logger.Error("获取切换时候的位点信息失败: %s", err.Error())
		return
	}
	// proxy switch 待切换slave
	logger.Info("proxy backend switch to %s", m.cluster.AltSlaveIns.Addr())
	err = util.Retry(
		util.RetryConfig{Times: 20, DelayTime: 500 * time.Millisecond},
		func() error {
			return m.cluster.UpdateProxiesBackend(m.cluster.AltSlaveIns.Host, m.cluster.AltSlaveIns.Port)
		},
	)
	if err != nil {
		logger.Error(
			"update proxies[%#v] backend to %s get an error:%s",
			m.cluster.ProxyInstances, m.cluster.AltSlaveIns.Addr(), err.Error(),
		)
		return "{}", err
	}
	return binPos, err
}

// StopAndResetSlave TODO
// 切换成功之后
// Stop Slave && Reset Slave
func (m *CutOverToSlaveComp) StopAndResetSlave() (err error) {
	// stop slave
	if err = m.cluster.AltSlaveIns.dbConn.StopSlave(); err != nil {
		logger.Error("stop slave failed %s", err.Error())
		return err
	}
	// reset slave
	if err = m.cluster.AltSlaveIns.dbConn.ResetSlave(); err != nil {
		logger.Error("stop slave failed %s", err.Error())
		return err
	}
	return
}

// GrantRepl 切换后对其他实例授权，便于后面change 到新的master
func (m *CutOverToSlaveComp) GrantRepl() (err error) {
	var hosts []string
	if !m.Params.IsDeadMaster {
		hosts = []string{m.cluster.MasterIns.Host}
	}
	for _, ins := range m.cluster.SlaveInstances {
		hosts = append(hosts, ins.Host)
	}
	for _, host := range hosts {
		g := grant.GrantReplComp{
			GeneralParam: m.GeneralParam,
			Params: &grant.GrantReplParam{
				Host:      m.cluster.AltSlaveIns.Host,
				Port:      m.cluster.AltSlaveIns.Port,
				ReplHosts: []string{host},
			},
		}
		if err = g.Init(); err != nil {
			logger.Error("%s:grant repl,init db conn failed:%s", host, err.Error())
			return
		}
		defer g.Db.Db.Close()
		if err = g.GrantRepl(); err != nil {
			logger.Error("%s:grant repl failed:%s", host, err.Error())
			return err
		}
	}
	return err
}
