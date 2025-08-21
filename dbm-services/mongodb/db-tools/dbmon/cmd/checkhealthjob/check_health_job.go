package checkhealthjob

import (
	"dbm-services/mongodb/db-tools/dbmon/cmd/basejob"
	"dbm-services/mongodb/db-tools/dbmon/pkg/linuxproc"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"slices"
	"strconv"
	"strings"
	"sync"
	"time"

	"go.uber.org/zap"

	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/embedfiles"
	"dbm-services/mongodb/db-tools/dbmon/mylog"
	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"

	"github.com/pkg/errors"
)

// checkHealthHandle 全局任务句柄
var checkHealthHandle *CheckHealthJob
var onceGetCheckHealthHandle sync.Once

// GetCheckHealthHandle 获取任务句柄
func GetCheckHealthHandle(conf *config.DbMonConfig, logger *zap.Logger, jobName string) *CheckHealthJob {
	onceGetCheckHealthHandle.Do(func() {
		checkHealthHandle = &CheckHealthJob{
			BaseJob: basejob.BaseJob{
				Name:   jobName,
				Conf:   conf,
				Logger: logger.With(zap.String("job", jobName)),
			},
		}
	})
	return checkHealthHandle
}

// CheckHealthJob 登录检查.
type CheckHealthJob struct { // NOCC:golint/naming(其他:设计如此)
	basejob.BaseJob
}

const mongoBin = "/usr/local/mongodb/bin/mongo"
const startMongoScript = "/usr/local/mongodb/bin/start_mongo.sh"

// Run 执行CheckHealthJob任务
func (job *CheckHealthJob) Run() {
	job.LoopTimes++
	var logger = job.Logger
	if err := job.UpdateConf(); err != nil {
		logger.Warn(fmt.Sprintf("UpdateConf return err %s", err.Error()))
		return
	}
	logger.Info("start", zap.Int("loopTimes", int(job.LoopTimes)))
	for _, svrItem := range job.MyConf.Servers {
		job.runOneServer(&svrItem)
	}
	logger.Info("done", zap.Int("loopTimes", int(job.LoopTimes)), zap.Error(job.Err))
}

func (job *CheckHealthJob) runOneServer(svrItem *config.ConfServerItem) {
	logger := mylog.Logger.With(
		zap.String("job", job.Name),
		zap.String("instance", svrItem.Addr()))

	if !consts.IsMongo(svrItem.ClusterType) {
		logger.Warn(fmt.Sprintf("server %v is not a mongo instance", svrItem.IP))
		return
	}

	if job.LoopTimes%5 == 1 {
		logger.Info("removeOldMongoLogFiles", zap.Uint64("times", job.LoopTimes))
		removeOldMongoLogFiles(svrItem, logger)
	}

	startTime := time.Now()
	loginTimeoutVal, err := config.ClusterConfig.GetInt64(svrItem, config.SegmentMonitor, config.KeyLoginTimeout, 10)
	if err != nil {
		logger.Error(fmt.Sprintf("get loginTimeout from config failed: %v", err))
	}
	// loginTimeoutVal < 5, loginTimeoutVal = 5
	if loginTimeoutVal < 5 {
		loginTimeoutVal = 5
	} else if loginTimeoutVal > 300 {
		loginTimeoutVal = 300
	}

	loginTimeout := int(loginTimeoutVal)
	if err := checkService(loginTimeout, svrItem, logger); err == nil {
		return
	}
	elapsedTime := time.Since(startTime).Seconds()
	// 检查 进程是否存在，存在： 发送消息LoginTimeout
	// Port被别的进程占用，此处算是误告，但问题不大，反正都需要人工处理.
	using, err := checkPortInUse(svrItem.Port)
	logger.Debug(fmt.Sprintf("checkPortInUse %d return using:%v, err: %v", svrItem.Port, using, err))
	if err != nil {
		logger.Info(fmt.Sprintf("checkPortInUse took %0.1f seconds, err: %v", elapsedTime, err))
	}
	if using {
		// 进程存在 发送消息LoginTimeout
		config.SendEvent(&job.MyConf.BkMonitorBeat, svrItem, consts.EventMongoLogin, consts.WarnLevelError,
			fmt.Sprintf("login timeout, taking %0.1f seconds", elapsedTime), logger)
		return
	}

	// 如果已屏蔽告警，不会尝试拉起进程
	if config.IsAlaramShield(svrItem,
		"skip to start mongo because isAlaramShield", job.Logger) {
		return
	}

	// 进程不存在，尝试启动
	// 启动成功: 发送消息LoginSuccess
	// 启动失败: 发送消息LoginFailed
	startMongo(svrItem.Port, logger)
	startTime = time.Now()
	job.Err = checkService(loginTimeout, svrItem, logger)
	logger.Info(fmt.Sprintf("checkService again,  cost %0.1f seconds, err: %v",
		time.Since(startTime).Seconds(), job.Err))
	if job.Err == nil {
		// 发送消息LoginSuccess
		config.SendEvent(&job.MyConf.BkMonitorBeat, svrItem, consts.EventMongoRestart, consts.WarnLevelWarning,
			"restarted", logger)
	} else {
		// 发送消息LoginFailed
		config.SendEvent(&job.MyConf.BkMonitorBeat,
			svrItem, consts.EventMongoRestart, consts.WarnLevelError,
			"restart failed", logger)
	}

}

