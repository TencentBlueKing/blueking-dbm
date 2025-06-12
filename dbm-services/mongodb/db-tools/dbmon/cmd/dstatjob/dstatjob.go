// Package dstatjob 统计job
package dstatjob

import (
	"dbm-services/mongodb/db-tools/dbmon/cmd/basejob"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mycmd"
	"fmt"
	"os"
	"path"
	"sync"
	"time"

	"go.uber.org/zap"

	"dbm-services/mongodb/db-tools/dbmon/config"
)

const MongoDbmonDstatMetricName = "mongo_dbmon_dstat"

// GlobDbmonDstatJob global var
var GlobDstatJob *Job
var dstatOnce sync.Once

// Job 心跳job
type Job struct {
	basejob.BaseJob
}

// GetJob 新建上报心跳任务
func GetJob(conf *config.DbMonConfig, logger *zap.Logger, jobName string, workDir string) *Job {
	dstatOnce.Do(func() {
		GlobDstatJob = &Job{
			BaseJob: basejob.BaseJob{
				Name:    jobName,
				Conf:    conf,
				Logger:  logger.With(zap.String("job", jobName)),
				WorkDir: workDir,
			},
		}
	})
	return GlobDstatJob
}

// Run 执行例行心跳metric上报 会带第一个实例的维度信息
func (job *Job) Run() {
	job.LoopTimes++
	job.Logger.Info("start", zap.Uint64("loopTimes", job.LoopTimes))

	if err := job.UpdateConf(); err != nil {
		job.Logger.Warn(fmt.Sprintf("UpdateConf return err %s", err.Error()))
		return
	}

	if len(job.MyConf.Servers) == 0 {
		job.Logger.Warn("no server in config")
		return
	}

	err := job.runDstat()
	if err != nil {
		job.Logger.Warn(fmt.Sprintf("SendHeartBeat return err %s", err.Error()),
			zap.Uint64("loopTimes", job.LoopTimes))
	} else {
		job.Logger.Info("done", zap.Uint64("loopTimes", job.LoopTimes))
	}
}

// deleteOldDstatLogs 删除7天前的dstat日志
func (job *Job) deleteOldDstatLogs() error {
	// list all files in job.WorkDir, "logs"
	files, err := os.ReadDir(path.Join(job.WorkDir, "logs"))
	if err != nil {
		job.Logger.Warn("read logs dir return err", zap.Error(err))
		return err
	}
	sevenDayAgo := time.Now().AddDate(0, 0, -7)
	for _, file := range files {
		if file.IsDir() {
			continue
		}
		fileInfo, err := file.Info()
		if err != nil {
			job.Logger.Warn("get file info return err", zap.Error(err))
			continue
		}
		// if file.mtime is before 7 day ago, remove it
		if fileInfo.ModTime().Before(sevenDayAgo) {
			job.Logger.Info("remove file", zap.String("file", file.Name()))
			os.Remove(path.Join(job.WorkDir, "logs", file.Name()))
		}
	}
	return nil
}

// runDstat 执行dstat
func (job *Job) runDstat() error {
	// create dir if not exists
	if _, err := os.Stat(path.Join(job.WorkDir, "logs")); os.IsNotExist(err) {
		os.MkdirAll(path.Join(job.WorkDir, "logs"), 0755)
	}
	if job.LoopTimes%288 == 0 {
		if err := job.deleteOldDstatLogs(); err != nil {
			job.Logger.Warn("deleteOldDstatLogs return err", zap.Error(err))
			return err
		} else {
			job.Logger.Info("deleteOldDstatLogs done")
		}
	}
	ymd := time.Now().Format("20060102")
	dstatLogFile := path.Join(job.WorkDir, "logs", fmt.Sprintf("dstat.%s", ymd))
	cmd, err := mycmd.NewMyExec(
		mycmd.New("dstat", "-t", "-m", "-a", "1", "300"),
		10*time.Minute,
		dstatLogFile,
		dstatLogFile,
		true,
	)

	if err != nil {
		job.Logger.Warn("runDstat return err", zap.Error(err))
		return err
	}
	if err := cmd.Run(); err != nil {
		job.Logger.Warn("runDstat return err", zap.Error(err))
		return err
	}
	return nil
}
