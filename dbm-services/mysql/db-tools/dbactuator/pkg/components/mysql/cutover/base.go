package cutover

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
)

const (
	// SwitchRelayCheckMaxSec TODO
	SwitchRelayCheckMaxSec = 10
	// AllowedChecksumMaxOffset TODO
	AllowedChecksumMaxOffset = 2
	// AllowedTimestampMaxOffset TODO
	AllowedTimestampMaxOffset = 5
	// AllowedSlaveDelayMax TODO
	AllowedSlaveDelayMax = 10
	// AllowedTimeDelayMax TODO
	AllowedTimeDelayMax = 3600
	// ExecSlowKbytes TODO
	ExecSlowKbytes = 0
)

// Ins tance  TODO
type Ins struct {
	native.Instance
	dbConn *native.DbWorker `json:"-"`
}

// Proxies TODO
type Proxies struct {
	native.Instance
	proxyConn *native.ProxyAdminDbWork
}

// SwitchTmpAccount 切换时，用于远程操作的临时超级账户
// 只允许 Slave Host 连接
type SwitchTmpAccount struct {
	User string `json:"user"`
	Pwd  string `json:"pwd"`
}

// MasterInfo TODO
type MasterInfo struct {
	native.Instance
	SwitchTmpAccount `json:"switch_account"`
	dbConn           *native.DbWorker `json:"-"`
	// 只读连接
	readOnlyConn *native.DbWorker `json:"-"`
}

// AltSlaveInfo 备选待切换
// Alt  = AlterNative:备选
type AltSlaveInfo struct {
	native.Instance
	dbConn *native.DbWorker `json:"-"`
	Slave  *NewSlaveInfo    `json:"slave"`
}

// NewSlaveInfo TODO
type NewSlaveInfo struct {
	native.Instance
	dbConn           *native.DbWorker `json:"-"`
	SwitchTmpAccount `json:"switch_account"`
}

// InitConn TODO
func (s *NewSlaveInfo) InitConn() (err error) {
	s.dbConn, err = native.InsObject{
		Host: s.Host,
		Port: s.Port,
		User: s.User,
		Pwd:  s.Pwd,
	}.Conn()
	if err != nil {
		return err
	}
	return nil
}

// MySQLClusterDetail 群基本信息
type MySQLClusterDetail struct {
	// Proxy Instances
	ProxyInstances []Proxies `json:"proxy_instances"  validate:"required,gt=0,dive"`
	// 主实例
	MasterIns MasterInfo `json:"master_instance"  validate:"required"`
	// 待切换的从实例
	AltSlaveIns AltSlaveInfo `json:"alt_slave_instance"  validate:"required"`
	// 除待切换其他从实例
	SlaveInstances []native.Instance `json:"slave_instance"`
}

// InitProxyConn 初始化Proxy连接
func (m *MySQLClusterDetail) InitProxyConn(user, pwd string) (err error) {
	for i := 0; i < len(m.ProxyInstances); i++ {
		p := m.ProxyInstances[i]
		m.ProxyInstances[i].proxyConn, err = native.InsObject{
			Host: p.Host,
			Port: p.Port,
			User: user,
			Pwd:  pwd,
		}.ConnProxyAdmin()
		if err != nil {
			logger.Error("connect proxy %s admin port %d failed: %s", p.Host, p.Port, err.Error())
			return err
		}
	}
	return err
}

// InitMasterConn 初始化 Master Ins 连接
func (m *MySQLClusterDetail) InitMasterConn(user, pwd string) (err error) {
	m.MasterIns.dbConn, err = native.InsObject{
		Host: m.MasterIns.Host,
		Port: m.MasterIns.Port,
		User: user,
		Pwd:  pwd,
	}.Conn()
	return err
}

