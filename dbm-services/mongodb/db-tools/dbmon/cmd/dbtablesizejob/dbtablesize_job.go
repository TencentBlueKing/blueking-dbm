// Package dbtablesizejob 在 backup 节点采集库表数据量并写入本地 report
package dbtablesizejob

import (
	"context"
	"fmt"
	"os"
	"path"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/mongodb/db-tools/dbmon/cmd/basejob"
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/report"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.uber.org/zap"
)

const (
	reportType            = "dbtablesize"
	connectTimeout        = 30 * time.Second
	defaultTimeoutSeconds = int64(300)
	// reportSavedDays report 文件本地保留天数
	reportSavedDays = 2
	// skipHeartbeatMaxBytes test.dbmon_heartbeat 小于该大小时不上报
	skipHeartbeatMaxBytes = int64(1024 * 1024)

	// MetricCollectSuccess 采集是否成功：1 成功，0 失败/关闭
	MetricCollectSuccess = "mongo_dbtablesize_collect_success"
	// MetricCollectDurationSeconds 本次采集耗时（秒）
	MetricCollectDurationSeconds = "mongo_dbtablesize_collect_duration_seconds"
)

var (
	globDbTableSizeJob  *Job
	dbTableSizeOnce     sync.Once
	cleanReportLastTime int64
)

// Job 库表数据量采集
type Job struct {
	basejob.BaseJob
}

// GetJob 获取库表数据量采集任务单例
func GetJob(conf *config.DbMonConfig, logger *zap.Logger, jobName string) *Job {
	dbTableSizeOnce.Do(func() {
		globDbTableSizeJob = &Job{
			BaseJob: basejob.BaseJob{
				Name:   jobName,
				Conf:   conf,
				Logger: logger.With(zap.String("job", jobName)),
			},
		}
	})
	return globDbTableSizeJob
}

// SizeRecord 库/表数据量上报记录
// 不含 app_name（可能含中文）；ip/port 使用 instance_host/instance_port
type SizeRecord struct {
	BkCloudID     int64   `json:"bk_cloud_id"`
	BkBizID       int     `json:"bk_biz_id"`
	App           string  `json:"app"`
	ClusterDomain string  `json:"cluster_domain"`
	ClusterId     int64   `json:"cluster_id"`
	ClusterName   string  `json:"cluster_name"`
	ClusterType   string  `json:"cluster_type"`
	RoleType      string  `json:"role_type"`
	MetaRole      string  `json:"meta_role"`
	Instance      string  `json:"instance"`
	InstanceHost  string  `json:"instance_host"`
	InstancePort  int     `json:"instance_port"`
	SetName       string  `json:"set_name"`
	Shard         string  `json:"shard"`
	DB            string  `json:"db"`
	Collection    string  `json:"collection"`
	DataSize      int64   `json:"data_size"`
	StorageSize   int64   `json:"storage_size"`
	IndexSize     int64   `json:"index_size"`
	Count         int64   `json:"count"`
	AvgObjSize    float64 `json:"avg_obj_size"`
	ReportTime    string  `json:"report_time"`
}

type dbStatsResult struct {
	DataSize    int64   `bson:"dataSize"`
	StorageSize int64   `bson:"storageSize"`
	IndexSize   int64   `bson:"indexSize"`
	Objects     int64   `bson:"objects"`
	AvgObjSize  float64 `bson:"avgObjSize"`
	OK          int     `bson:"ok"`
}

type collStatsResult struct {
	Size           int64   `bson:"size"`
	StorageSize    int64   `bson:"storageSize"`
	TotalIndexSize int64   `bson:"totalIndexSize"`
	Count          int64   `bson:"count"`
	AvgObjSize     float64 `bson:"avgObjSize"`
	OK             int     `bson:"ok"`
}

var skipDBs = map[string]struct{}{
	"admin":  {},
	"local":  {},
	"config": {},
}

