package atomproxy

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/go-playground/validator/v10"

	"dbm-services/mongodb/db-tools/dbmon/util"
	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
)

// PredixyAddModulesCmdsParams 参数
type PredixyAddModulesCmdsParams struct {
	IP          string   `json:"ip" validate:"required"`
	Port        int      `json:"port" validate:"required"`         //  只支持1个端口
	LoadModules []string `json:"load_modules" validate:"required"` // 需要加载的模块, [redisbloom,rediscell,redisjson]
	ClusterType string   `json:"cluster_type" validate:"required"`
}

// PredixyAddModulesCmds predixy 增加module命令
type PredixyAddModulesCmds struct {
	runtime       *jobruntime.JobGenericRuntime
	params        PredixyAddModulesCmdsParams
	configFile    string
	proxyPassword string
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*PredixyAddModulesCmds)(nil)

// NewPredixyAddModulesCmds new
func NewPredixyAddModulesCmds() jobruntime.JobRunner {
	return &PredixyAddModulesCmds{}
}

// Init 初始化
func (job *PredixyAddModulesCmds) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m
	err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("json.Unmarshal failed,err:%+v", err))
		return err
	}
	// 参数有效性检查
	validate := validator.New()
	err = validate.Struct(job.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			job.runtime.Logger.Error("PredixyAddModulesCmds Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("PredixyAddModulesCmds Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	return nil
}

// Name 原子任务名
func (job *PredixyAddModulesCmds) Name() string {
	return "predixy_add_modules_cmds"
}

// Run 执行
func (job *PredixyAddModulesCmds) Run() (err error) {
	job.configFile, err = myredis.GetPredixyLocalConfFile(job.params.Port)
	if err != nil {
		return err
	}
	job.proxyPassword, err = myredis.GetProxyPasswdFromConfFlie(job.params.Port, consts.MetaRolePredixy)
	if err != nil {
		return err
	}
	// 如果存在一个module 认识，且他的命令不在配置文件中，则继续
	// 不继续的情况:
	// - 如果所有的module都不认识，找不到其对应的命令, 则无需继续了
	// - 如果所有module都已认识，且配置文件中没有对应的命令，则也无需继续了
	isAnyKnownModuleNotFoundCmds := false
	for _, module := range job.params.LoadModules {
		knownModule, moduleCmdInFile := job.IsModuleCmdInConfFile(job.configFile, module)
		if knownModule && !moduleCmdInFile {
			isAnyKnownModuleNotFoundCmds = true
			break
		}
	}
	if !isAnyKnownModuleNotFoundCmds {
		job.runtime.Logger.Warn("%s all modules not known or all modules commands alreayt in config file",
			job.params.LoadModules)
		return nil
	}
	// 删除配置文件中 CustomCommand 配置中的内容
	// sed命令意思是删除 CustomCommand 到 ###### 所有行
	sedCmd := fmt.Sprintf(`sed -i '/CustomCommand/,/######/d' %s`, job.configFile)
	job.runtime.Logger.Info(sedCmd)
	_, err = util.RunBashCmd(sedCmd, job.configFile, nil, 10*time.Second)
	if err != nil {
		return err
	}
	// 生成 CustomCommand内容并添加到配置文件中
	customCmdData := consts.GetPredixyModuleCommands(job.params.LoadModules)
	catCmd := fmt.Sprintf(`
cat >>%s<<EOF
%s
EOF
	`, job.configFile, customCmdData)
	job.runtime.Logger.Info(catCmd)
	_, err = util.RunBashCmd(catCmd, job.configFile, nil, 10*time.Second)
	if err != nil {
		return err
	}
	// 重启predixy
	if err = job.stopProxy(); err != nil {
		return err
	}
	if err = job.startProxy(); err != nil {
		return err
	}
	return nil
}

// IsModuleCmdInConfFile 配置文件中是否包含 module的命令
// 以module的第一个command作为判断标准
// 返回值:
// knownModule: true 表示 认识这个module,能找到其对应的命令
// (对于用户自定义的module,很多时候我们也不知道对应command,此时不用在predixy的customCommands中增加这些module的命令)
// moduleCmdInFile: true 表示 在配置文件中包含该module的命令.
func (job *PredixyAddModulesCmds) IsModuleCmdInConfFile(confFile, module string) (knownModule, moduleCmdInFile bool) {
	if module != consts.ModuleRedisBloom && module != consts.ModuleRedisJson && module != consts.ModuleRedisCell {
		// 目前只认识这三个module的命令
		return false, false
	}
	knownModule = true
	grepCmd := fmt.Sprintf(`grep -i %q %s`, module, confFile)
	ret, _ := util.RunBashCmd(grepCmd, "", nil, 10*time.Second)
	if ret != "" {
		moduleCmdInFile = true
	}
	return
}

// stopProxy 关闭 proxy
func (job *PredixyAddModulesCmds) stopProxy() (err error) {
	stopScript := ""
	stopScript = filepath.Join(consts.UsrLocal, "predixy", "bin", "stop_predixy.sh")
	_, err = os.Stat(stopScript)
	if err != nil && os.IsNotExist(err) {
		job.runtime.Logger.Info("%s not exist", stopScript)
		return nil
	}
	job.runtime.Logger.Info(fmt.Sprintf("su %s -c \"%s %d\"",
		consts.MysqlAaccount, stopScript, job.params.Port))

	maxRetryTimes := 5
	inUse := false
	for maxRetryTimes >= 0 {
		maxRetryTimes--
		util.RunLocalCmd("su",
			[]string{consts.MysqlAaccount, "-c", stopScript + " " + strconv.Itoa(job.params.Port)},
			"", nil, 10*time.Minute)
		inUse, err = util.CheckPortIsInUse(job.params.IP, strconv.Itoa(job.params.Port))
		if err != nil {
			job.runtime.Logger.Error(fmt.Sprintf("check %s:%d inUse failed,err:%v", job.params.IP, job.params.Port, err))
			return err
		}
		if !inUse {
			break
		}
		time.Sleep(2 * time.Second)
	}
	if inUse {
		err = fmt.Errorf("stop predixy (%s:%d) failed,port:%d still using", job.params.IP, job.params.Port, job.params.Port)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	job.runtime.Logger.Info("stop predixy (%s:%d) success", job.params.IP, job.params.Port)
	return nil
}

// startProxy 拉起 proxy
func (job *PredixyAddModulesCmds) startProxy() (err error) {
	startScript := ""
	port := job.params.Port
	startScript = filepath.Join(consts.UsrLocal, "predixy", "bin", "start_predixy.sh")
	job.runtime.Logger.Info(fmt.Sprintf("su %s -c \"%s\" 2>/dev/null",
		consts.MysqlAaccount, startScript+" "+strconv.Itoa(port)))
	_, err = util.RunLocalCmd("su",
		[]string{consts.MysqlAaccount, "-c", startScript + " " + strconv.Itoa(port) + " 2>/dev/null"},
		"", nil, 10*time.Minute)
	if err != nil {
		return err
	}
	addr := fmt.Sprintf("%s:%d", job.params.IP, port)
	cli, err := myredis.NewRedisClientWithTimeout(addr, job.proxyPassword, 0,
		consts.TendisTypeRedisInstance, 10*time.Second)
	if err != nil {
		return err
	}
	defer cli.Close()
	job.runtime.Logger.Info("start proxy (%s:%d) success", job.params.IP, port)
	return nil
}

// Retry times
func (job *PredixyAddModulesCmds) Retry() uint {
	return 2
}

// Rollback rollback
func (job *PredixyAddModulesCmds) Rollback() error {
	return nil
}
