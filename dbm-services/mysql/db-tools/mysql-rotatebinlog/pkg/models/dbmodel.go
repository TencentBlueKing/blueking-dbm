package models

import (
	"database/sql"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/cst"

	sq "github.com/Masterminds/squirrel"
	"github.com/golang-migrate/migrate/v4"
	"github.com/jmoiron/sqlx"
	"github.com/mitchellh/mapstructure"
	"github.com/pkg/errors"
	_ "modernc.org/sqlite" // sqlite TODO
)

// DBO db object wrapper
type DBO struct {
	Conn *sqlx.DB
}

// DB TODO
var DB *DBO

/*
func init() {
	// //_ "github.com/glebarez/go-sqlite"
	// sql.Register("go-sqlite", &sqlite.Driver{})
}
*/

// InitDB godoc
// 因为下面的 migrate 库用的 sqlite driver 是 modernc.org/sqlite (gitlab.com/cznic/sqlite)
// 不好再用其它 sqlite 库，否则会报 panic: sql: Register called twice for driver sqlite
// 当然一种处理方法是重新注册一个 driver name，如上。但没必要了
func InitDB() error {
	homeDir, _ := os.Executable()
	if err := os.Chdir(filepath.Dir(homeDir)); err != nil {
		return err
	}
	dbFile := "binlog_rotate.db"
	dsName := fmt.Sprintf(
		`%s?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)`,
		filepath.Join(".", dbFile),
	)
	if dbConn, err := sqlx.Open("sqlite", dsName); err != nil {
		return err
	} else {
		DB = &DBO{
			Conn: dbConn,
		}
	}
	return nil
}

// SetupTable create table
func SetupTable() (err error) {
	if err := DoMigrate(DB.Conn); err != nil && err != migrate.ErrNoChange {
		log.Fatal(err)
		// logger.Error(err.Error())
		return err
	}
	return nil
}

// BinlogFileModel TODO
type BinlogFileModel struct {
	BkBizId   int `json:"bk_biz_id,omitempty" db:"bk_biz_id"`
	ClusterId int `json:"cluster_id,omitempty" db:"cluster_id"`
	// immutable domain, 如果是从库，也使用主域名。cluster_domain 至少作为备注信息，一般不作为查询条件
	ClusterDomain string `json:"cluster_domain" db:"cluster_domain"`
	DBRole        string `json:"db_role" db:"db_role"`
	Host          string `json:"host,omitempty" db:"host"`
	Port          int    `json:"port,omitempty" db:"port"`
	Filename      string `json:"filename,omitempty" db:"filename"`
	Filesize      int64  `json:"size" db:"filesize"`
	// FileMtime 文件最后修改时间，带时区
	FileMtime        string `json:"file_mtime" db:"file_mtime"`
	StartTime        string `json:"start_time" db:"start_time"`
	StopTime         string `json:"stop_time" db:"stop_time"`
	BackupStatus     int    `json:"backup_status,omitempty" db:"backup_status"`
	BackupStatusInfo string `json:"backup_status_info" db:"backup_status_info"`
	BackupTaskid     string `json:"task_id,omitempty" db:"task_id"`
	*ModelAutoDatetime
}

// String 用于打印
func (m *BinlogFileModel) String() string {
	return fmt.Sprintf(
		"{filename:%s, start_time: %s, stop_time: %s, backup_status:%d, task_id: %s}",
		m.Filename, m.StartTime, m.StopTime, m.BackupStatus, m.BackupTaskid,
	)
}

// ModelAutoDatetime TODO
type ModelAutoDatetime struct {
	CreatedAt string `json:"created_at,omitempty" db:"created_at"`
	UpdatedAt string `json:"updated_at,omitempty" db:"updated_at"`
}

func (m *BinlogFileModel) instanceWhere() map[string]interface{} {
	return map[string]interface{}{
		"bk_biz_id":  m.BkBizId,
		"cluster_id": m.ClusterId,
		"host":       m.Host,
		"port":       m.Port,
	}
}

func (m *BinlogFileModel) autoTime() {
	if m.ModelAutoDatetime == nil {
		m.ModelAutoDatetime = &ModelAutoDatetime{}
	}
	m.ModelAutoDatetime.autoTime()
}

func (d *ModelAutoDatetime) autoTime() {
	nowTime := time.Now()
	if d.CreatedAt == "" {
		d.CreatedAt = nowTime.Format(cst.DBTimeLayout)
	}
	d.UpdatedAt = nowTime.Format(cst.DBTimeLayout)
}

