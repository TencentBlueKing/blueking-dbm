package checkhealthjob

import (
	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbmon/cmd/basejob"
	"dbm-services/mongodb/db-tools/dbmon/mylog"
	"dbm-services/mongodb/db-tools/dbmon/pkg/linuxproc"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"slices"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"go.uber.org/zap"

	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/embedfiles"
	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"

	"github.com/pkg/errors"
)

// checkHealthHandle 全局任务句柄
var checkHealthHandle *CheckHealthJob
var onceGetCheckHealthHandle sync.Once

var errNoOutputFromMongo = errors.New("no output from mongo")
var errAuthenticationFailed = errors.New("authentication failed")
var errBadState = errors.New("bad state")
var errConnectionFailed = errors.New("connection failed")

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
const mongoshBin = "/usr/local/mongodb/bin/mongosh"
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
	for i := range job.MyConf.Servers {
		job.runOneServer(&job.MyConf.Servers[i])
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

	loginTimeout := getLoginTimeout(svrItem, logger)
	err := checkService(mongoBin, loginTimeout, svrItem, logger)
	logger.Info("checkService result", zap.Int("loginTimeout", loginTimeout), zap.Any("err", err))
	if err == nil {
		return
	}
	// checkService 返回的几种情况：
	/*
		1. 连接失败
		2. 认证失败
		3. 状态异常 (mongod)
	*/
	logger.Error("checkService failed, err: " + err.Error())
	if errors.Is(err, errAuthenticationFailed) {
		// 认证失败
		config.SendEvent(&job.MyConf.BkMonitorBeat, svrItem, consts.EventMongoLogin, consts.WarnLevelCritical,
			err.Error(), logger)
		return
	}
	if errors.Is(err, errBadState) {
		// 状态异常
		config.SendEvent(&job.MyConf.BkMonitorBeat, svrItem, consts.EventMongoLogin, consts.WarnLevelCritical,
			err.Error(), logger)
		return
	}

	elapsedTime := time.Since(startTime).Seconds()
	// 检查 进程是否存在，存在： 发送消息LoginTimeout
	// Port被别的进程占用，此处算是误告，但问题不大，反正都需要人工处理.
	using, err := checkPortInUse(svrItem.Port)
	logger.Info("checkPortInUse", zap.Int("port", svrItem.Port), zap.Bool("using", using), zap.Error(err))
	if using {
		// 进程存在 发送消息LoginTimeout
		config.SendEvent(&job.MyConf.BkMonitorBeat, svrItem, consts.EventMongoLogin, consts.WarnLevelCritical,
			fmt.Sprintf("login timeout, taking %0.1f seconds", elapsedTime), logger)
		return
	}

	// 如果已屏蔽告警，不会尝试拉起进程
	if config.IsAlarmShield(svrItem,
		"skip to start mongo because isAlarmShield", job.Logger) {
		return
	}

	// 进程不存在，尝试启动
	// 启动成功: 发送消息LoginSuccess
	// 启动失败: 发送消息LoginFailed
	if err := startMongo(svrItem.Port, logger); err != nil {
		logger.Warn("startMongo failed", zap.Error(err))
	}
	startTime = time.Now()
	job.Err = checkService(mongoBin, loginTimeout, svrItem, logger)
	logger.Info(fmt.Sprintf("checkService again,  cost %0.1f seconds, err: %v",
		time.Since(startTime).Seconds(), job.Err))
	if job.Err == nil {
		// 发送消息LoginSuccess
		config.SendEvent(&job.MyConf.BkMonitorBeat, svrItem, consts.EventMongoRestart, consts.WarnLevelWarning,
			"restarted", logger)
	} else {
		// 发送消息LoginFailed
		config.SendEvent(&job.MyConf.BkMonitorBeat,
			svrItem, consts.EventMongoRestart, consts.WarnLevelCritical,
			"restart failed with error: "+job.Err.Error(), logger)
	}

}

