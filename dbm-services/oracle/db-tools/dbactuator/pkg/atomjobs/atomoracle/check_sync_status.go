package atomoracle

import (
	"database/sql"
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"
)

// CheckSyncStatusParams 执行脚本初始化参数
type CheckSyncStatusParams struct {
}

// CheckSyncStatus 执行脚本原子任务   oracle用户执行
type CheckSyncStatus struct {
	BaseJob
	Params                    *CheckSyncStatusParams
	CheckSyncStatusRunTimeCtx `json:"-"`
}

// CheckSyncStatusRunTimeCtx 运行时上下文
type CheckSyncStatusRunTimeCtx struct {
}

// NewCheckSyncStatus new
func NewCheckSyncStatus() jobruntime.JobRunner {
	return &CheckSyncStatus{}
}

// Init 初始化
func (e *CheckSyncStatus) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of CheckSyncStatus fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of CheckSyncStatus fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *CheckSyncStatus) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of CheckSyncStatus")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of CheckSyncStatus fail, error:%s", err)
		return fmt.Errorf("validate parameters of CheckSyncStatus fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *CheckSyncStatus) Name() string {
	return "check-sync-status"
}

// Run 执行函数
func (e *CheckSyncStatus) Run() error {
	db, err := common.OpenOracleAsSysdba()
	if err != nil {
		return fmt.Errorf("open oracle as sysdba failed: %v", err)
	}
	defer db.Close()
	if err = CheckSync(db); err != nil {
		return err
	}
	return nil
}

func CheckSync(db *sql.DB) error {
	// 1) 检查 MRP 进程：必须存在且状态是 APPLYING_LOG 或 WAIT_FOR_LOG
	if err := CheckMRPProcess(db); err != nil {
		return err
	}

	// 2) 检查 transport lag / apply lag 是否在阈值内
	if err := CheckDataguardLag(db); err != nil {
		return fmt.Errorf("check dataguard lag failed: %v", err)
	}
	return nil
}

// CheckMRPProcess 校验 MRP0 进程存在且状态健康。
// 在 1 分钟窗口内每 10 秒探测一次
// 只要任一次命中 APPLYING_LOG / WAIT_FOR_LOG 即视为正常，
// 其他任何状态（含 WAIT_FOR_GAP、进程缺失等）都持续重试直到窗口耗尽。
func CheckMRPProcess(db *sql.DB) error {
	const (
		maxRetry      = 6
		retryInterval = 10 * time.Second
	)
	var lastErr error
	for attempt := 0; attempt <= maxRetry; attempt++ {
		if err := probeMRPProcess(db); err == nil {
			return nil
		} else {
			lastErr = err
		}
		if attempt == maxRetry {
			break
		}
		time.Sleep(retryInterval)
	}
	return fmt.Errorf("MRP process still unhealthy after %d retries: %v", maxRetry, lastErr)
}

// probeMRPProcess 单次探测 MRP 进程状态。
// 返回值：err=nil 表示所有 MRP 进程都健康（APPLYING_LOG / WAIT_FOR_LOG），
// 否则返回具体的非健康原因，交由上层决定是否重试。
func probeMRPProcess(db *sql.DB) error {
	query := `SELECT PROCESS, STATUS, SEQUENCE#, THREAD#, BLOCK#, DELAY_MINS
		FROM V$MANAGED_STANDBY
		WHERE PROCESS LIKE 'MRP%'`

	type mrpRow struct {
		Process   string
		Status    string
		Sequence  int64
		Thread    int64
		Block     int64
		DelayMins int64
	}
	var rows []mrpRow
	if err := common.QueryOracle(db, query, func(r *sql.Rows) error {
		var m mrpRow
		if err := r.Scan(&m.Process, &m.Status, &m.Sequence, &m.Thread, &m.Block, &m.DelayMins); err != nil {
			return err
		}
		rows = append(rows, m)
		return nil
	}); err != nil {
		return fmt.Errorf("query v$managed_standby failed: %v", err)
	}
	if len(rows) == 0 {
		return fmt.Errorf("no MRP process found in v$managed_standby, apply not started")
	}
	for _, m := range rows {
		status := strings.ToUpper(strings.TrimSpace(m.Status))
		if status != "APPLYING_LOG" && status != "WAIT_FOR_LOG" {
			return fmt.Errorf(
				"MRP process %s in unhealthy status: %s (thread=%d, sequence=%d)",
				m.Process, m.Status, m.Thread, m.Sequence,
			)
		}
	}
	return nil
}

// CheckDataguardLag 校验 transport lag / apply lag 在阈值内
func CheckDataguardLag(db *sql.DB) error {
	query := `SELECT NAME,
		NVL(VALUE, '') AS VALUE,
		CASE
		  WHEN VALUE IS NULL OR TRIM(VALUE) IS NULL THEN -1
		  ELSE EXTRACT(DAY    FROM TO_DSINTERVAL(VALUE)) * 86400
		     + EXTRACT(HOUR   FROM TO_DSINTERVAL(VALUE)) * 3600
		     + EXTRACT(MINUTE FROM TO_DSINTERVAL(VALUE)) * 60
		     + EXTRACT(SECOND FROM TO_DSINTERVAL(VALUE))
		END AS LAG_SECONDS
		FROM V$DATAGUARD_STATS
		WHERE NAME IN ('transport lag','apply lag')`

	type lagRow struct {
		Name   string
		Value  string
		Second float64
	}
	var got []lagRow
	err := common.QueryOracle(db, query, func(r *sql.Rows) error {
		var l lagRow
		if err := r.Scan(&l.Name, &l.Value, &l.Second); err != nil {
			return err
		}
		got = append(got, l)
		return nil
	})
	if err != nil {
		return fmt.Errorf("query v$dataguard_stats failed: %v", err)
	}
	if len(got) < 2 {
		return fmt.Errorf("v$dataguard_stats returned %d rows, expect 2 (transport lag & apply lag)", len(got))
	}
	for _, l := range got {
		if strings.TrimSpace(l.Value) == "" {
			return fmt.Errorf("%s is empty, apply may not be running", l.Name)
		}
		if l.Second < 0 {
			return fmt.Errorf("%s parse failed, value=%q", l.Name, l.Value)
		}
		if l.Second > consts.LagThresholdSec {
			return fmt.Errorf("%s = %s exceeds threshold %ds, current value: %.0f seconds", l.Name, l.Value,
				consts.LagThresholdSec, l.Second)
		}
	}
	return nil
}
