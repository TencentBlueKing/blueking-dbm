package keylifecycle

import (
	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/models/myredis"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/report"
	"dbm-services/redis/db-tools/dbmon/util"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"time"
)

// GlobRedisKeyLifeCycleJob global var
var GlobRedisKeyLifeCycleJob *Job

// Job tendis key 生命周期Job 入口
type Job struct { // NOCC:golint/naming(其他:设计如此)
	Conf          *config.Configuration `json:"conf"`
	StatTask      *Task                 `json:"stat_task"`
	RealBackupDir string                `json:"real_backup_dir"`
	HotKeyRp      report.Reporter       `json:"-"`
	BigKeyRp      report.Reporter       `json:"-"`
	KeyModeRp     report.Reporter       `json:"-"`
	KeyLifeRp     report.Reporter       `json:"-"`
	Err           error                 `json:"-"`
}

// InitRedisKeyLifeCycleJob tendis key 生命周期Job
func InitRedisKeyLifeCycleJob(conf *config.Configuration) {
	GlobRedisKeyLifeCycleJob = &Job{
		Conf: conf,
	}
}

// Run 执行例行任务
func (job *Job) Run() {
	mylog.Logger.Info("keylifecycle wakeup,start running...")
	defer func() {
		if job.Err != nil {
			mylog.Logger.Info(fmt.Sprintf("keylifecycle end fail,err:%v", job.Err))
		} else {
			mylog.Logger.Info("keylifecycle end succ")
		}
	}()
	job.Err = nil
	if job.precheck(); job.Err != nil {
		return
	}

	if job.GetReporter(); job.Err != nil {
		return
	}
	defer job.HotKeyRp.Close()
	defer job.BigKeyRp.Close()
	defer job.KeyModeRp.Close()
	defer job.KeyLifeRp.Close()

	if job.createTasks(); job.Err != nil {
		return
	}

	if job.Err = job.StatTask.RunStat(); job.Err != nil {
		return
	}
}

func (job *Job) precheck() {
	if _, job.Err = os.Stat(job.Conf.KeyLifeCycle.StatDir); os.IsNotExist(job.Err) {
		if job.Err = os.Mkdir(job.Conf.KeyLifeCycle.StatDir, fs.ModePerm); job.Err != nil {
			return
		}
	}

	baseBins := []string{
		consts.TendisKeyLifecycleBin,
		consts.LdbTendisplusBin,
		consts.LdbWithV38Bin,
		consts.LdbWithV513Bin,
	}
	for _, binfile := range baseBins {
		if !util.FileExists(binfile) {
			job.Err = fmt.Errorf("file :%s does not exist|%+v", binfile, job.Err)
		}
	}
}

// GetReporter 上报者
func (job *Job) GetReporter() {
	reportDir := filepath.Join(job.Conf.ReportSaveDir, "keylifecycle")
	util.MkDirsIfNotExists([]string{reportDir})
	util.LocalDirChownMysql(reportDir)
	job.HotKeyRp, job.Err = report.NewFileReport(filepath.Join(reportDir,
		fmt.Sprintf(consts.RedisHotKeyReporter, time.Now().Local().Format(consts.FilenameDayLayout))))
	job.BigKeyRp, job.Err = report.NewFileReport(filepath.Join(reportDir,
		fmt.Sprintf(consts.RedisBigKeyReporter, time.Now().Local().Format(consts.FilenameDayLayout))))
	job.KeyModeRp, job.Err = report.NewFileReport(filepath.Join(reportDir,
		fmt.Sprintf(consts.RedisKeyModeReporter, time.Now().Local().Format(consts.FilenameDayLayout))))
	job.KeyLifeRp, job.Err = report.NewFileReport(filepath.Join(reportDir,
		fmt.Sprintf(consts.RedisKeyLifeReporter, time.Now().Local().Format(consts.FilenameDayLayout))))
}

func (job *Job) createTasks() {
	var password string
	localInstances := []Instance{}

	mylog.Logger.Info(fmt.Sprintf("keylifecycle start servers : %+v", job.Conf.Servers))
	for _, svrItem := range job.Conf.Servers {
		if !consts.IsRedisMetaRole(svrItem.MetaRole) {
			mylog.Logger.Info(fmt.Sprintf("keylifecycle start but unkonwn role : %s", svrItem.MetaRole))
			continue
		}
		for _, port := range svrItem.ServerPorts {
			if password, job.Err = myredis.GetRedisPasswdFromConfFile(port); job.Err != nil {
				return
			}

			server := Instance{
				App:      svrItem.BkBizID,
				IP:       svrItem.ServerIP,
				Port:     port,
				Addr:     fmt.Sprintf("%s:%d", svrItem.ServerIP, port),
				Domain:   svrItem.ClusterDomain,
				Password: password,
			}

			if server.Cli, job.Err = myredis.NewRedisClientWithTimeout(server.Addr,
				server.Password, 0, consts.TendisTypeRedisInstance, time.Second); job.Err != nil {
				return
			}

			var info map[string]string
			if info, job.Err = server.Cli.Info("all"); job.Err != nil {
				return
			}

			server.Role = info["role"]
			server.Version = info["redis_version"]
			localInstances = append(localInstances, server)
		}
	}
	job.StatTask = NewKeyStatTask(localInstances, &job.Conf.KeyLifeCycle,
		job.HotKeyRp, job.BigKeyRp, job.KeyModeRp, job.KeyLifeRp)
}
