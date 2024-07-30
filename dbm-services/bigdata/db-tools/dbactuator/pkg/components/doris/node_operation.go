package doris

import (
	"fmt"
	"os"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// NodeOperationParams 节点操作参数 结构体
type NodeOperationParams struct {
	// Host 主机IP
	Host string `json:"host" validate:"required,ip"`
	// Component 组件/角色
	Component string `json:"component"`
	// Operation 操作
	Operation string `json:"operation"`
}

// NodeOperationService 节点操作Service
type NodeOperationService struct {
	// GeneralParam 通用参数
	GeneralParam *components.GeneralParam
	// Params 节点操作特定参数
	Params *NodeOperationParams
	// RollBackContext 回滚上下文
	RollBackContext rollback.RollBackObjects
	// InstallParams 安装参数
	InstallParams
}

// CleanData TODO
// not update anymore, need to fix
func (i *NodeOperationService) CleanData() (err error) {
	// 清除crontab
	logger.Info("获取crontab")
	out, err := osutil.ListCrontb(i.ExecuteUser)
	if err != nil {
		logger.Error("获取crontab失败", err)
		return err
	}
	if len(out) > 0 {
		extraCmd := fmt.Sprintf("crontab -u %s -r", i.ExecuteUser)
		logger.Info("清除crontab, [%s]", extraCmd)
		if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("[%s] execute failed, %v", extraCmd, err)
			return err
		}
	}

	// 强杀进程
	extraCmd := `ps -ef | egrep 'supervisord|java'|grep -v grep |awk {'print "kill -9 " $2'}|sh`
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
	extraCmd = `sed -i '/dorisprofile/d' /etc/profile`
	logger.Info("clean provile, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}
	// 删除dorisenv
	extraCmd = `rm -rf /data/doris*`
	logger.Info("删除doris初始安装目录, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	// 删除数据目录
	extraCmd = `df |grep data|grep -vw '/data'|awk '{print $NF}'|while read line;do rm -rf $line/dorisdata*;done`
	logger.Info("删除dorisdata, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}
	return nil
}

// StartStopComponent TODO
func (i *NodeOperationService) StartStopComponent() (err error) {
	// 调用Supervisor 封装命令
	if err := SupervisorCommand(i.Params.Operation, i.Params.Component); err != nil {
		logger.Error("shell execute failed, %v", err)
		return err
	}
	logger.Info("%s doris process %s successfully", i.Params.Operation, i.Params.Component)
	return nil
}

// FirstLaunch TODO
func (i *NodeOperationService) FirstLaunch() (err error) {
	// 执行 supervisorctl update
	if err := SupervisorUpdate(); err != nil {
		logger.Error("shell execute failed, %v", err)
		return err
	}
	logger.Info("doris process %s first launch successfully", i.Params.Component)
	return nil
}

// SupervisorCommand Supervisor 命令集
func SupervisorCommand(command string, component string) error {
	execCommand := fmt.Sprintf("supervisorctl %s %s", command, component)
	if _, err := osutil.ExecShellCommand(false, execCommand); err != nil {
		logger.Error("[%s] execute failed, %v", execCommand, err)
		return err
	}
	return nil
}

// SupervisorAddConfig Supervisor 添加配置
func SupervisorAddConfig(supervisorConfDir string, component string) error {

	group := RoleEnum(component).Group()
	data := []byte(fmt.Sprintf(`[program:%s]
command=/data/dorisenv/%s/bin/start_%s.sh ; the program (relative uses PATH, can take args)
numprocs=1 ; number of processes copies to start (def 1)
autostart=true ; start at supervisord start (default: true)
startsecs=3 ; # of secs prog must stay up to be running (def. 1)
startretries=99 ; max # of serial start failures when starting (default 3)
autorestart=true ; when to restart if exited after running (def: unexpected)
exitcodes=0 ; 'expected' exit codes used with autorestart (default 0,2)
user=mysql ;
stopsignal=KILL ;
stopasgroup=true ;
killasgroup=true ;
redirect_stdout=false ; 
redirect_stderr=false ; redirect proc stderr to stdout (default false)`, component, component, group))

	componentIni := supervisorConfDir + "/" + component + ".ini"

	if err := os.WriteFile(componentIni, data, 0644); err != nil {
		logger.Error("write %s failed, %v", componentIni, err)
		return err
	}
	return nil
}

// SupervisorUpdate TODO
func SupervisorUpdate() error {
	return SupervisorCommand("update", "")
}
