// Package dbmonheartbeat 心跳
package dbmonheartbeat

import (
	"dbm-services/mongodb/db-tools/dbmon/cmd/basejob"
	"dbm-services/mongodb/db-tools/dbmon/cmd/mongojob"
	"fmt"
	"runtime"
	"sync"

	"go.uber.org/zap"

	"dbm-services/mongodb/db-tools/dbmon/config"
)

const MongoDbmonHeartBeatMetricName = "mongo_dbmon_heart_beat"

// GlobDbmonHeartbeatJob global var
var globDbmonHeartbeatJob *Job
var dbmonHeartOnce sync.Once

// Job 心跳job
type Job struct {
	basejob.BaseJob
}

// GetJob 新建上报心跳任务
func GetJob(conf *config.DbMonConfig, logger *zap.Logger, jobName string) *Job {
	dbmonHeartOnce.Do(func() {
		globDbmonHeartbeatJob = &Job{
			BaseJob: basejob.BaseJob{
				Name:   jobName,
				Conf:   conf,
				Logger: logger.With(zap.String("job", jobName)),
			},
		}
	})
	return globDbmonHeartbeatJob
}

// loggerMemInfo 打印内存信息
func loggerMemInfo(logger *zap.Logger) {
	var m runtime.MemStats
	runtime.ReadMemStats(&m)
	logger.Info("meminfo", zap.Uint64("AllocM", m.Alloc/1024/1024),
		zap.Uint64("Sys", m.Sys/1024/1024),
		zap.Uint64("NumGC", uint64(m.NumGC)),
	)
}

// Run 执行例行心跳metric上报 会带第一个实例的维度信息
func (job *Job) Run() {
	job.Logger.Info("start", zap.Uint64("loopTimes", job.LoopTimes))
	loggerMemInfo(job.Logger)

	if err := job.UpdateConf(); err != nil {
		job.Logger.Warn(fmt.Sprintf("UpdateConf return err %s", err.Error()))
		return
	}

	if len(job.MyConf.Servers) == 0 {
		job.Logger.Warn("no server in config")
		return
	}

	err := job.sendHeartBeat(&job.MyConf.BkMonitorBeat, &job.MyConf.Servers[0])
	if err != nil {
		job.Logger.Warn(fmt.Sprintf("SendHeartBeat return err %s", err.Error()),
			zap.Uint64("loopTimes", job.LoopTimes))
	} else {
		job.Logger.Info("done", zap.Uint64("loopTimes", job.LoopTimes))
	}
}

// sendHeartBeat 发送心跳 会带第一个实例的维度信息
func (job *Job) sendHeartBeat(conf *config.BkMonitorBeatConfig, serverConf *config.ConfServerItem) error {
	msgH, err := mongojob.GetBkMonitorBeatSender(conf, serverConf)
	if err != nil {
		return err
	}
	return msgH.SendTimeSeriesMsg(conf.MetricConfig.DataID, conf.MetricConfig.Token,
		serverConf.IP, MongoDbmonHeartBeatMetricName, 1, job.Logger)
}
