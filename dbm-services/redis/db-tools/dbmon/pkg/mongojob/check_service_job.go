package mongojob

import (
	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/embedfiles"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/report"
	"fmt"
	"strings"
	"time"

	"github.com/pkg/errors"
)

// checkServiceJobHandle 全局任务句柄
var checkServiceJobHandle *CheckServiceJob

// GetCheckServiceJob 获取任务句柄
func GetCheckServiceJob(conf *config.Configuration) *CheckServiceJob {
	if checkServiceJobHandle == nil {
		lock.Lock()
		defer lock.Unlock()
		if checkServiceJobHandle == nil {
			checkServiceJobHandle = &CheckServiceJob{
				Conf: conf,
				Name: "login",
			}
		}
	}
	return checkServiceJobHandle
}

// CheckServiceJob 登录检查.
type CheckServiceJob struct { // NOCC:golint/naming(其他:设计如此)
	Name          string                `json:"name"`
	Conf          *config.Configuration `json:"conf"`
	Tasks         []*BackupTask         `json:"tasks"`
	RealBackupDir string                `json:"real_backup_dir"` // 如 /data/dbbak
	Reporter      report.Reporter       `json:"-"`
	Err           error                 `json:"-"`
}

/*
		sub conn_mongodb () {
	    my ( $self, $host, $port, $user, $pass, $timeout ) = @_;
	    my $cmd        = "/usr/local/mongodb/bin/mongo --quiet --eval \"{var user='$user';var pwd='$pass';}\" $host:$port/admin $RealBin/tools/login.js";
	    my $cmd_out    = $self->do_command_timeout_v2 ( $cmd, $timeout, 1 );
	    my $o          = $cmd_out->[2];
	    my $ok         = ( $o =~ /connect ok/ ) ? 1 : 0;
	    my $mongo_type = '';

	    if ( $o =~ /mongo_type:(\w+)/ ) {
	        $mongo_type = $1;
	    }
	    return ( $ok, $mongo_type, $o );
		}
*/
const mongoBin = "/usr/local/mongodb/bin/mongo"

// Run 执行例行备份. 被cron对象调用
func (job *CheckServiceJob) Run() {
	mylog.Logger.Info(fmt.Sprintf("%s Run start", job.Name))
	defer func() {
		mylog.Logger.Info(fmt.Sprintf("%s Run End, Err: %+v", job.Name, job.Err))
	}()

	for _, svrItem := range job.Conf.Servers {
		mylog.Logger.Info(fmt.Sprintf("job %s server: %s:%v start", job.Name, svrItem.ServerIP, svrItem.ServerPorts))
		job.runOneServer(&svrItem)
		mylog.Logger.Info(fmt.Sprintf("job %s server: %s:%v end", job.Name, svrItem.ServerIP, svrItem.ServerPorts))
	}

}

func (job *CheckServiceJob) runOneServer(svrItem *config.ConfServerItem) {
	if !consts.IsMongo(svrItem.ClusterType) {
		mylog.Logger.Warn(fmt.Sprintf("server %+v is not a mongo instance", svrItem.ServerIP))
		return
	}

	if len(svrItem.ServerPorts) == 0 {
		mylog.Logger.Error(fmt.Sprintf("server %+v has no port", svrItem.ServerIP))
		return
	}

	// loginTimeout := job.Conf.InstConfig.Get(svrItem.ClusterDomain, svrItem.ServerIP, "login", "timeout")
	loginTimeout := 10
	t := time.Now()
	err := checkService(loginTimeout, svrItem)
	mylog.Logger.Info(fmt.Sprintf("checkService %s:%d cost %0.1f seconds, err: %v",
		svrItem.ServerIP, svrItem.ServerPorts[0], time.Now().Sub(t).Seconds(), err))
	if err == nil {
		// ok
		return
	}

	// 检查 进程是否存在，存在： 发送消息LoginTimeout
	// Port被别的进程占用，此处算是误告，但问题不大，反正都需要人工处理.
	if checkPortInUse(svrItem.ServerPorts[0]) {
		// 进程存在
		// 发送消息LoginTimeout
		SendEvent(job.Conf,
			svrItem,
			consts.EventMongoRestart,
			consts.WarnLevelError,
			fmt.Sprintf("mongo %s:%d login failed:timeout", svrItem.ServerIP, svrItem.ServerPorts[0]),
		)
		return
	}

	// 不存在，尝试启动
	//  启动成功: 发送消息LoginSuccess
	//  启动失败: 发送消息LoginFailed
	startMongo(svrItem.ServerPorts[0])
	err = checkService(loginTimeout, svrItem)
	if err == nil {
		// 发送消息LoginSuccess
		SendEvent(job.Conf,
			svrItem,
			consts.EventMongoRestart,
			consts.WarnLevelWarning,
			fmt.Sprintf("mongo %s:%d restart", svrItem.ServerIP, svrItem.ServerPorts[0]),
		)
	} else {
		// 发送消息LoginFailed
		SendEvent(job.Conf,
			svrItem,
			consts.EventMongoRestart,
			consts.WarnLevelError,
			fmt.Sprintf("mongo %s:%d login failed", svrItem.ServerIP, svrItem.ServerPorts[0]),
		)
	}

}

// checkPortInUse TODO
// todo checkPortInUse
// todo 分析/proc/tcp/netstat，判断端口是否被占用
func checkPortInUse(port int) bool {

	return false
}

// checkService TODO
func checkService(loginTimeout int, svrItem *config.ConfServerItem) error {
	user := "root"
	pass := "root"
	authDb := "admin"
	port := fmt.Sprintf("%d", svrItem.ServerPorts[0])
	outBuf, errBuf, err := ExecLoginJs(mongoBin, loginTimeout, svrItem.ServerIP, port, user, pass, authDb,
		embedfiles.MongoLoginJs)
	mylog.Logger.Info(fmt.Sprintf("outBuf: %s", outBuf))
	mylog.Logger.Info(fmt.Sprintf("errBuf: %s", errBuf))
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
	_, err := DoCommandWithTimeout(10, cmd, fmt.Sprintf("%d", port))
	if err != nil {
		return err
	}
	return nil
}

// SendWarnMessage TODO
func SendWarnMessage() {

}
