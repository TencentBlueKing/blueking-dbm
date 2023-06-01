package hdfs

import (
	"fmt"
	"io/ioutil"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// NodeOperationParams TODO
type NodeOperationParams struct {
	Host      string `json:"host" validate:"required,ip"`
	Component string `json:"component"`
	Operation string `json:"operation"`
}

// NodeOperationService TODO
type NodeOperationService struct {
	GeneralParam    *components.GeneralParam
	Params          *NodeOperationParams
	RollBackContext rollback.RollBackObjects
	InstallParams
}

// StopAllProcess TODO
func (i *NodeOperationService) StopAllProcess() (err error) {
	// 停止进程
	if err := SupervisorCommand(Stop, All); err != nil {
		logger.Error("shell execute failed, %v", err)
		return err
	}
	logger.Info("Stop hdfs all process successfully")
	return nil
}

// StopHaProxy TODO
func (i *NodeOperationService) StopHaProxy() (err error) {
	// 停止进程
	extraCmd := "service stop haproxy"
	logger.Info("停止HaProxy, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
	}
	logger.Info("Stop hdfs all process successfully")
	return nil
}

// CleanData TODO
func (i *NodeOperationService) CleanData() (err error) {
	// 清除crontab
	logger.Info("获取crontab")
	out, err := osutil.ListCrontb(i.ExecuteUser)
	if err != nil {
		logger.Error("获取crontab失败", err)
		return err
	}
	logger.Debug("crontab: ", out)
	if len(out) > 0 {
		extraCmd := fmt.Sprintf("crontab -u %s -r", i.ExecuteUser)
		logger.Info("清除crontab, [%s]", extraCmd)
		if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("[%s] execute failed, %v", extraCmd, err)
			return err
		}
	}

	// 强杀进程
	extraCmd := `ps -ef | egrep 'supervisord|telegraf|consul'|grep -v grep |awk {'print "kill -9 " $2'}|sh`
	logger.Info("强杀进程, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = `rm -f /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord /usr/bin/java`
	logger.Info("删除软链, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	// clean profile
	extraCmd = `sed -i '/hdfsProfile/d' /etc/profile`
	logger.Info("clean provile, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}
	// 删除hadoopenv
	extraCmd = `rm -rf /data/hadoopenv`
	logger.Info("hadoopenv, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	// 删除数据目录
	extraCmd = `df |grep data|grep -vw '/data'|awk '{print $NF}'|while read line;do rm  -rf $line/hadoopdata*;done`
	logger.Info("删除hadoopdata, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}
	return nil
}

// StartComponent TODO
func (i *NodeOperationService) StartComponent() (err error) {

	// 如果为启动，判断是否存在supervisor配置，不存在则添加并update
	if i.Params.Operation == Start {
		judgeCommand := fmt.Sprintf("ls -l %s/%s.ini", i.SupervisorConfDir, i.Params.Component)
		if _, err = osutil.ExecShellCommand(false, judgeCommand); err != nil {
			logger.Error("shell execute failed, need init supervisor ini")
			if i.Params.Component == ZooKeeper {
				return SupervisorUpdateZooKeeperConfig(i.SupervisorConfDir)
			} else {
				return SupervisorUpdateHdfsConfig(i.SupervisorConfDir, i.Params.Component)
			}
		}
	}
	if err := SupervisorCommand(i.Params.Operation, i.Params.Component); err != nil {
		logger.Error("shell execute failed, %v", err)
		return err
	}
	logger.Info("%s hdfs process %s successfully", i.Params.Operation, i.Params.Component)
	return nil
}

// SupervisorCommand TODO
func SupervisorCommand(command string, component string) error {
	execCommand := fmt.Sprintf("supervisorctl %s %s", command, component)
	if _, err := osutil.ExecShellCommand(false, execCommand); err != nil {
		logger.Error("[%s] execute failed, %v", execCommand, err)
		return err
	}
	return nil
}

// SupervisorUpdateHdfsConfig TODO
func SupervisorUpdateHdfsConfig(supervisorConfDir string, component string) error {
	data := []byte(`[program:` + component + `]
command=hadoop-daemon-wrapper.sh start-foreground ` + component + ` ; the program (relative uses PATH, can take args)
numprocs=1 ; number of processes copies to start (def 1)
stopsignal=TERM ;
stopasgroup=true ;
killasgroup=true ;
autostart=true ; start at supervisord start (default: true)
user=hadoop ;
redirect_stdout=false ; 
redirect_stderr=false ; redirect proc stderr to stdout (default false)`)

	componentIni := supervisorConfDir + "/" + component + ".ini"

	if err := ioutil.WriteFile(componentIni, data, 0644); err != nil {
		logger.Error("write %s failed, %v", componentIni, err)
	}

	return SupervisorCommand("update", "")
}

// SupervisorUpdateZooKeeperConfig TODO
func SupervisorUpdateZooKeeperConfig(supervisorConfDir string) error {
	data := []byte(`[program:zookeeper]
command=/data/hadoopenv/zookeeper/bin/zkServer.sh start-foreground ; the program (relative uses PATH, can take args)
numprocs=1 ; number of processes copies to start (def 1)
autostart=true ; start at supervisord start (default: true)
startsecs=3 ; # of secs prog must stay up to be running (def. 1)
startretries=99 ; max # of serial start failures when starting (default 3)
autorestart=true ; when to restart if exited after running (def: unexpected)
exitcodes=0 ; 'expected' exit codes used with autorestart (default 0,2)
user=hadoop ;
stopsignal=KILL ;
redirect_stderr=true ; redirect proc stderr to stdout (default false)
stdout_logfile=/data/hadoopenv/zookeeper/zk_startup.log ; stdout log path, NONE for none; default AUTO
stdout_logfile_maxbytes=50MB ; max # logfile bytes b4 rotation (default 50MB)
stdout_logfile_backups=10 ; # of stdout logfile backups (default 10)`)

	componentIni := supervisorConfDir + "/zookeeper.ini"

	if err := ioutil.WriteFile(componentIni, data, 0644); err != nil {
		logger.Error("write %s failed, %v", componentIni, err)
	}
	return SupervisorCommand("update", "")
}
