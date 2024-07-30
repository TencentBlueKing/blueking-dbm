package doris

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/dorisutil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/esutil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
	"encoding/json"
	"fmt"
	"math"
	"net"
	"os"
	"strconv"
	"time"

	"github.com/pkg/errors"
)

// InstallDorisService TODO
type InstallDorisService struct {
	GeneralParam *components.GeneralParam
	Params       *InstallDorisParams
	InstallParams
	RollBackContext rollback.RollBackObjects
}

// InstallParams Doris安装配置 now by default
type InstallParams struct {
	InstallDir  string `json:"install_dir"`
	PkgDir      string `json:"pkg_dir"`
	DorisEnvDir string `json:"doris_env_dir"`
	MetaDataDir string `json:"meta_data_dir"`
	// DorisHomeDir      string `json:"doris_home_dir"`
	DorisConfDir      string `json:"doris_conf_dir"`
	SupervisorConfDir string `json:"supervisor_conf_dir"`
	ExecuteUser       string `json:"exec_user"`
}

// InstallDorisParams from db_flow
type InstallDorisParams struct {
	Host          string            `json:"host" validate:"required,ip"`
	Role          Role              `json:"role" validate:"required"`
	FeConf        map[string]string `json:"fe_conf"`                          // fe配置
	BeConf        map[string]string `json:"be_conf"`                          // be配置
	HttpPort      int               `json:"http_port" validate:"required"`    // http 端口
	QueryPort     int               `json:"query_port" validate:"required"`   // mysql查询端口
	RootPassword  string            `json:"root_password"`                    // 拥有节点管理权限默认用户root
	AdminPassword string            `json:"admin_password"`                   // 拥有grant权限默认用户admin
	Version       string            `json:"version"  validate:"required"`     // 版本号eg: 2.0.4
	ClusterName   string            `json:"cluster_name" validate:"required"` // 集群名
	MasterFeIp    string            `json:"master_fe_ip" validate:"ip"`       // 第一台FE IP
}

// InitDefaultInstallParam TODO
func InitDefaultInstallParam() (params InstallParams) {
	logger.Info("start InitDefaultInstallParam")

	return InstallParams{
		PkgDir:            DefaultPkgDir,
		InstallDir:        DefaultInstallDir,
		DorisEnvDir:       DefaultDorisEnv,
		MetaDataDir:       "",
		SupervisorConfDir: DefaultSupervisorConfDir,
		ExecuteUser:       DefaultDorisExecUser,
	}

}

// InstallSupervisor TODO
/**
 * @description:  安装supervisor
 * @return {*}
 */