// InitMasterOnlyReadConn 初始化 Master Ins ReadOnly 连接
func (m *MySQLClusterDetail) InitMasterOnlyReadConn(user, pwd string) (err error) {
	m.MasterIns.readOnlyConn, err = native.InsObject{
		Host: m.MasterIns.Host,
		Port: m.MasterIns.Port,
		User: user,
		Pwd:  pwd,
	}.Conn()
	return err
}

// InitAltSlaveConn 初始化Alt Slave 连接
func (m *MySQLClusterDetail) InitAltSlaveConn(user, pwd string) (err error) {
	m.AltSlaveIns.dbConn, err = native.InsObject{
		Host: m.AltSlaveIns.Host,
		Port: m.AltSlaveIns.Port,
		User: user,
		Pwd:  pwd,
	}.Conn()
	return err
}

// InitAltSlaveSlaveConn 初始化Alt Slave 的 Slave 连接
func (m *MySQLClusterDetail) InitAltSlaveSlaveConn(user, pwd string) (err error) {
	m.AltSlaveIns.Slave.dbConn, err = native.InsObject{
		Host: m.AltSlaveIns.Slave.Host,
		Port: m.AltSlaveIns.Slave.Port,
		User: user,
		Pwd:  pwd,
	}.Conn()
	return err
}

// CheckBackends TODO
func (m *MySQLClusterDetail) CheckBackends(host string, port int) (err error) {
	for _, p := range m.ProxyInstances {
		if err = p.proxyConn.CheckBackend(host, port); err != nil {
			return err
		}
	}
	return
}

// CheckAltSlaveMasterAddr TODO
// CheckAlterMasterOk
// 检查待切换的从实例，复制的源是否等于Master
func (m *MySQLClusterDetail) CheckAltSlaveMasterAddr() (err error) {
	ss, err := m.AltSlaveIns.dbConn.ShowSlaveStatus()
	if err != nil {
		return err
	}
	if strings.Compare(fmt.Sprintf("%s:%d", ss.MasterHost, ss.MasterPort), m.MasterIns.Addr()) != 0 {
		msg := fmt.Sprintf(
			"主从复制关系不正确,%s repl from %s,而不是%s",
			m.AltSlaveIns.Addr(),
			ss.MasterHost,
			m.MasterIns.Addr(),
		)
		logger.Error(msg)
		return fmt.Errorf(msg)
	}
	return err
}

// UpdateProxiesBackend Set Backend
func (m *MySQLClusterDetail) UpdateProxiesBackend(host string, port int) (err error) {
	for _, p := range m.ProxyInstances {
		if err = p.proxyConn.RefreshBackends(host, port); err != nil {
			logger.Error("refreshBackend failed %s", err.Error())
			return err
		}
		if err = p.proxyConn.CheckBackend(host, port); err != nil {
			return err
		}
	}
	return
}

// SetProxiesDefaultBackend TODO
// set proxy backend to 1.1.1.1:3306
func (m *MySQLClusterDetail) SetProxiesDefaultBackend() (err error) {
	// proxy switch 1.1.1.1:3306
	logger.Info("proxy backend switch to 1.1.1.1:3306")
	err = util.Retry(
		util.RetryConfig{Times: 5, DelayTime: 3 * time.Second},
		func() error { return m.UpdateProxiesBackend("1.1.1.1", 3306) },
	)
	if err != nil {
		logger.Error(
			"update proxies[%#v] backend to %s get an error:%s",
			m.ProxyInstances, "1.1.1.1:3306", err.Error(),
		)
		return err
	}
	return
}

// LockTablesPreCheck TODO
// TryLockTables
func (c *MasterInfo) LockTablesPreCheck(backupUser string) (err error) {
	// 尝试去kill backup processlist
	// backup processlist 占用的时间比较长会影响lock table
	if err = c.KillBackupUserProcesslist(backupUser); err != nil {
		return err
	}
	// 查看是否有长的非活跃连接
	if err = c.FindLongQuery(); err != nil {
		return err
	}
	return
}

