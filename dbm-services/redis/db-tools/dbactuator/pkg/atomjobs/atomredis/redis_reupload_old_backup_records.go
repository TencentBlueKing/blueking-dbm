package atomredis

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"

	"dbm-services/redis/db-tools/dbactuator/pkg/backupsys"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/report"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisBinlogHistorySchema TODO
type RedisBinlogHistorySchema struct {
	ID         int64  `json:"-" gorm:"primaryKey;column:id;not null`
	ReportType string `json:"report_type" gorm:"column:report_type;not null;default:''"`
	BkBizID    string `json:"bk_biz_id" gorm:"column:bk_biz_id;not null;default:''"`
	BkCloudID  int64  `json:"bk_cloud_id" gorm:"column:bk_cloud_id;not null;default:0"`
	ServerIP   string `json:"server_ip" gorm:"column:server_ip;not null;default:''"`
	ServerPort int    `json:"server_port" gorm:"column:server_port;not null;default:0"`
	Domain     string `json:"domain" gorm:"column:domain;not null;default:'';index"`
	// TendisplusInstance or TendisSSDInstance
	DbType string `json:"db_type" gorm:"column:db_type;not null;default:''"`
	Role   string `json:"role" gorm:"column:role;not null;default:''"`
	// 备份路径,如 /data/dbbak/binlog/30000
	BackupDir string `json:"backup_dir" gorm:"column:backup_dir;not null;default:''"`
	// 备份的目标文件(已压缩)
	BackupFile string `json:"backup_file" gorm:"column:backup_file;not null;default:''"`
	// binlog对应的 kvstoreidx
	KvstoreIdx int `json:"kvstoreidx" gorm:"column:kvstoreidx;not null;default:0"`
	// 备份文件大小(已压缩)
	BackupFileSize int64 `json:"backup_file_size" gorm:"column:backup_file_size;not null;default:0"`
	// binlog文件生成时间(非压缩)
	StartTime time.Time `json:"start_time" gorm:"column:start_time;not null;default:'';index"`
	// binlog文件最后修改时间(非压缩)
	EndTime      time.Time `json:"end_time" gorm:"column:end_time;not null;default:'';index"`
	TimeZone     string    `json:"time_zone" gorm:"column:time_zone;not null;default:''"`
	BackupTaskID string    `json:"backup_taskid" gorm:"column:backup_taskid;not null;default:''"`
	// 目前为空
	BackupMD5 string `json:"backup_md5" gorm:"column:backup_md5;not null;default:''"`
	// REDIS_BINLOG
	BackupTag string `json:"backup_tag" gorm:"column:backup_tag;not null;default:''"`
	// shard值
	ShardValue string `json:"shard_value" gorm:"column:shard_value;not null;default:''"`
	Status     string `json:"status" gorm:"column:status;not null;default:''"`
	Message    string `json:"message" gorm:"column:message;not null;default:''"`
	// 本地文件是否已删除,未被删除为0,已被删除为1
	LocalFileRemoved int `json:"-" gorm:"column:local_file_removed;not null;default:0"`
}

// TableName TODO
func (r *RedisBinlogHistorySchema) TableName() string {
	return "redis_binlog_history"
}

// Addr string
func (r *RedisBinlogHistorySchema) Addr() string {
	return r.ServerIP + ":" + strconv.Itoa(r.ServerPort)
}

type redisBinlogReport struct {
	RedisBinlogHistorySchema
	StartTime string `json:"start_time"`
	EndTime   string `json:"end_time"`
}

// reuploadBackupRecordsParams 参数
type reuploadBackupRecordsParams struct {
	BkBizID       string            `json:"bk_biz_id" validate:"required"`
	BkCloudID     int64             `json:"bk_cloud_id"`
	ServerIP      string            `json:"server_ip" validate:"required"`
	ServerPorts   []int             `json:"server_ports" validate:"required"`
	ClusterDomain string            `json:"cluster_domain" validate:"required"`
	ClusterType   string            `json:"cluster_type" validate:"required"`
	MetaRole      string            `json:"meta_role" validate:"required"`
	ServerShards  map[string]string `json:"server_shards" `
	RecordsFile   string            `json:"records_file" validate:"required"`
	Force         bool              `json:"force"` // 如果某个备份记录解析出错,是否继续上传
}

// RedisReuploadOldBackupRecords TODO
type RedisReuploadOldBackupRecords struct {
	runtime            *jobruntime.JobGenericRuntime
	params             reuploadBackupRecordsParams
	backupClient       backupsys.BackupClient
	oldBackupRecrods   []oldBackupItem
	fullbackupReporter report.Reporter `json:"-"`
	binlogReporter     report.Reporter `json:"-"`
	binlogRow          RedisBinlogHistorySchema
	fullbackupRow      RedisFullbackupHistorySchema
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisReuploadOldBackupRecords)(nil)

// NewRedisReuploadOldBackupRecords TODO
func NewRedisReuploadOldBackupRecords() jobruntime.JobRunner {
	return &RedisReuploadOldBackupRecords{}
}

// Init 初始化
func (job *RedisReuploadOldBackupRecords) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m
	err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("json.Unmarshal failed,err:%+v", err))
		return err
	}
	// 参数有效性检查
	validate := validator.New()
	err = validate.Struct(job.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			job.runtime.Logger.Error("RedisReuploadOldBackupRecords Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisReuploadOldBackupRecords Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	return nil
}

// Name 原子任务名
func (job *RedisReuploadOldBackupRecords) Name() string {
	return "redis_reupload_old_backup_records"
}

// Run 执行
func (job *RedisReuploadOldBackupRecords) Run() (err error) {
	err = job.decodeOldBackupFile()
	if err != nil {
		return err
	}
	err = job.getReporter()
	if err != nil {
		return err
	}
	defer job.closeReporter()

	err = job.precheck()
	if err != nil && !job.params.Force {
		return err
	}
	err = job.reupload()
	if err != nil {
		return err
	}

	return nil
}

func (job *RedisReuploadOldBackupRecords) decodeOldBackupFile() error {
	if !util.FileExists(job.params.RecordsFile) {
		job.runtime.Logger.Error("decodeOldBackupFile failed,file not exist,file:%s", job.params.RecordsFile)
		return fmt.Errorf("file not exist,file:%s", job.params.RecordsFile)
	}
	// 读取文件全部内容并base64解码
	recordsBytes, err := os.ReadFile(job.params.RecordsFile)
	if err != nil {
		job.runtime.Logger.Error("decodeOldBackupFile os.ReadFile failed,err:%+v,file:%s", err, job.params.RecordsFile)
		return err
	}
	recordsStr := string(recordsBytes)
	recordsStr = strings.TrimSpace(recordsStr)
	decodeRet, err := base64.StdEncoding.DecodeString(recordsStr)
	if err != nil {
		job.runtime.Logger.Error("decodeOldBackupFile base64.StdEncoding.DecodeString failed,err:%+v,recordsBytes:%s,file:%s",
			err, string(recordsBytes), job.params.RecordsFile)
		return err
	}
	// 解析json
	err = json.Unmarshal(decodeRet, &job.oldBackupRecrods)
	if err != nil {
		job.runtime.Logger.Error("decodeOldBackupFile json.Unmarshal failed,err:%+v,file:%s", err, job.params.RecordsFile)
		return err
	}

	return nil
}

func (job *RedisReuploadOldBackupRecords) getReporter() (err error) {
	err = report.CreateReportDir()
	if err != nil {
		return
	}
	util.MkDirsIfNotExists([]string{consts.RedisReportSaveDir})
	// 全备的上报文件名用的是 当前日期的后一天:
	// 因为采集工具是文件有更新才去采集这个文件数据,否则不采集;
	// 如果用当天的日期,当天如果该集群没有全备了,上报文件不再有更新,此时采集工具就不会采集这个文件的数据。
	// 用后一天的日期,每个集群后一天肯定有全备,第二天全备执行时,会更新同样的上报文件,就可以保证采集工具一定会采集到这个文件的数据。
	nextDay := time.Now().Local().AddDate(0, 0, 1)
	fullReportFile := fmt.Sprintf(consts.RedisFullbackupRepoter, nextDay.Format(consts.FilenameDayLayout))
	// binlog的上报文件名用的是 当前日期:
	// 因为binlog每隔20分钟就会生成一个,意味着每隔20分钟,上报文件就会被更新一次,所以不用担心采集工具采集不到数据。
	binlogReportFile := fmt.Sprintf(consts.RedisBinlogRepoter, time.Now().Local().Format(consts.FilenameDayLayout))
	job.fullbackupReporter, err = report.NewFileReport(filepath.Join(consts.RedisReportSaveDir, fullReportFile))
	if err != nil {
		return
	}
	job.binlogReporter, err = report.NewFileReport(filepath.Join(consts.RedisReportSaveDir, binlogReportFile))
	if err != nil {
		return
	}
	util.LocalDirChownMysql(consts.RedisReportSaveDir)
	return nil
}

func (job *RedisReuploadOldBackupRecords) closeReporter() {
	job.binlogReporter.Close()
	job.fullbackupReporter.Close()
}

// precheck 前置检查
func (job *RedisReuploadOldBackupRecords) precheck() (err error) {
	for _, item := range job.oldBackupRecrods {
		if !item.IsValidFile() {
			job.runtime.Logger.Warn("reupload item is invalid,item:%s", util.ToString(item))
			continue
		}
		_, err = item.getPort()
		if err != nil {
			job.runtime.Logger.Error(err.Error())
			return err
		}
		_, err = item.getFileFullpath()
		if err != nil {
			job.runtime.Logger.Error(err.Error())
			return err
		}
		// 获取备份文件最后修改时间
		_, err = time.ParseInLocation(consts.UnixtimeLayout, item.FileLastMtime, time.Local)
		if err != nil {
			job.runtime.Logger.Error(err.Error())
			return err
		}
		_, err = item.getUpTime()
		if err != nil {
			job.runtime.Logger.Error(err.Error())
			return err
		}
		// 获取备份文件的备份目录
		_, err = item.getBackupDir()
		if err != nil {
			job.runtime.Logger.Error(err.Error())
			return err
		}
	}
	return nil
}

func (job *RedisReuploadOldBackupRecords) reupload() (err error) {
	var port int
	var backupDir, fullPath, shardVal string
	var upTime time.Time
	var addr string
	timeZone, _ := time.Now().Local().Zone()
	job.binlogRow = RedisBinlogHistorySchema{
		ReportType: consts.RedisBinlogBackupReportType,
		BkBizID:    job.params.BkBizID,
		BkCloudID:  job.params.BkCloudID,
		ServerIP:   job.params.ServerIP,
		Domain:     job.params.ClusterDomain,
		DbType:     util.GetRedisDbTypeByClusterType(job.params.ClusterType),
		Role:       job.params.MetaRole,
		TimeZone:   timeZone,
		Status:     consts.BackupStatusToBakSysSuccess,
		BackupTag:  consts.RedisBinlogTAG,
		Message:    "上传备份系统成功",
	}
	job.fullbackupRow = RedisFullbackupHistorySchema{
		ReportType: consts.RedisFullBackupReportType,
		BkBizID:    job.params.BkBizID,
		BkCloudID:  job.params.BkCloudID,
		ServerIP:   job.params.ServerIP,
		Domain:     job.params.ClusterDomain,
		DbType:     util.GetRedisDbTypeByClusterType(job.params.ClusterType),
		Role:       job.params.MetaRole,
		TimeZone:   timeZone,
		Status:     consts.BackupStatusToBakSysSuccess,
		BackupTag:  consts.RedisFullBackupTAG,
		Message:    "上传备份系统成功",
	}
	for _, item := range job.oldBackupRecrods {
		if !item.IsValidFile() {
			job.runtime.Logger.Warn("reupload item is invalid,item:%s", util.ToString(item))
			continue
		}
		port, err = item.getPort()
		if err != nil {
			continue
		}
		// 获取备份文件的备份目录
		backupDir, err = item.getBackupDir()
		if err != nil {
			continue
		}
		// 获取备份文件的全路径
		fullPath, err = item.getFileFullpath()
		if err != nil {
			continue
		}
		// 获取备份文件的时间
		upTime, err = item.getUpTime()
		if err != nil {
			continue
		}
		addr = item.SourceIP + ":" + strconv.Itoa(port)
		shardVal, _ = job.params.ServerShards[addr]
		job.setParams(port, backupDir, fullPath, item.Size, upTime, item.TaskID, shardVal, item.FileTag)
		err = job.DoReport(item.FileTag)
		if err != nil {
			job.runtime.Logger.Error("DoReport failed,err:%+v", err)
			continue
		}
	}
	return nil
}

// setParams 设置参数
func (job *RedisReuploadOldBackupRecords) setParams(port int, backupDir, backupFile string, backupFileSize int64,
	upTime time.Time, taskID, shardVal, fileTag string) {
	if fileTag == consts.RedisFullBackupTAG {
		job.fullbackupRow.ServerPort = port
		job.fullbackupRow.BackupDir = backupDir
		job.fullbackupRow.BackupFile = backupFile
		job.fullbackupRow.BackupFileSize = backupFileSize
		job.fullbackupRow.StartTime = upTime
		job.fullbackupRow.EndTime = upTime
		job.fullbackupRow.BackupTaskID = taskID
		job.fullbackupRow.ShardValue = shardVal
	} else if fileTag == consts.RedisBinlogTAG {
		job.binlogRow.ServerPort = port
		job.binlogRow.BackupDir = backupDir
		job.binlogRow.BackupFile = backupFile
		job.binlogRow.BackupFileSize = backupFileSize
		job.binlogRow.StartTime = upTime
		job.binlogRow.EndTime = upTime
		job.binlogRow.BackupTaskID = taskID
		job.binlogRow.ShardValue = shardVal
	}
}

// DoReport 执行上报
func (job RedisReuploadOldBackupRecords) DoReport(fileTag string) error {
	if fileTag == consts.RedisFullBackupTAG {
		reportRow := redisFullBackupReport{
			RedisFullbackupHistorySchema: job.fullbackupRow,
			StartTime:                    job.fullbackupRow.StartTime.Format(time.RFC3339),
			EndTime:                      job.fullbackupRow.EndTime.Format(time.RFC3339),
		}
		tmpBytes, _ := json.Marshal(reportRow)
		job.fullbackupReporter.AddRecord(string(tmpBytes)+"\n", true)
	} else if fileTag == consts.RedisBinlogTAG {
		reportRow := redisBinlogReport{
			RedisBinlogHistorySchema: job.binlogRow,
			StartTime:                job.binlogRow.StartTime.Format(time.RFC3339),
			EndTime:                  job.binlogRow.EndTime.Format(time.RFC3339),
		}
		tmpBytes, _ := json.Marshal(reportRow)
		job.binlogReporter.AddRecord(string(tmpBytes)+"\n", true)
	}
	return nil
}

// Retry times
func (job *RedisReuploadOldBackupRecords) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisReuploadOldBackupRecords) Rollback() error {
	return nil
}