// TableName TODO
func (m *BinlogFileModel) TableName() string {
	return "binlog_rotate"
}

// Save TODO
func (m *BinlogFileModel) Save(db *sqlx.DB) error {
	m.autoTime()
	sqlBuilder := sq.Insert("").Into(m.TableName()).
		Columns(
			"bk_biz_id", "cluster_id", "cluster_domain", "db_role", "host", "port", "filename",
			"filesize", "start_time", "stop_time", "file_mtime", "backup_status", "task_id",
			"created_at", "updated_at",
		).
		Values(
			m.BkBizId, m.ClusterId, m.ClusterDomain, m.DBRole, m.Host, m.Port, m.Filename,
			m.Filesize, m.StartTime, m.StopTime, m.FileMtime, m.BackupStatus, m.BackupTaskid,
			m.CreatedAt, m.UpdatedAt,
		)
	sqlStr, args, err := sqlBuilder.ToSql()
	if err != nil {
		return err
	}
	if res, err := db.Exec(sqlStr, args...); err != nil {
		return err
	} else {
		if num, _ := res.RowsAffected(); num != 1 {
			return errors.Errorf("rows_affected expect 1 but got %d", num)
		}
	}
	return nil
}

// BatchSave TODO
func (m *BinlogFileModel) BatchSave(models []*BinlogFileModel, db *sqlx.DB) error {
	if len(models) == 0 {
		return nil
	}
	sqlBuilder := sq.Insert("").Into(m.TableName()).
		Columns(
			"bk_biz_id", "cluster_id", "cluster_domain", "db_role", "host", "port", "filename",
			"filesize", "start_time", "stop_time", "file_mtime", "backup_status", "task_id",
			"created_at", "updated_at",
		)
	for _, o := range models {
		o.autoTime()
		sqlBuilder = sqlBuilder.Values(
			o.BkBizId, o.ClusterId, o.ClusterDomain, o.DBRole, o.Host, o.Port, o.Filename,
			o.Filesize, o.StartTime, o.StopTime, o.FileMtime, o.BackupStatus, o.BackupTaskid,
			o.CreatedAt, o.UpdatedAt,
		)
	}
	sqlStr, args, err := sqlBuilder.ToSql()
	if err != nil {
		return err
	}
	if _, err = db.Exec(sqlStr, args...); err != nil {
		return err
	}
	return nil
}

// Update 根据 host,port,filename 来进行 update
func (m *BinlogFileModel) Update(db *sqlx.DB) error {
	m.autoTime()
	if m.BackupStatusInfo == "" {
		m.BackupStatusInfo = fmt.Sprintf(IBStatusMap[m.BackupStatus])
	}
	sqlBuilder := sq.Update("").Table(m.TableName()).
		Set("backup_status", m.BackupStatus).
		Set("backup_status_info", m.BackupStatusInfo).
		Set("updated_at", m.UpdatedAt)
	if m.BackupTaskid != "" {
		sqlBuilder = sqlBuilder.Set("task_id", m.BackupTaskid)
	}
	if m.StartTime != "" {
		sqlBuilder = sqlBuilder.Set("start_time", m.StartTime)
	}
	if m.StopTime != "" {
		sqlBuilder = sqlBuilder.Set("stop_time", m.StopTime)
	}
	sqlBuilder = sqlBuilder.Where(
		"host = ? and port = ? and filename = ? and cluster_id=?",
		m.Host, m.Port, m.Filename, m.ClusterId,
	)

	sqlStr, args, err := sqlBuilder.ToSql()
	if err != nil {
		return err
	}
	// logger.Info("update sql:%s, args:%v", sqlStr, args)
	if res, err := db.Exec(sqlStr, args...); err != nil {
		return err
	} else {
		if num, _ := res.RowsAffected(); num != 1 {
			return errors.Errorf("rows_affected expect 1 but got %d", num)
		}
	}
	return nil
}