// FlushTablesWithReadLock 执行flush table with read  lock
func (c *MasterInfo) FlushTablesWithReadLock() (err error) {
	if _, err := c.dbConn.Exec("set lock_wait_timeout = 10;"); err != nil {
		return err
	}
	err = util.Retry(
		util.RetryConfig{Times: 10, DelayTime: 200 * time.Millisecond}, func() error {
			_, err = c.dbConn.Exec("FLUSH TABLES;")
			return err
		},
	)
	if err != nil {
		logger.Error("重试3次,每次间隔5秒，依然失败：%s", err.Error())
		return err
	}
	if _, err := c.dbConn.Exec("FLUSH TABLES WITH READ LOCK;"); err != nil {
		return err
	}
	return
}

// UnlockTables TODO
// FlushTablesWithReadLock 执行flush table with read  lock
func (c *MasterInfo) UnlockTables() (err error) {
	if _, err := c.dbConn.Exec("UNLOCK TABLES"); err != nil {
		logger.Error("unlock table failed:%s", err.Error())
		return err
	}
	return
}

// DropSwitchUser TODO
// FlushTablesWithReadLock 执行flush table with read  lock
func (c *MasterInfo) DropSwitchUser(userHost string) (err error) {
	if _, err := c.dbConn.Exec(fmt.Sprintf("drop user %s;", userHost)); err != nil {
		logger.Error("drop %s failed:%s", userHost, err.Error())
		return err
	}
	return
}

// KillBackupUserProcesslist kill 备份processlist
func (c *MasterInfo) KillBackupUserProcesslist(backupUser string) (err error) {
	processLists, err := c.dbConn.SelectProcesslist([]string{backupUser})
	if err != nil {
		return err
	}
	if len(processLists) <= 0 {
		logger.Info("没有发现关于备份用户[%s]相关的processlist~", backupUser)
		return nil
	}
	var killSQLs []string
	for _, processlist := range processLists {
		killSQLs = append(killSQLs, fmt.Sprintf("Kill %d;", processlist.ID))
	}
	logger.Info("will kill processlist %v", killSQLs)
	_, err = c.dbConn.ExecMore(killSQLs)
	return
}

// FindLongQuery 查询是否存在长的查询、processlist
func (c *MasterInfo) FindLongQuery() (err error) {
	activeProcessLists, err := c.dbConn.SelectLongRunningProcesslist(10)
	if err != nil {
		return err
	}
	if len(activeProcessLists) <= 0 {
		return nil
	}
	errMsg := []string{"active processlist exist:\n"}
	for _, p := range activeProcessLists {
		errMsg = append(
			errMsg, fmt.Sprintf(
				"[user:%s,time:%s,host:%s,db:%s,info:%s]",
				p.User, p.Time, p.Host, realVal(p.DB), realVal(p.Info),
			),
		)
	}
	return
}

// realVal TODO
func realVal(v sql.NullString) string {
	if !v.Valid {
		return ""
	}
	return v.String
}

// GetChangeMasterSQL 获取change master SQL
// proxy 切掉流量后，在备选从库上获取位点信息，供Old Master Change 使用
// func (s *AltSlaveInfo) GetChangeMasterSQL(repluser, replpwd string) (changeSQL string, err error) {
// 	pos, err := s.dbConn.ShowMasterStatus()
// 	if err != nil {
// 		logger.Error("执行show master status 失败！%s", err.Error())
// 		return "", err
// 	}
// 	logger.Info("current pos is binlog_file:%s,binlog_pos:%d", pos.File, pos.Position)
// 	changeSQL = fmt.Sprintf(`CHANGE MASTER TO
// 						MASTER_HOST='%s',
// 						MASTER_USER='%s',
// 						MASTER_PASSWORD='%s',
// 						MASTER_PORT=%d,
// 						MASTER_LOG_FILE='%s',
// 						MASTER_LOG_POS=%d;`, s.Host, repluser, replpwd, s.Port, pos.File, pos.Position)
// 	return
// }

