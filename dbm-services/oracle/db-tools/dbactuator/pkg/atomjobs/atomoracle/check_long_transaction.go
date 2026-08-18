package atomoracle

import (
	"database/sql"
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"
)

// kill 长事务后等待 PMON 清理会话的相关常量
const (
	// killWaitTimeout kill 后等待会话被 PMON 清理完的最大时长
	killWaitTimeout = 60 * time.Second
	// killCheckInterval 轮询检查会话是否已清理的间隔
	killCheckInterval = 10 * time.Second
)

// CheckLongTransactionParams 检查长事务初始化参数
type CheckLongTransactionParams struct {
}

// CheckLongTransaction 检查长事务原子任务   oracle用户执行
type CheckLongTransaction struct {
	BaseJob
	Params *CheckLongTransactionParams `json:"extend"`
	CheckLongTransactionRunTimeCtx
}

// CheckLongTransactionRunTimeCtx 运行时上下文
type CheckLongTransactionRunTimeCtx struct {
	Sessions []Session `json:"sessions"`
}

type Session struct {
	Sid        string `json:"sid"`
	Serial     string `json:"serial"`
	Username   string `json:"username"`
	Machine    string `json:"machine"`
	LastCallEt int    `json:"last_call_et"`
	SqlId      string `json:"sql_id"`
}

// NewCheckLongTransaction new
func NewCheckLongTransaction() jobruntime.JobRunner {
	return &CheckLongTransaction{}
}

// Init 初始化
func (e *CheckLongTransaction) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of InstallOracle fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of InstallOracle fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *CheckLongTransaction) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of CheckLongTransaction")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of CheckLongTransaction fail, error:%s", err)
		return fmt.Errorf("validate parameters of CheckLongTransaction fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *CheckLongTransaction) Name() string {
	return "check_long_transaction"
}

// Run 执行函数
func (e *CheckLongTransaction) Run() error {
	// 检查长事务
	if err := e.CheckLongTransaction(); err != nil {
		return err
	}
	if len(e.Sessions) == 0 {
		e.Runtime.Logger.Info("no long transaction found, skip kill")
		return nil
	}
	// kill指定来源并且执行时长超过阈值的长事务
	if err := e.KillLongTransaction(); err != nil {
		return err
	}
	// KILL SESSION IMMEDIATE 只是触发回滚，PMON 需要时间清理会话
	// 轮询等待会话被真正清理，最长等待 killWaitTimeout
	deadline := time.Now().Add(killWaitTimeout)
	for {
		if err := e.CheckLongTransaction(); err != nil {
			return err
		}
		if len(e.Sessions) == 0 {
			e.Runtime.Logger.Info("all long transactions have been cleaned up")
			return nil
		}
		if time.Now().After(deadline) {
			e.Runtime.Logger.Error("long transaction still exists after kill, count: %d, wait timeout: %s",
				len(e.Sessions), killWaitTimeout)
			return fmt.Errorf("long transaction still exists after kill, count: %d", len(e.Sessions))
		}
		e.Runtime.Logger.Info("still %d session(s) remaining, wait %s and retry...",
			len(e.Sessions), killCheckInterval)
		time.Sleep(killCheckInterval)
	}
}

// CheckLongTransaction 获取长事务、未提交事务
func (e *CheckLongTransaction) CheckLongTransaction() error {
	e.Runtime.Logger.Info("start to check long transaction")
	// 每次调用先清空上一次的结果，避免残留
	e.Sessions = e.Sessions[:0]
	sql := []string{common.GetLongTransactionSql, common.GetUncommittedTransactionSql}
	// 获取长事务、未提交事务
	for _, s := range sql {
		if err := e.querySessions(s); err != nil {
			return err
		}
	}
	return nil
}

// querySessions 执行单条查询 SQL，将结果 append 到 e.Sessions
func (e *CheckLongTransaction) querySessions(query string) error {
	db, err := common.OpenOracleAsSysdba()
	if err != nil {
		e.Runtime.Logger.Error("open oracle as sysdba fail, error:%s", err)
		return fmt.Errorf("open oracle as sysdba fail, error:%s", err)
	}
	defer db.Close()

	if err = common.QueryOracle(db, query, func(rows *sql.Rows) error {
		var session Session
		if err := rows.Scan(&session.Sid, &session.Serial, &session.Username, &session.Machine,
			&session.LastCallEt, &session.SqlId); err != nil {
			return err
		}
		e.Sessions = append(e.Sessions, session)
		e.Runtime.Logger.Info("sid: %s, serial: %s, username: %s, machine: %s, last_call_et: %d, sql_id: %s",
			session.Sid, session.Serial, session.Username, session.Machine, session.LastCallEt, session.SqlId)
		return nil
	}); err != nil {
		e.Runtime.Logger.Error("check long transaction fail, error:%s", err)
		return fmt.Errorf("check long transaction fail, error:%s", err)
	}
	e.Runtime.Logger.Info("check long transaction successfully")
	return nil
}

// KillLongTransaction kill 上一次 CheckLongTransaction 查出的所有会话
func (e *CheckLongTransaction) KillLongTransaction() error {
	seen := make(map[string]struct{}, len(e.Sessions))
	for _, session := range e.Sessions {
		key := session.Sid + "," + session.Serial
		if _, ok := seen[key]; ok {
			e.Runtime.Logger.Info("skip duplicated session '%s'", key)
			continue
		}
		seen[key] = struct{}{}
		if err := e.killOneSession(session); err != nil {
			return err
		}
	}
	return nil
}

// killOneSession 对单个会话执行 ALTER SYSTEM KILL SESSION IMMEDIATE
func (e *CheckLongTransaction) killOneSession(session Session) error {
	stmt := fmt.Sprintf("ALTER SYSTEM KILL SESSION '%s,%s' IMMEDIATE", session.Sid, session.Serial)
	e.Runtime.Logger.Info("sql: %s", stmt)
	db, err := common.OpenOracleAsSysdba()
	if err != nil {
		e.Runtime.Logger.Error("open oracle as sysdba fail, error:%s", err)
		return fmt.Errorf("open oracle as sysdba fail, error:%s", err)
	}
	defer db.Close()

	if _, err = db.Exec(stmt); err != nil {
		// 以下错误码对于"确保长事务被清理"的目标来说等价于成功，忽略即可：
		//   ORA-00030: User session ID does not exist. 会话已不存在
		//     （可能被前一次 KILL 清掉、或事务自行 commit/rollback 后会话已断开）
		//   ORA-00031: session marked for kill. 会话已被标记为待 kill，PMON 会异步清理
		ignorableErrs := []string{"ORA-00030", "ORA-00031"}
		for _, code := range ignorableErrs {
			if strings.Contains(err.Error(), code) {
				e.Runtime.Logger.Warn("skip session '%s,%s', error: %s",
					session.Sid, session.Serial, err)
				return nil
			}
		}
		e.Runtime.Logger.Error("kill long transaction fail, error:%s", err)
		return fmt.Errorf("kill long transaction fail, error:%s", err)
	}
	e.Runtime.Logger.Info("kill session '%s,%s' successfully", session.Sid, session.Serial)
	return nil
}

// Retry times
func (e *CheckLongTransaction) Retry() uint {
	return 2
}

// Rollback rollback
func (e *CheckLongTransaction) Rollback() error {
	return nil
}
