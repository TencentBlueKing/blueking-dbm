package dbareport

import (
	"encoding/json"
	"time"

	//recore "dbm-services/common/reverseapi/internal/core"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
)

type MysqlBackupResultEvent IndexContent

func (e *MysqlBackupResultEvent) ClusterType() string {
	return "tendbha"
}

func (e *MysqlBackupResultEvent) EventType() string {
	return "mysql_dbbackup_result"
}

func (e *MysqlBackupResultEvent) EventCreateTimeStamp() int64 {
	return e.BackupBeginTime.UnixMilli()
}

func (e *MysqlBackupResultEvent) EventBkBizId() int64 {
	return int64(e.BkBizId)
}

// 不强求实现 String, 这里是给下面的错误处理写例子用的
func (e *MysqlBackupResultEvent) String() string {
	b, _ := json.Marshal(e)
	return string(b)
}

type MysqlBackupStatusEvent struct {
	config *config.BackupConfig
	report BackupStatus
	ts     time.Time
	//core   *recore.Core
}

func NewMysqlBackupStatusEvent(config *config.BackupConfig, report BackupStatus) (*MysqlBackupStatusEvent, error) {
	/*reportCore, err := reverseapi.NewCore(0)
	if err != nil {
		return nil, err
	}
	*/
	return &MysqlBackupStatusEvent{
		config: config,
		report: report,
		//core:   reportCore,
	}, nil
}

func (e *MysqlBackupStatusEvent) ClusterType() string {
	return "tendbha"
}

func (e *MysqlBackupStatusEvent) EventType() string {
	return "mysql_dbbackup_progress"
}

func (e *MysqlBackupStatusEvent) EventCreateTimeStamp() int64 {
	if e.ts.IsZero() {
		e.ts = time.Now()
	}
	return e.ts.UnixMilli()
}

func (e *MysqlBackupStatusEvent) EventBkBizId() int64 {
	return int64(e.config.Public.BkBizId)
}

func (e *MysqlBackupStatusEvent) MarshalJSON() ([]byte, error) {
	return json.Marshal(e.report)
}

// 不强求实现 String, 这里是给下面的错误处理写例子用的
func (e *MysqlBackupStatusEvent) String() string {
	b, _ := json.Marshal(e)
	return string(b)
}

// SetStatus 设置备份进度
// 每次修改 status都当做一个新的 event上报，这里要修改 ts
func (e *MysqlBackupStatusEvent) SetStatus(progress string, detail string) *MysqlBackupStatusEvent {
	e.ts = time.Now()
	e.report.Status = progress
	e.report.StatusDetail = detail
	return e
}
