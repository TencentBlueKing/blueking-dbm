package doris

import (
	"fmt"
	"os"
	"os/user"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// InitSystemConfigParams TODO
type InitSystemConfigParams struct {
	// Host 主机IP
	Host string `json:"host" validate:"required,ip" ` // 本机IP
	// Role 角色
	Role Role `json:"role" validate:"required"`
}

// InitSystemConfigService TODO
type InitSystemConfigService struct {
	// GeneralParam 通用参数
	GeneralParam *components.GeneralParam
	// Params InitSystemConfig 所需参数
	Params *InitSystemConfigParams
	// RollBackContext 回滚上下文
	RollBackContext rollback.RollBackObjects
}

// InitSystemConfig TODO
func (i *InitSystemConfigService) InitSystemConfig() (err error) {
	// 创建执行用户
	err = i.CreateExecuteUser()
	if err != nil {
		return err
	}
	// 初始化安装目录
	err = i.InitInstallDir()

	return nil
}

// CreateExecuteUser 创建执行用户
func (i *InitSystemConfigService) CreateExecuteUser() (err error) {
	// 创建用户
	execUser := DefaultDorisExecUser
	logger.Info("检查用户[%s]是否存在", execUser)
	if _, err := user.Lookup(execUser); err != nil {
		logger.Info("用户[%s]不存在，开始创建", execUser)
		if output, err := osutil.ExecShellCommand(false,
			fmt.Sprintf("useradd %s -g root -s /bin/bash -d /home/mysql",
				execUser)); err != nil {
			logger.Error("创建系统用户[%s]失败,%s, %v", execUser, output, err.Error())
			return err
		}
		logger.Info("用户[%s]创建成功", execUser)
	} else {
		logger.Info("用户[%s]存在, 跳过创建", execUser)
	}
	return nil
}

// InitInstallDir 初始化安装目录
func (i *InitSystemConfigService) InitInstallDir() (err error) {
	// mkdir
	extraCmd := fmt.Sprintf("mkdir -p %s ; mkdir -p %s ; chown -R mysql %s",
		DefaultDorisEnv, DefaultDorisDataDir, "/data/doris*")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err.Error())
		return err
	}
	return nil
}

// UpdateSystemConfig 修改系统配置
func (i *InitSystemConfigService) UpdateSystemConfig() (err error) {
	// 修改系统参数
	// 设置系统最大打开文件句柄数
	noFileParams := []byte(`* soft noFileParams 65536
* hard noFileParams 65536`)
	limitFile := "/etc/security/limits.d/doris-no-file.conf"
	if err := os.WriteFile(limitFile, noFileParams, 0644); err != nil {
		logger.Error("write %s failed, %v", limitFile, err)
	}
	// 关闭swap
	extraCmd :=
		`sed -i '/swap/s/^/#/' /etc/fstab
swapoff -a`
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("关闭swap分区执行失败", err.Error())
	}
	if i.Params.Role == Hot || i.Params.Role == Cold {
		// BE节点 修改vma数量
		addConfCmd := "echo 'vm.max_map_count=2000000'>> /etc/sysctl.conf; sysctl -p"
		delConfCmd := "sed -i '/vm\\.max_map_count/d' /etc/sysctl.conf;"
		if _, err := osutil.ExecShellCommand(false, delConfCmd+addConfCmd); err != nil {
			logger.Error("修改vma数量", err.Error())
		}
	}
	return nil
}

// WriteProfile 写入环境变量到profile
func (i *InitSystemConfigService) WriteProfile() (err error) {
	logger.Info("写入/etc/profile")
	// doris profile 内容
	scripts := []byte(`cat << 'EOF' > /data/dorisenv/dorisprofile
export JAVA_HOME=/data/dorisenv/java/jdk
export JRE=$JAVA_HOME/jre
export PATH=$JAVA_HOME/bin:$JRE_HOME/bin:$PATH
export CLASSPATH=".:$JAVA_HOME/lib:$JRE/lib:$CLASSPATH"
export LC_ALL=en_US
export DORIS_HOME=/data/dorisenv/` + i.Params.Role + `
EOF

chown mysql  /data/dorisenv/dorisprofile
sed -i '/dorisprofile/d' /etc/profile
echo "source /data/dorisenv/dorisprofile" >>/etc/profile`)

	scriptFile := fmt.Sprintf("%s/init.sh", DefaultDorisEnv)
	if err := os.WriteFile(scriptFile, scripts, 0644); err != nil {
		logger.Error("write %s failed, %v", scriptFile, err)
	}

	extraCmd := fmt.Sprintf("bash %s", scriptFile)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("修改系统参数失败:%s", err.Error())
		return err
	}
	return nil
}