// Run 仅在 backup 节点执行
func (job *Job) Run() {
	job.LoopTimes++
	job.Logger.Info("start", zap.Uint64("loopTimes", job.LoopTimes))
	defer job.Logger.Info("end", zap.Uint64("loopTimes", job.LoopTimes))

	if err := job.UpdateConf(); err != nil {
		job.Logger.Warn(fmt.Sprintf("UpdateConf return err %s", err.Error()))
		return
	}

	now := time.Now()
	if now.Unix()-cleanReportLastTime > 24*3600 {
		job.cleanReport(now, reportSavedDays)
		cleanReportLastTime = now.Unix()
	}

	for i := range job.MyConf.Servers {
		svr := &job.MyConf.Servers[i]
		if !isBackupRole(svr.MetaRole) {
			job.Logger.Info(fmt.Sprintf("skip dbtablesize for %s", svr.MetaRole),
				zap.String("instance", svr.Addr()))
			continue
		}
		enable, err := config.ClusterConfig.GetOne(svr, config.SegmentDBTableSize, config.KeyEnable)
		if err != nil {
			job.Logger.Warn("get dbtablesize.enable failed, use default true",
				zap.String("instance", svr.Addr()), zap.Error(err))
			enable = config.ValueTrue
		}
		if enable == config.ValueFalse {
			job.Logger.Info("dbtablesize disabled", zap.String("instance", svr.Addr()))
			job.reportCollectStatus(svr, false, 0, 0)
			continue
		}
		if config.IsAlarmShield(svr, "skip dbtablesize because Shielded", job.Logger) {
			continue
		}
		timeoutSeconds, err := config.ClusterConfig.GetInt64(
			svr, config.SegmentDBTableSize, config.KeyTimeout, defaultTimeoutSeconds)
		if err != nil {
			job.Logger.Warn("get dbtablesize.timeout failed, use default 300 seconds",
				zap.String("instance", svr.Addr()), zap.Error(err))
			timeoutSeconds = defaultTimeoutSeconds
		}
		if timeoutSeconds <= 0 {
			job.Logger.Warn("invalid dbtablesize.timeout, use default 300 seconds",
				zap.String("instance", svr.Addr()), zap.Int64("timeout", timeoutSeconds))
			timeoutSeconds = defaultTimeoutSeconds
		}
		start := time.Now()
		err = job.runOneServer(svr, time.Duration(timeoutSeconds)*time.Second)
		duration := time.Since(start).Seconds()
		success := float64(0)
		if err != nil {
			job.Logger.Warn("dbtablesize failed",
				zap.String("instance", svr.Addr()), zap.Error(err))
		} else {
			success = 1
		}
		job.reportCollectStatus(svr, true, success, duration)
	}
}

// reportCollectStatus 上报采集状态指标；发送失败仅记日志，不影响采集结果
func (job *Job) reportCollectStatus(svr *config.ConfServerItem, enabled bool, success, durationSeconds float64) {
	enabledLabel := config.ValueFalse
	if enabled {
		enabledLabel = config.ValueTrue
	}
	beat := &job.MyConf.BkMonitorBeat
	port := strconv.Itoa(svr.Port)

	msgH, err := config.GetBkMonitorBeatSender(beat, svr)
	if err != nil {
		job.Logger.Warn("report collect success metric failed",
			zap.String("instance", svr.Addr()), zap.Error(err))
		return
	}
	msgH.SetLabel("enabled", enabledLabel).SetLabel("port", port)
	if err = msgH.SendTimeSeriesMsg(beat.MetricConfig.DataID, beat.MetricConfig.Token,
		svr.IP, MetricCollectSuccess, success, job.Logger); err != nil {
		job.Logger.Warn("report collect success metric failed",
			zap.String("instance", svr.Addr()), zap.Error(err))
	}

	msgH2, err := config.GetBkMonitorBeatSender(beat, svr)
	if err != nil {
		job.Logger.Warn("report collect duration metric failed",
			zap.String("instance", svr.Addr()), zap.Error(err))
		return
	}
	msgH2.SetLabel("enabled", enabledLabel).SetLabel("port", port)
	if err = msgH2.SendTimeSeriesMsg(beat.MetricConfig.DataID, beat.MetricConfig.Token,
		svr.IP, MetricCollectDurationSeconds, durationSeconds, job.Logger); err != nil {
		job.Logger.Warn("report collect duration metric failed",
			zap.String("instance", svr.Addr()), zap.Error(err))
	}
}

func isBackupRole(metaRole string) bool {
	return metaRole == consts.MetaRoleShardsvrBackup ||
		metaRole == consts.MetaRoleShardsvrBackupNewName
}

// cleanReport 删除 mtime 超过 savedDays 天的 report 文件
func (job *Job) cleanReport(nowTime time.Time, savedDays int) {
	_, reportDir, _ := consts.GetMongoReportPath(reportType)
	if reportDir == "" {
		return
	}
	files, err := os.ReadDir(reportDir)
	if err != nil {
		if !os.IsNotExist(err) {
			job.Logger.Warn("cleanReport read dir failed",
				zap.String("dir", reportDir), zap.Error(err))
		}
		return
	}
	for _, file := range files {
		filePath := path.Join(reportDir, file.Name())
		fileInfo, err := os.Stat(filePath)
		if err != nil {
			job.Logger.Warn("cleanReport stat failed", zap.String("file", filePath), zap.Error(err))
			continue
		}
		if nowTime.Sub(fileInfo.ModTime()) > time.Duration(savedDays)*24*time.Hour {
			if err := os.Remove(filePath); err != nil {
				job.Logger.Warn("cleanReport remove failed", zap.String("file", filePath), zap.Error(err))
			} else {
				job.Logger.Info("cleanReport removed", zap.String("file", filePath))
			}
		}
	}
}