func (i *InstallDorisService) InstallSupervisor() (err error) {
	// Todo: check supervisor exist
	// supervisor

	if !util.FileExists(i.SupervisorConfDir) {
		logger.Error("supervisor not exist, %v", err)
		return err
	}

	extraCmd := fmt.Sprintf("ln -sf %s %s", i.SupervisorConfDir+"/supervisord.conf",
		"/etc/supervisord.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("ln -sf %s %s", i.DorisEnvDir+"/supervisor/bin/supervisorctl",
		"/usr/local/bin/supervisorctl")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("ln -sf %s %s", i.DorisEnvDir+"/python/bin/supervisord",
		"/usr/local/bin/supervisord")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("chown -R mysql %s ", i.DorisEnvDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	// crontab
	extraCmd = `crontab -l -u mysql >/home/mysql/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
	}

	extraCmd = `cp /home/mysql/crontab.bak /home/mysql/crontab.tmp`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = `sed -i '/check_supervisord.sh/d' /home/mysql/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = "echo '*/1 * * * *  /data/dorisenv/supervisor/check_supervisord.sh " +
		">>/data/dorisenv/supervisor/check_supervisord.err 2>&1' >>/home/mysql/crontab.bak"
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = `crontab -u mysql /home/mysql/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	startCmd := `su - mysql -c "/usr/local/bin/supervisord -c /data/dorisenv/supervisor/conf/supervisord.conf"`
	logger.Info(fmt.Sprintf("execute supervisor [%s] begin", startCmd))
	pid, err := osutil.RunInBG(false, startCmd)
	logger.Info(fmt.Sprintf("execute supervisor [%s] end, pid: %d", startCmd, pid))
	if err != nil {
		return err
	}
	return nil
}

// RenderConfig TODO
func (i *InstallDorisService) RenderConfig() (err error) {
	roleEnum := RoleEnumByRole(i.Params.Role)
	group := roleEnum.Group()

	dorisConfDir := fmt.Sprintf(ConfDirTmpl, i.Params.Role)
	confFileName := fmt.Sprintf("%s.conf", group)
	logger.Info("now doris conf is %s/%s", dorisConfDir, confFileName)
	cidr, err := dorisutil.GetLocalNetwork()
	if err != nil {
		logger.Error("get local cidr failed ", err.Error())
		return err
	}
	if group == Fronted {
		// 修改默认配置
		feConfMap := i.Params.FeConf
		feConfMap[PriorityNetworks] = cidr
		// 修改JVM参数
		var instMem uint64
		if instMem, err = esutil.GetInstMem(); err != nil {
			logger.Error("获取实例内存失败, err: %w", err)
			return fmt.Errorf("获取实例内存失败, err: %w", err)
		}
		heapSize := int(math.Floor(0.8 * float64(instMem)))
		feConfMap[JavaOpts] = fmt.Sprintf(JavaOptsDefault, heapSize)
		feConfBytes, err := dorisutil.DefaultTransMap2Bytes(feConfMap)
		if err != nil {
			logger.Error("buffer concat fe config bytes failed %s", err.Error())
			return err
		}
		if err = os.WriteFile(dorisConfDir+"/"+confFileName, feConfBytes, 0644); err != nil {
			logger.Error("write fe config failed %s", err.Error())
			return err
		}
	} else if group == Backend {
		// 获取数据目录配置
		dataDirs := dorisutil.GetDataMountDir()
		dataDirConf := GenDorisDataDirConf(i.Params.Role, dataDirs)
		beConfMap := i.Params.BeConf
		beConfMap[PriorityNetworks] = cidr
		beConfMap[StorageRootPath] = dataDirConf

		beConfBytes, err := dorisutil.DefaultTransMap2Bytes(beConfMap)
		if err != nil {
			logger.Error("buffer concat be config bytes failed %s", err.Error())
			return err
		}
		if err = os.WriteFile(dorisConfDir+"/"+confFileName, beConfBytes, 0644); err != nil {
			logger.Error("write be config failed %s", err.Error())
			return err
		}
	}
	return nil

}

// StartFeByHelper TODO
func (i *InstallDorisService) StartFeByHelper() (err error) {

	// TODO
	/*
		1. 通过helper启动其他FE
		2. 本地调用Http接口测试服务是否正常启动
		3. 退出Fe
	*/
	if err := dorisutil.StartFeByHelper(i.DorisEnvDir, string(i.Params.Role),
		i.Params.MasterFeIp, FeEditLogPort); err != nil {
		return err
	}
	// 检查FE启动是否成功
	if err = i.CheckFrontEndStart(); err != nil {
		return err
	}
	// 停止通过helper启动的服务
	if err = i.StopByFeHelper(); err != nil {
		return err
	}
	return nil

}

// InstallDoris TODO
func (i *InstallDorisService) InstallDoris() (err error) {
	// supervisor 守护进程配置在这里添加
	if err = SupervisorAddConfig(i.SupervisorConfDir, string(i.Params.Role)); err != nil {
		logger.Error("write supervisor conf failed")
		return err
	}

	return SupervisorUpdate()
}

// GenDorisDataDirConf TODO
func GenDorisDataDirConf(role Role, dirs []string) string {
	dirConf := ""
	var diskType DiskType

	if role == Hot {
		diskType = SSD
	} else {
		diskType = HDD
	}
	concatWord := ""
	subPath := "mini_download"
	for _, dir := range dirs {
		// 生成配置同时生成目录并赋权给启动用户
		mkdirCmd := fmt.Sprintf("mkdir -p %s/dorisdata/%s; chown -R mysql:mysql %s/dorisdata", dir, subPath, dir)
		if _, err := osutil.ExecShellCommand(false, mkdirCmd); err != nil {
			logger.Error("初始化Doris数据目录%s/dorisdata失败:%s", dir, err.Error())
		}
		dirConf = fmt.Sprintf("%s%s%s/dorisdata,medium:%s", dirConf, concatWord, dir, diskType)
		concatWord = ";"
	}
	return dirConf
}

// CheckQeServiceStart 检查Follower QE service是否正常启动，
func (i *InstallDorisService) CheckQeServiceStart() (err error) {
	RetryCount := 3
	SleepDuration := 10 * time.Second
	for retryTimes := 0; retryTimes <= RetryCount; retryTimes++ {
		err = CheckHostPortOpen(i.Params.Host, i.Params.QueryPort)
		if err != nil {
			logger.Error("打开连接失败, ", err.Error())
			time.Sleep(SleepDuration)
			continue
		} else {
			return nil
		}
	}
	return errors.New("retry all failed")
}

// CheckHostPortOpen 检查主机端口是否打开
func CheckHostPortOpen(host string, port int) (err error) {
	timeout := 10 * time.Second
	conn, err := net.DialTimeout("tcp", net.JoinHostPort(host, strconv.Itoa(port)), timeout)

	if conn != nil {
		logger.Info("检查连接对象成功")
		defer conn.Close()
		return nil
	} else {
		return err
	}
}

// CheckFrontEndStart TODO
func (i *InstallDorisService) CheckFrontEndStart() (err error) {
	RetryCount := 3
	SleepDuration := 10 * time.Second
	url := fmt.Sprintf("http://%s:%d/api/bootstrap", i.Params.Host, i.Params.HttpPort)
	var statusStruct *BootstrapStatus

	for retryTimes := 0; retryTimes <= RetryCount; retryTimes++ {
		responseBody, err := dorisutil.HttpGet(url)
		if err != nil {
			logger.Error("httpGet failed", err.Error())
			// 等待5s
			time.Sleep(SleepDuration)
			continue
		}
		if err = json.Unmarshal(responseBody, &statusStruct); err != nil {
			logger.Error("transfer response to json failed", err.Error())
			// 等待5s
			time.Sleep(SleepDuration)
			continue
		}
		if statusStruct.Code != BootstrapStatusOK {
			logger.Error("bootstrap failed, msg is %s, err is %s", statusStruct.Message, err.Error())
			// 等待5s
			time.Sleep(SleepDuration)
			continue
		} else {
			return nil
		}
	}

	return errors.New("retry all failed")
}

// StopByFeHelper TODO
func (i *InstallDorisService) StopByFeHelper() (err error) {
	_, err = osutil.ExecShellCommand(false, fmt.Sprintf(
		"su - mysql -c \"%s/%s/bin/stop_fe.sh\"",
		i.DorisEnvDir, i.Params.Role))
	return err

}

// BootstrapStatus TODO
type BootstrapStatus struct {
	Code    int    `json:"code"`
	Message string `json:"msg"`
}