type oldBackupItem struct {
	FileTag       string `json:"file_tag"`
	Status        string `json:"status"`
	UpTime        string `json:"uptime"`
	FileLastMtime string `json:"file_last_mtime"`
	Size          int64  `json:"size"`
	SourceIP      string `json:"source_ip"`
	TaskID        string `json:"task_id"`
	FileName      string `json:"file_name"`
}

// IsValidFile 上传成功的文件才是有效的
func (item *oldBackupItem) IsValidFile() bool {
	return item.Status == "4" && item.FileName != "" && item.FileLastMtime != "" && item.Size > 0
}

var tendisBinlogReg = regexp.MustCompile(`binlog-(\d+)-(\d+)-(\d+).log`)
var tendisFullBackupReg = regexp.MustCompile(`(\d+\.\d+\.\d+\.\d+)-(\d+)-`)

func (item *oldBackupItem) getPort() (port int, err error) {
	var ll01 []string
	var portStr string
	if item.FileTag == consts.RedisFullBackupTAG {
		ll01 = tendisFullBackupReg.FindStringSubmatch(item.FileName)
		portStr = ll01[2]
	} else if item.FileTag == consts.RedisBinlogTAG {
		ll01 = tendisBinlogReg.FindStringSubmatch(item.FileName)
		portStr = ll01[1]
	} else {
		err = fmt.Errorf("getPort invalid file tag:%s,backupRecord:%s", item.FileTag, util.ToString(item))
		return
	}
	port, err = strconv.Atoi(portStr)
	if err != nil {
		err = fmt.Errorf("getPort strconv.Atoi failed,err:%+v,backupRecord:%s", err, util.ToString(item))
		return
	}
	return
}

// getUpTime 获取备份文件的时间
func (item *oldBackupItem) getUpTime() (upTime time.Time, err error) {

	upTime, err = time.ParseInLocation(consts.UnixtimeLayout, item.UpTime, time.Local)
	if err != nil {
		err = fmt.Errorf("getUpTime time.ParseInLocation failed,err:%+v,up_time:%s,backupRecord:%s",
			err, item.UpTime, util.ToString(item))
		return
	}
	return
}

// getBackupDir 伪造备份文件的备份目录
func (item *oldBackupItem) getBackupDir() (dir string, err error) {
	if item.FileTag == consts.RedisFullBackupTAG {
		return "/data/dbbak/", nil
	} else if item.FileTag == consts.RedisBinlogTAG {
		port, err := item.getPort()
		if err != nil {
			return "", err
		}
		return filepath.Join("/data/dbbak/binlog/", strconv.Itoa(port)), nil
	} else {
		err = fmt.Errorf("getBackupDir invalid file tag:%s,backupRecord:%s", item.FileTag, util.ToString(item))
		return
	}
}

// getFileFullpath 获取备份文件的全路径
func (item *oldBackupItem) getFileFullpath() (fullPath string, err error) {
	dir, err := item.getBackupDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(dir, item.FileName), nil
}