func getLoginTimeout(svrItem *config.ConfServerItem, logger *zap.Logger) int {
	loginTimeoutVal, err := config.ClusterConfig.GetInt64(svrItem, config.SegmentMonitor, config.KeyLoginTimeout, 10)
	if err != nil {
		logger.Warn("get loginTimeout from config failed, use default 10", zap.Error(err))
		return 10
	}
	// 有效值为 [5, 360]，与 cluster_config 注释一致
	if loginTimeoutVal < 5 {
		loginTimeoutVal = 5
	} else if loginTimeoutVal > 360 {
		loginTimeoutVal = 360
	}
	return int(loginTimeoutVal)
}

const secondsDay = 86400

const defaultLogMaxCount = 30

// removeOldMongoLogFiles 删除旧文件
// 删除/data/mongolog/port/mongo.log* 和 /data1/mongolog/port/mongo.log*文件，保留配置天数前的文件（默认15天，最小2天）.
// 并按 log.maxcount（默认30）限制本地 mongo.log* 个数，超出从最旧开始删，不删除正在写的 mongo.log。
func removeOldMongoLogFiles(svrItem *config.ConfServerItem, logger *zap.Logger) {
	logMaxTime, err := config.ClusterConfig.GetInt64(svrItem, config.SegmentLog, config.KeyMaxTime, secondsDay*15)
	if err != nil {
		logger.Warn("get log maxtime from config failed, use default 15 days", zap.Error(err))
		logMaxTime = secondsDay * 15
	}
	if logMaxTime < secondsDay*2 {
		logMaxTime = secondsDay * 2
	}
	logMaxCount, err := config.ClusterConfig.GetInt64(svrItem, config.SegmentLog, config.KeyMaxCount, defaultLogMaxCount)
	if err != nil {
		logger.Warn("get log maxcount from config failed, use default 30", zap.Error(err))
		logMaxCount = defaultLogMaxCount
	}
	if logMaxCount < 1 {
		logMaxCount = 1
	}
	portStr := strconv.Itoa(svrItem.Port)
	for _, baseDir := range []string{"/data/mongolog", "/data1/mongolog"} {
		logPattern := path.Join(baseDir, portStr, "mongo.log*")
		if err := removeOldFile(logPattern, logMaxTime, logger); err != nil {
			logger.Error("remove old file failed", zap.String("pattern", logPattern), zap.Error(err))
		}
		if err := removeExcessMongoLogFiles(logPattern, int(logMaxCount), logger); err != nil {
			logger.Error("remove excess mongo log files failed", zap.String("pattern", logPattern), zap.Error(err))
		}
	}
}

// removeOldFile removes old files that match the pattern.
// Delete file if modTime < now - maxTimeSeconds.
// Single file failure (e.g. Stat/Remove) is logged and does not stop other files.
func removeOldFile(pattern string, maxTimeSeconds int64, logger *zap.Logger) error {
	files, err := filepath.Glob(pattern)
	if err != nil {
		return err
	}

	now := time.Now().Unix()
	for _, file := range files {
		fileInfo, err := os.Stat(file)
		if err != nil {
			logger.Warn("stat file failed, skip", zap.String("file", file), zap.Error(err))
			continue
		}

		if now-fileInfo.ModTime().Unix() > maxTimeSeconds {
			if err := os.Remove(file); err != nil {
				logger.Warn("remove old file failed", zap.String("file", file), zap.Error(err))
				continue
			}
			logger.Info("remove old file", zap.String("file", file))
		}
	}
	return nil
}

type mongoLogFileInfo struct {
	path    string
	modTime int64
}