// RecordBinPos 记录切换时候的bin postion
func (s *AltSlaveInfo) RecordBinPos() (binPosJsonStr string, err error) {
	pos, _ := s.dbConn.ShowMasterStatus()
	logger.Info("show master status on %s,detail: File:%s,Pos:%s", s.Addr(), pos.File, pos.Position)
	b, err := json.Marshal(pos)
	if err != nil {
		return "", err
	}
	changeSQL := fmt.Sprintf(
		`CHANGE MASTER TO
						MASTER_HOST='%s',
						MASTER_USER='%s',
						MASTER_PASSWORD='%s',
						MASTER_PORT=%d,
						MASTER_LOG_FILE='%s',
						MASTER_LOG_POS=%d;`, s.Host, "{user}", "{pwd}", s.Port, pos.File, pos.Position,
	)
	logger.Info("change master sql: %s", changeSQL)
	return string(b), nil
}

// MSVersionCheck 主从版本对比
func (m *MySQLClusterDetail) MSVersionCheck() (err error) {
	masterVer, err := m.MasterIns.readOnlyConn.SelectVersion()
	if err != nil {
		return err
	}
	slaveVer, err := m.AltSlaveIns.dbConn.SelectVersion()
	if err != nil {
		return err
	}
	return mysqlutil.VersionCompare(masterVer, slaveVer)
}

// MSVarsCheck 主从配置对比
func (m *MySQLClusterDetail) MSVarsCheck(checkVars []string) (err error) {
	return m.AltSlaveIns.dbConn.MySQLVarsCompare(m.MasterIns.readOnlyConn, checkVars)
}

// MSCheck 切换前同步检查
type MSCheck struct {
	SlavedbConn          *native.DbWorker
	NeedCheckSumRd       bool // 需要存在校验记录
	NotVerifyChecksum    bool // 是否检查checksum
	AllowDiffCount       int  // 允许存在差异的校验记录的行数
	AllowDelaySec        int  // 允许存在的延迟差异
	AllowDelayBinlogByte int  // 允许binlog的最大延迟
}

// NewMsCheck TODO
func NewMsCheck(dbConn *native.DbWorker) *MSCheck {
	return &MSCheck{
		SlavedbConn:          dbConn,
		NeedCheckSumRd:       true,
		AllowDiffCount:       AllowedChecksumMaxOffset,
		AllowDelaySec:        AllowedSlaveDelayMax,
		AllowDelayBinlogByte: ExecSlowKbytes,
	}
}