const (
	// IBStatusNew TODO
	IBStatusNew = -2 // 文件尚未提交
	// IBStatusClientFail TODO
	IBStatusClientFail = -1 // 文件上传 提交失败
	// IBStatusClientFailRetry TODO
	IBStatusClientFailRetry = -3 // 客户端错误，需要重新提交
	// IBStatusWaiting TODO
	IBStatusWaiting = 1 // 等待调度上传
	// IBStatusUploading TODO
	IBStatusUploading = 3 // <= 3 备份上传中
	// IBStatusSuccess TODO
	IBStatusSuccess = 4
	// IBStatusFileNotFound TODO
	IBStatusFileNotFound = 5
	// IBStatusFail TODO
	IBStatusFail = 6 // >= 6 fail
	// IBStatusExpired TODO
	IBStatusExpired = 44 // 文件已过期
	// FileStatusRemoved TODO
	FileStatusRemoved = 201
	// FileStatusAbnormal TODO
	FileStatusAbnormal = 202
	// FileStatusNoNeedUpload binlog无需上传
	FileStatusNoNeedUpload = 203
)

const (
	// RoleMaster TODO
	RoleMaster = "master"
	// RoleSlave TODO
	RoleSlave = "slave"
	// RoleRepeater TODO
	RoleRepeater = "repeater"
)

// IBStatusMap TODO
var IBStatusMap = map[int]string{
	IBStatusClientFail:   "submit failed",
	0:                    "todo, submitted",       // 等待确认主机信息
	IBStatusWaiting:      "todo, waiting",         // 等待备份
	2:                    "todo, locking",         // Locking
	IBStatusUploading:    "doing",                 // 正在备份中
	IBStatusSuccess:      "done, success",         // 备份完成
	IBStatusFileNotFound: "Fail:  file not found", // 源上找不到文件
	IBStatusFail:         "Fail: unknown",         // 其它错误
	IBStatusExpired:      "done, expired",         // 备份系统文件已过期

	FileStatusRemoved:      "local removed",
	FileStatusAbnormal:     "file abnormal",
	FileStatusNoNeedUpload: "no need to backup",
}

// IBStatusUnfinish TODO
var IBStatusUnfinish = []int{IBStatusNew, IBStatusClientFail, 0, IBStatusWaiting, 2, IBStatusUploading}

// DeleteExpired godoc
// 删除过期记录
func (m *BinlogFileModel) DeleteExpired(db *sqlx.DB, mTime string) (int64, error) {
	sqlBuilder := sq.Delete("").From(m.TableName()).
		Where(m.instanceWhere()).Where("file_mtime < ?", mTime)
	sqlStr, args, err := sqlBuilder.ToSql()
	if err != nil {
		return 0, err
	}
	if res, err := db.Exec(sqlStr, args...); err != nil {
		return 0, err
	} else {
		num, _ := res.RowsAffected()
		return num, nil
	}
}

func mapStructureDecodeJson(input interface{}, output interface{}) error {
	msCfg := &mapstructure.DecoderConfig{TagName: "json", Result: output}
	mapStruct, _ := mapstructure.NewDecoder(msCfg)
	return mapStruct.Decode(input)
}

// QueryUnfinished 查询待上传、上传未完成的列表
func (m *BinlogFileModel) QueryUnfinished(db *sqlx.DB) ([]*BinlogFileModel, error) {
	// 在发生切换场景，slave 变成 master，在变之前的 binlog 是不需要上传的
	return m.Query(
		db, "backup_status < ? and db_role=?",
		IBStatusSuccess, RoleMaster,
	)
}

// QuerySuccess 查询上传成功的文件，或者不需要上传的文件
func (m *BinlogFileModel) QuerySuccess(db *sqlx.DB) ([]*BinlogFileModel, error) {
	inWhere := sq.Eq{"backup_status": []int{IBStatusSuccess, FileStatusNoNeedUpload}}
	return m.Query(db, inWhere)
	// return m.Query(db, "backup_status IN ?", []int{IBStatusSuccess, FileStatusNoNeedUpload})
}

// QueryFailed 查询上传失败、过期的文件
func (m *BinlogFileModel) QueryFailed(db *sqlx.DB) ([]*BinlogFileModel, error) {
	inWhere := sq.NotEq{"backup_status": []int{IBStatusSuccess, FileStatusRemoved}}
	return m.Query(db, inWhere)
}

// Query 返回 binlog files 以文件名排序
func (m *BinlogFileModel) Query(db *sqlx.DB, pred interface{}, params ...interface{}) ([]*BinlogFileModel, error) {
	var files []*BinlogFileModel
	sqlBuilder := sq.Select(
		"bk_biz_id", "cluster_id", "cluster_domain", "db_role", "host", "port", "filename",
		"filesize", "start_time", "stop_time", "file_mtime", "backup_status", "task_id",
	).
		From(m.TableName()).Where(m.instanceWhere())
	sqlBuilder = sqlBuilder.Where(pred, params...).OrderBy("filename asc")
	sqlStr, args, err := sqlBuilder.ToSql()
	if err != nil {
		return nil, err
	}
	logger.Debug("Query sqlStr: %s, args: %v", sqlStr, args)
	if err = db.Select(&files, sqlStr, args...); err != nil {
		return nil, err
	}
	return files, nil
}