const secondsDay = 86400

// removeOldMongoLogFiles 删除旧文件
func removeOldMongoLogFiles(svrItem *config.ConfServerItem, logger *zap.Logger) {
	logPattern := path.Join("/data/mongolog", strconv.Itoa(svrItem.Port), "mongo.log*")
	logMaxTime, _ := config.ClusterConfig.GetInt64(svrItem, "log", "maxtime", secondsDay*15)
	if logMaxTime < secondsDay*2 {
		logMaxTime = secondsDay * 2
	}
	err := removeOldFile(logPattern, logMaxTime, logger)
	if err != nil {
		logger.Error(fmt.Sprintf("remove old file failed: %v", err))
	}
}

// RemoveOldFile removes the old file that matches the pattern.
// 1. delete file if modTime < now - maxTimeSeconds
// 2. delete 1 oldest file if totalSize > maxTotalSize (delete the oldest file first)
func removeOldFile(pattern string, maxTimeSeconds int64, logger *zap.Logger) error {
	files, err := filepath.Glob(pattern)
	if err != nil {
		return err
	}

	now := time.Now().Unix()
	for _, file := range files {
		fileInfo, err := os.Stat(file)
		if err != nil {
			return err
		}

		if now-fileInfo.ModTime().Unix() > maxTimeSeconds {
			err = os.Remove(file)
			logger.Info(fmt.Sprintf("remove old file %s", file))
			if err != nil {
				return err
			}
			continue
		}
	}
	return nil
}

// checkPortInUse 分析/proc/net/tcp，判断端口是否被占用
/*
# get_pid_by_port
# tlinux 2.2/2.6测试ok.  lsof -i :27003 -t -sTCP:LISTEN
#lsofCmd := mycmd.NewCmdBuilder().Append("lsof", "-i", fmt.Sprintf(":%d", port), "-t", "-sTCP:LISTEN")
*/
func checkPortInUse(port int) (bool, error) {
	tcpRows, err := linuxproc.ProcNetTcp(nil)
	if err != nil {
		return false, err
	}
	idx := slices.IndexFunc(tcpRows, func(row linuxproc.NetTcp) bool {
		return row.LocalPort == port && row.St == linuxproc.LISTEN
	})

	return idx >= 0, nil
}

// checkService 尝试登录
func checkService(loginTimeout int, svrItem *config.ConfServerItem, logger *zap.Logger) error {
	user := svrItem.UserName
	pass := svrItem.Password
	authDb := "admin"
	port := fmt.Sprintf("%d", svrItem.Port)
	outBuf, errBuf, err := ExecLoginJs(mongoBin, loginTimeout, svrItem.IP, port, user, pass, authDb,
		embedfiles.MongoLoginJs, logger)
	logger.Info(fmt.Sprintf("ExecLoginJs %s timeout:%d stdout: %q, stderr: %q", port, loginTimeout, outBuf, errBuf))
	if err == nil {
		return nil
	}
	if len(outBuf) == 0 {
		return errors.New("login failed")
	}
	// ExecLoginJs
	if strings.Contains(string(outBuf), "connect ok") {
		return nil
	}
	return errors.New("login failed")
}

func startMongo(port int, logger *zap.Logger) error {
	ret, err := DoCommandWithTimeout(60, startMongoScript, fmt.Sprintf("%d", port))
	logger.Info(fmt.Sprintf("exec %s return err:%v", ret.Cmdline, err))
	if err != nil {
		return err
	}
	return nil
}
