// Package dstatjob 统计job
package dstatjob

import (
	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbmon/cmd/basejob"
	"fmt"
	"os"
	"os/exec"
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

	job.Logger.Info("start", zap.Uint64("loopTimes", job.LoopTimes))

	if err := job.UpdateConf(); err != nil {
		job.Logger.Warn(fmt.Sprintf("UpdateConf return err %s", err.Error()))
		return
	}

	if len(job.MyConf.Servers) == 0 {
		job.Logger.Warn("no server in config")
		return
	}

	err := job.runDstatLoop()
	if err != nil {
		job.Logger.Warn(fmt.Sprintf("runDstat return err %s", err.Error()),
			zap.Uint64("loopTimes", job.LoopTimes))
	} else {
		job.Logger.Info("done", zap.Uint64("loopTimes", job.LoopTimes))
	}
}

// runDstatLoop 执行dstat循环
// 每次循环执行dstat命令，并等待1秒后继续循环. 这样保证了dstat命令的执行间隔为1秒.
// 如果dstat命令执行失败，则等待30秒后重试.
func (job *Job) runDstatLoop() error {
	for {
		job.LoopTimes++
		err := job.runDstat()
		if err != nil {
			return err
		}
		time.Sleep(1 * time.Second)
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
	// 如果没有dstat 命令,则不执行
	if _, err := exec.LookPath("dstat"); err != nil {
		job.Logger.Warn("dstat command not found", zap.Error(err))
		// sleep 60 seconds
		time.Sleep(60 * time.Second) // 等待60秒后重试. 如果这里sleep 太短时间，会导致频繁地尝试.
		return fmt.Errorf("dstat command not found: %w", err)
	}
	// 执行dstat命令, 将结果写入到日志文件中
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
		time.Sleep(30 * time.Second) // 等待60秒后重试. 如果这里sleep 太短时间，会导致频繁地尝试.
		return fmt.Errorf("runDstat return err: %w", err)
	}
	if err := cmd.Run(); err != nil {
		time.Sleep(30 * time.Second) // 等待60秒后重试. 如果这里sleep 太短时间，会导致频繁地尝试.
		job.Logger.Warn("runDstat return err", zap.Error(err))
		return err
	}
	return nil
}