func (m *BinlogFileModel) QueryWithBuildWhere(db *sqlx.DB, builder *sq.SelectBuilder) ([]*BinlogFileModel, error) {
	var files []*BinlogFileModel
	sqlStr, args, err := builder.ToSql()

	if err != nil {
		return nil, err
	}
	logger.Debug("build where Query sqlStr: %s, args: %v", sqlStr, args)
	// fmt.Println("ssss", sqlStr, args)
	if err = db.Select(&files, sqlStr, args...); err != nil {
		return nil, err
	}
	return files, nil
}

// QueryLastFileReport 获取上一轮最后被处理的文件
func (m *BinlogFileModel) QueryLastFileReport(db *sqlx.DB) (*BinlogFileModel, error) {
	sqlBuilder := sq.Select("filename", "backup_status").From(m.TableName()).
		Where(m.instanceWhere()).OrderBy("filename desc").Limit(1)
	sqlStr, args, err := sqlBuilder.ToSql()
	if err != nil {
		return nil, err
	}
	logger.Info("QueryLastFileReport sqlStr: %s, args: %v", sqlStr, args)
	bf := &BinlogFileModel{}
	if err = db.Get(bf, sqlStr, args...); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return bf, nil
		}
		return nil, errors.Wrap(err, "QueryLastFileReport")
	}
	return bf, nil
}

// TimeInterval TODO
type TimeInterval struct {
	TaskName string `json:"task_name" db:"task_name"`
	Tag      string `json:"tag" db:"tag"`
	// 上一次运行时间
	LastRunAt string `json:"last_run_at" db:"last_run_at"`
}

// TableName TODO
func (t *TimeInterval) TableName() string {
	return "time_interval"
}

// Update TODO
func (t *TimeInterval) Update(db *sqlx.DB) error {
	nowTime := time.Now()
	t.LastRunAt = nowTime.Format(cst.DBTimeLayout) // 会吧 utc 转换成当前时区 str
	replace := sq.Replace("").Into(t.TableName()).
		Columns("task_name", "tag", "last_run_at").
		Values(t.TaskName, t.Tag, t.LastRunAt)
	sqlStr, args, err := replace.ToSql()
	if err != nil {
		return err
	}
	if _, err = db.Exec(sqlStr, args...); err != nil {
		return err
	}
	return nil
}

// Query TODO
func (t *TimeInterval) Query(db *sqlx.DB) (string, error) {
	selectBuilder := sq.Select("last_run_at").From(t.TableName()).
		Where("task_name=? and tag=?", t.TaskName, t.Tag)
	sqlstr, args, err := selectBuilder.ToSql()
	if err != nil {
		return "", err
	}
	var tt TimeInterval
	if err = db.Get(&tt, sqlstr, args...); err != nil {
		return "", err
	} else {
		return tt.LastRunAt, nil
	}
}

// IntervalOut 查询是否超过interval
// true: 已超过 interval, 满足执行频率，可以执行
func (t *TimeInterval) IntervalOut(db *sqlx.DB, dura time.Duration) bool {
	if dura == 0 {
		return false
	}
	lastRunAt, err := t.Query(db)
	// logger.Info("purge_interval:%s, lastRunAt:%s", dura.String(), lastRunAt)

	if err == sql.ErrNoRows {
		logger.Info("no time_interval item found for %s %s", t.TaskName, t.Tag)
		return true
	} else if err != nil {
		logger.Info("time_interval item found error for %s %s: %s", t.TaskName, t.Tag, err.Error())
		return true
	} else if lastRunAt == "" {
		return true
	}

	nowTime := time.Now()
	lastRunTime, err := time.ParseInLocation(cst.DBTimeLayout, lastRunAt, time.Local)
	if err != nil {
		logger.Error("error time_interval: task_name=%s, tag=%s, last_run_aat", t.TaskName, t.Tag, t.LastRunAt)
		return true
	}
	if nowTime.Sub(lastRunTime).Seconds() > dura.Seconds() {
		return true
	} else {
		return false
	}
}