// Check TODO
func (s *MSCheck) Check() (err error) {
	slaveStatus, err := s.SlavedbConn.ShowSlaveStatus()
	if err != nil {
		return err
	}
	if !slaveStatus.ReplSyncIsOk() {
		return fmt.Errorf(
			"IOThread:%s,SQLThread:%s",
			slaveStatus.SlaveIORunning, slaveStatus.SlaveSQLRunning,
		)
	}
	// 检查主从同步delay binlog size
	total, err := s.SlavedbConn.TotalDelayBinlogSize()
	if err != nil {
		logger.Error("get total delay binlog size failed %s", err.Error())
		return err
	}
	if total > s.AllowDelayBinlogByte {
		return fmt.Errorf("the total delay binlog size %d 超过了最大允许值 %d", total, s.AllowDelayBinlogByte)
	}
	var delaysec int
	c := fmt.Sprintf(
		`select check_result as slave_delay from %s.master_slave_check 
			WHERE check_item='slave_delay_sec';`, native.INFODBA_SCHEMA,
	)
	if err = s.SlavedbConn.Queryxs(&delaysec, c); err != nil {
		logger.Error("查询slave delay sec: %s", err.Error())
		return err
	}
	if delaysec > s.AllowDelaySec {
		return fmt.Errorf("slave 延迟时间 %d， 超过了上限 %d", delaysec, s.AllowDelaySec)
	}

	// 以为内部版本需要校验的参数
	if s.SlavedbConn.IsEmptyInstance() {
		logger.Info("主从关系正常，从库是空实例，跳过检查checksum表")
		return nil
	}
	// 如果不需要检查checksum table 则直接返回
	if s.NotVerifyChecksum {
		return
	}
	var cnt int
	c = fmt.Sprintf(
		"select count(distinct db, tbl) as cnt from %s.checksum where ts > date_sub(now(), interval 14 day)",
		native.INFODBA_SCHEMA,
	)
	if err = s.SlavedbConn.Queryxs(&cnt, c); err != nil {
		logger.Error("查询最近14天checkTable总数失败%s", err.Error())
		return err
	}

	if !s.NeedCheckSumRd {
		logger.Info("不需要检查校验记录. 获取到的CheckSum Record 总数为%d", cnt)
	}

	// 如果查询不到 校验记录需要 return error
	if cnt == 0 && s.NeedCheckSumRd {
		logger.Warn("没有查询到最近14天的校验记录")
		return fmt.Errorf("主从校验记录为空")
	}

	c = fmt.Sprintf(
		`select count(distinct db, tbl,chunk) as cnt from %s.checksum
			where (this_crc <> master_crc or this_cnt <> master_cnt)
		  	and ts > date_sub(now(), interval 14 day);`, native.INFODBA_SCHEMA,
	)
	if err = s.SlavedbConn.Queryxs(&cnt, c); err != nil {
		logger.Error("查询数据校验差异表失败: %s", err.Error())
		return err
	}

	if cnt > s.AllowDiffCount {
		return fmt.Errorf("checksum 不同值的 chunk 个数是 %d， 超过了上限 %d", cnt, s.AllowDiffCount)
	}

	return nil
}

// CheckCheckSum TODO
// CheckMSReplStatus
// 只在待切换的从库检查CheckSum 和主从同步状态
func (s AltSlaveInfo) CheckCheckSum() (err error) {
	return NewMsCheck(s.dbConn).Check()
}

// CheckCheckSum TODO
func (s NewSlaveInfo) CheckCheckSum() (err error) {
	return NewMsCheck(s.dbConn).Check()
}

// CompareMSBinPos 比较主从的同步的位点信息对比
func CompareMSBinPos(master MasterInfo, slave AltSlaveInfo) (err error) {
	masterStatus, err := master.readOnlyConn.ShowMasterStatus()
	if err != nil {
		logger.Error("show master status on %s failed:%s", master.Addr(), err.Error())
		return err
	}

	slaveStatus, err := slave.dbConn.ShowSlaveStatus()
	if err != nil {
		logger.Error("show slave status on %s failed:%s", slave.Addr(), err.Error())
		return err
	}
	// 比较从库回放到了对应主库的哪个BinLog File
	msg := fmt.Sprintf(
		"Master Current BinlogFile:%s Slave SQL Thread Exec BinlogFile:%s",
		masterStatus.File, slaveStatus.RelayMasterLogFile,
	)
	logger.Info(msg)
	if strings.Compare(masterStatus.File, slaveStatus.RelayMasterLogFile) != 0 {
		return fmt.Errorf("主从同步可能有差异," + msg)
	}
	// 比较主库的位点和从库已经回放的位点信息
	// 比较从库回放到了对应主库的哪个BinLog File
	msg = fmt.Sprintf(
		"Master Current Pos:%d Slave SQL Thread Exec Pos:%d",
		masterStatus.Position, slaveStatus.ExecMasterLogPos,
	)
	logger.Info(msg)
	if masterStatus.Position != slaveStatus.ExecMasterLogPos {
		return fmt.Errorf("主从执行的位点信息有差异%s", msg)
	}
	return err
}