// removeExcessMongoLogFiles keeps at most maxCount files matching pattern.
// Never deletes the live log basename "mongo.log"; deletes oldest rotated files first.
func removeExcessMongoLogFiles(pattern string, maxCount int, logger *zap.Logger) error {
	if maxCount < 1 {
		maxCount = 1
	}
	files, err := filepath.Glob(pattern)
	if err != nil {
		return err
	}
	if len(files) <= maxCount {
		return nil
	}

	var candidates []mongoLogFileInfo
	total := 0
	for _, file := range files {
		fileInfo, err := os.Stat(file)
		if err != nil {
			logger.Warn("stat file failed, skip", zap.String("file", file), zap.Error(err))
			continue
		}
		total++
		if filepath.Base(file) == "mongo.log" {
			continue
		}
		candidates = append(candidates, mongoLogFileInfo{path: file, modTime: fileInfo.ModTime().Unix()})
	}
	if total <= maxCount || len(candidates) == 0 {
		return nil
	}

	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].modTime < candidates[j].modTime
	})

	toRemove := total - maxCount
	if toRemove > len(candidates) {
		toRemove = len(candidates)
	}
	for i := 0; i < toRemove; i++ {
		file := candidates[i].path
		if err := os.Remove(file); err != nil {
			logger.Warn("remove excess mongo log file failed", zap.String("file", file), zap.Error(err))
			continue
		}
		logger.Info("remove excess mongo log file", zap.String("file", file), zap.Int("maxCount", maxCount))
	}
	return nil
}

// checkPortInUse 分析/proc/net/tcp，判断端口是否被占用
/*
# get_pid_by_port
# tlinux 2.2/2.6测试ok.  lsof -i :27003 -t -sTCP:LISTEN
#lsofCmd := NewCmdBuilder().Append("lsof", "-i", fmt.Sprintf(":%d", port), "-t", "-sTCP:LISTEN")
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
func checkService(bin string, loginTimeout int, svrItem *config.ConfServerItem, logger *zap.Logger) error {
	user := svrItem.UserName
	pass := svrItem.Password
	authDb := "admin"
	port := fmt.Sprintf("%d", svrItem.Port)
	out, errOut, err := ExecLoginJsNoDb(bin, loginTimeout, svrItem.IP, port, user, pass, authDb,
		embedfiles.MongoLoginJs, logger)

	// if err is
	// not nil, return error, and log the error
	logger.Info(fmt.Sprintf("ExecLoginJs %s %s:%d timeout:%d stdout: %s, stderr: %s, err:%v",
		bin, svrItem.IP, svrItem.Port, loginTimeout, out, errOut, err))

	if len(out) == 0 {
		return errNoOutputFromMongo
	}

	connectSuccess := false
	authSuccess := false
	stateOK := false
	stateVal := ""

	// split out by '\n'
	lines := strings.Split(out, "\n")
	for _, line := range lines {
		if strings.Contains(line, "connect_success true") {
			connectSuccess = true
		} else if strings.Contains(line, "auth_success 1") {
			authSuccess = true
		} else if strings.Contains(line, "state ") {
			parts := strings.Fields(line)
			if len(parts) >= 2 && parts[0] == "state" {
				stateVal = parts[1]
				stateOK = (stateVal == "1" || stateVal == "2" || stateVal == "7")
			}
		}
	}
	logger.Info(fmt.Sprintf("authSuccess: %v, stateOK: %v, stateVal: %s", authSuccess, stateOK, stateVal))

	if !connectSuccess {
		return errConnectionFailed
	}
	if !authSuccess {
		return errAuthenticationFailed
	}
	if !stateOK {
		return errors.Wrapf(errBadState, "state is %s", parseState(stateVal))
	}
	return nil
}

func startMongo(port int, logger *zap.Logger) error {
	startMongoCmd := mycmd.New(startMongoScript, fmt.Sprintf("%d", port))
	ret, err := startMongoCmd.Run(60 * time.Second)
	logger.Info(fmt.Sprintf("exec %s return stdout: %s, stderr: %s, err:%v",
		startMongoCmd.GetCmdLine("", false), ret.GetStdout(), ret.GetStderr(), err))
	if err != nil {
		return errors.Wrap(err, "startMongo failed")
	}
	return nil
}

func parseState(state string) string {
	stateMap := map[string]string{
		"0":  "startup",
		"1":  "primary",
		"2":  "secondary",
		"3":  "recovering",
		"5":  "startup2",
		"6":  "unknown",
		"7":  "arbiter",
		"8":  "down",
		"9":  "rollback",
		"10": "removed",
	}
	if state, ok := stateMap[state]; ok {
		return state
	}
	return "unknown-code(" + state + ")"
}
