package mongojob

import (
	"dbm-services/mongodb/db-tools/dbmon/pkg/linuxproc"
	"fmt"
	"slices"
	"strings"
	"time"

	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/embedfiles"
	"dbm-services/mongodb/db-tools/dbmon/mylog"
	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"

	"github.com/pkg/errors"
)

// checkHealthHandle 全局任务句柄
var checkHealthHandle *CheckHealthJob

// GetCheckHealthHandle 获取任务句柄
func GetCheckHealthHandle(conf *config.Configuration) *CheckHealthJob {
	if checkHealthHandle == nil {
		lock.Lock()
		defer lock.Unlock()
		if checkHealthHandle == nil {
			checkHealthHandle = &CheckHealthJob{
				Conf: conf,
				Name: "checkhealth",
			}
		}
	}
	return checkHealthHandle
}

// CheckHealthJob 登录检查.
type CheckHealthJob struct { // NOCC:golint/naming(其他:设计如此)
	Name  string                `json:"name"`
	Conf  *config.Configuration `json:"conf"`
	Tasks []*BackupTask         `json:"tasks"`
	Err   error                 `json:"-"`
}

const mongoBin = "/usr/local/mongodb/bin/mongo"

// Run 执行例行备份. 被cron对象调用
func (job *CheckHealthJob) Run() {
	mylog.Logger.Info(fmt.Sprintf("%s Run start", job.Name))
	defer func() {
		mylog.Logger.Info(fmt.Sprintf("%s Run End, Err: %+v", job.Name, job.Err))
	}()

	for _, svrItem := range job.Conf.Servers {
		mylog.Logger.Info(fmt.Sprintf("job %s server: %s:%v start", job.Name, svrItem.ServerIP, svrItem.ServerPort))
		job.runOneServer(&svrItem)
		mylog.Logger.Info(fmt.Sprintf("job %s server: %s:%v end", job.Name, svrItem.ServerIP, svrItem.ServerPort))
	}

}

func (job *CheckHealthJob) runOneServer(svrItem *config.ConfServerItem) {
	if !consts.IsMongo(svrItem.ClusterType) {
		mylog.Logger.Warn(fmt.Sprintf("server %+v is not a mongo instance", svrItem.ServerIP))
		return
	}

	loginTimeout := 10
	t := time.Now()
	err := checkService(loginTimeout, svrItem)

	mylog.Logger.Info(fmt.Sprintf("checkService %s:%d cost %0.1f seconds, err: %v",
		svrItem.ServerIP, svrItem.ServerPort, time.Now().Sub(t).Seconds(), err))
	if err == nil {
		return
	}
	elapsedTime := time.Now().Sub(t).Seconds()

	// 检查 进程是否存在，存在： 发送消息LoginTimeout
	// Port被别的进程占用，此处算是误告，但问题不大，反正都需要人工处理.
	using, err := checkPortInUse(svrItem.ServerPort)
	if err != nil {
		mylog.Logger.Info(fmt.Sprintf("checkService %s:%d cost %0.1f seconds, err: %v",
			svrItem.ServerIP, svrItem.ServerPort, elapsedTime, err))
	}
	if using {
		// 进程存在
		// 发送消息LoginTimeout
		SendEvent(&job.Conf.BkMonitorBeat,
			svrItem,
			consts.EventMongoLogin,
			consts.WarnLevelError,
			fmt.Sprintf("login timeout, taking %0.1f seconds", elapsedTime),
		)
		return
	}

	// 不存在，尝试启动
	//  启动成功: 发送消息LoginSuccess
	//  启动失败: 发送消息LoginFailed
	startMongo(svrItem.ServerPort)
	err = checkService(loginTimeout, svrItem)
	if err == nil {
		// 发送消息LoginSuccess
		SendEvent(&job.Conf.BkMonitorBeat,
			svrItem,
			consts.EventMongoRestart,
			consts.WarnLevelWarning,
			fmt.Sprintf("restarted"),
		)
	} else {
		// 发送消息LoginFailed
		SendEvent(&job.Conf.BkMonitorBeat,
			svrItem,
			consts.EventMongoRestart,
			consts.WarnLevelError,
			fmt.Sprintf("restart failed"),
		)
	}

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
		return row.LocalPort == port
	})

	return idx >= 0, nil
}

// checkService 尝试登录
func checkService(loginTimeout int, svrItem *config.ConfServerItem) error {
	user := svrItem.UserName
	pass := svrItem.Password
	authDb := "admin"
	port := fmt.Sprintf("%d", svrItem.ServerPort)
	outBuf, errBuf, err := ExecLoginJs(mongoBin, loginTimeout, svrItem.ServerIP, port, user, pass, authDb,
		embedfiles.MongoLoginJs)
	mylog.Logger.Info(fmt.Sprintf("ExecLoginJs %s stdout: %q, stderr: %q", port, outBuf, errBuf))
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

func startMongo(port int) error {
	cmd := "/usr/local/mongodb/bin/start.sh"
	_, err := DoCommandWithTimeout(60, cmd, fmt.Sprintf("%d", port))
	if err != nil {
		return err
	}
	return nil
}