func (job *Job) runOneServer(svr *config.ConfServerItem, timeout time.Duration) error {
	logger := job.Logger.With(zap.String("instance", svr.Addr()))
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	reportFile, _, _ := consts.GetMongoReportPath(reportType)
	if err := report.PrepareReportPath(reportFile); err != nil {
		return fmt.Errorf("prepare report path: %w", err)
	}

	client, err := mymongo.ConnectWithDirect(
		svr.IP, strconv.Itoa(svr.Port),
		svr.UserName, svr.Password, "admin",
		connectTimeout, true)
	if err != nil {
		return fmt.Errorf("connect: %w", err)
	}
	defer func() {
		_ = client.Disconnect(context.Background())
	}()

	dbs, err := client.ListDatabaseNames(ctx, bson.D{})
	if err != nil {
		return fmt.Errorf("listDatabases: %w", err)
	}

	reportTime := time.Now().Local().Format(time.RFC3339)
	written := 0
	for _, dbName := range dbs {
		if err := ctx.Err(); err != nil {
			return fmt.Errorf("collect timeout after %s: %w", timeout, err)
		}
		if _, skip := skipDBs[dbName]; skip {
			continue
		}
		n, err := job.collectAndWriteDB(ctx, client, svr, dbName, reportFile, reportTime, logger)
		if err != nil {
			if ctx.Err() != nil {
				return fmt.Errorf("collect timeout after %s: %w", timeout, ctx.Err())
			}
			logger.Warn("collect db failed", zap.String("db", dbName), zap.Error(err))
			continue
		}
		written += n
	}
	logger.Info("dbtablesize done", zap.Int("records", written), zap.String("report", reportFile))
	return nil
}

func (job *Job) collectAndWriteDB(
	ctx context.Context,
	client *mongo.Client,
	svr *config.ConfServerItem,
	dbName, reportFile, reportTime string,
	logger *zap.Logger,
) (int, error) {
	var dbStats dbStatsResult
	if err := client.Database(dbName).RunCommand(ctx, bson.D{{Key: "dbStats", Value: 1}}).
		Decode(&dbStats); err != nil {
		return 0, fmt.Errorf("dbStats: %w", err)
	}
	written := 0
	dbRec := newSizeRecord(svr, dbName, "", dbStats.DataSize, dbStats.StorageSize,
		dbStats.IndexSize, dbStats.Objects, dbStats.AvgObjSize, reportTime)
	if err := report.AppendObjectToFile(reportFile, dbRec); err != nil {
		return 0, fmt.Errorf("write db record: %w", err)
	}
	written++

	colls, err := client.Database(dbName).ListCollectionNames(ctx, bson.D{})
	if err != nil {
		return written, fmt.Errorf("listCollections: %w", err)
	}
	for _, coll := range colls {
		if err := ctx.Err(); err != nil {
			return written, err
		}
		if strings.HasPrefix(coll, "system.") {
			continue
		}
		var collStats collStatsResult
		if err := client.Database(dbName).RunCommand(
			ctx, bson.D{{Key: "collStats", Value: coll}}).Decode(&collStats); err != nil {
			logger.Warn("collStats failed",
				zap.String("db", dbName), zap.String("collection", coll), zap.Error(err))
			continue
		}
		if shouldSkipCollection(dbName, coll, collStats.Size) {
			logger.Debug("skip small heartbeat collection",
				zap.String("db", dbName), zap.String("collection", coll),
				zap.Int64("data_size", collStats.Size))
			continue
		}
		rec := newSizeRecord(svr, dbName, coll, collStats.Size, collStats.StorageSize,
			collStats.TotalIndexSize, collStats.Count, collStats.AvgObjSize, reportTime)
		if err := report.AppendObjectToFile(reportFile, rec); err != nil {
			logger.Warn("write collection record failed",
				zap.String("db", dbName), zap.String("collection", coll), zap.Error(err))
			continue
		}
		written++
	}
	return written, nil
}

// shouldSkipCollection 忽略小于 1MB 的 test.dbmon_heartbeat
func shouldSkipCollection(dbName, collection string, dataSize int64) bool {
	return dbName == "test" && collection == "dbmon_heartbeat" && dataSize < skipHeartbeatMaxBytes
}

func newSizeRecord(
	svr *config.ConfServerItem,
	dbName, collection string,
	dataSize, storageSize, indexSize, count int64,
	avgObjSize float64,
	reportTime string,
) SizeRecord {
	return SizeRecord{
		BkCloudID:     svr.BkCloudID,
		BkBizID:       svr.BkBizID,
		App:           svr.App,
		ClusterDomain: svr.ClusterDomain,
		ClusterId:     svr.ClusterId,
		ClusterName:   svr.ClusterName,
		ClusterType:   svr.ClusterType,
		RoleType:      svr.RoleType,
		MetaRole:      svr.MetaRole,
		Instance:      svr.Addr(),
		InstanceHost:  svr.IP,
		InstancePort:  svr.Port,
		SetName:       svr.SetName,
		Shard:         strings.TrimPrefix(svr.SetName, svr.ClusterName+"-"),
		DB:            dbName,
		Collection:    collection,
		DataSize:      dataSize,
		StorageSize:   storageSize,
		IndexSize:     indexSize,
		Count:         count,
		AvgObjSize:    avgObjSize,
		ReportTime:    reportTime,
	}
}
