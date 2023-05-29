package atomproxy

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// PredixyConfServersRewriteParams params
type PredixyConfServersRewriteParams struct {
	PredixyIP       string   `json:"predixy_ip" validate:"required"`
	PredixyPort     int      `json:"predixy_port" validate:"required"`
	ToRemoveServers []string `json:"to_remove_servers"` // 需要移除的servers,如: ["a.a.a.a:30000","b.b.b.b:30000"]
}

// Addr addr
func (p PredixyConfServersRewriteParams) Addr() string {
	return fmt.Sprintf("%s:%d", p.PredixyIP, p.PredixyPort)
}

// PredixyConfServersRewrite predixy config servers rewrite
type PredixyConfServersRewrite struct {
	runtime *jobruntime.JobGenericRuntime
	params  PredixyConfServersRewriteParams
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*PredixyConfServersRewrite)(nil)

// NewPredixyConfServersRewrite new
func NewPredixyConfServersRewrite() jobruntime.JobRunner {
	return &PredixyConfServersRewrite{}
}

// Init prepare run env
func (job *PredixyConfServersRewrite) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("PredixyConfServersRewrite Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("PredixyConfServersRewrite Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	return nil
}

// Name job name
func (job *PredixyConfServersRewrite) Name() string {
	return "predixy_config_servers_rewrite"
}

// Run Command Run
func (job *PredixyConfServersRewrite) Run() (err error) {
	var confFile, password string
	var sedCmd string
	confFile, err = myredis.GetPredixyLocalConfFile(job.params.PredixyPort)
	if err != nil {
		return nil
	}
	password, err = myredis.GetProxyPasswdFromConfFlie(job.params.PredixyPort, consts.MetaRolePredixy)
	if err != nil {
		return nil
	}
	// 先sleep 100s,便于proxy将一些 redis node标记为fail
	job.runtime.Logger.Error("sleep 100s for proxy mark certain Redis nodes as failed")
	time.Sleep(100 * time.Second)
	// 获取 predixy running servers信息
	infoServers, err := myredis.GetPredixyInfoServersDecoded(job.params.PredixyIP, job.params.PredixyPort, password)
	if err != nil {
		return nil
	}
	confDataBytes, err := os.ReadFile(confFile)
	if err != nil {
		err = fmt.Errorf("read file:%s failed,err:%v", confFile, err)
		mylog.Logger.Error(err.Error())
		return
	}
	confData := string(confDataBytes)
	toRemoveMap := make(map[string]bool)
	for _, addr := range job.params.ToRemoveServers {
		toRemoveMap[addr] = true
	}
	for _, tmp := range infoServers {
		server := tmp
		sedCmd = ""
		if server.CurrentIsFail == 1 && strings.Contains(confData, server.Server) {
			// 已经连接失败的,且配置文件中存在的,需要移除
			sedCmd = fmt.Sprintf(`sed -i -e '/%s/d' %s`, server.Server, confFile)
		} else if server.CurrentIsFail == 0 && !toRemoveMap[server.Server] && !strings.Contains(confData, server.Server) {
			// 依然是running的,配置文件中不存在的,需要添加
			sedCmd = fmt.Sprintf(`sed -i -e '/Servers[[:space:]]*{/a\\    + %s' %s`, server.Server, confFile)
		}
		if sedCmd == "" {
			continue
		}
		mylog.Logger.Info("PredixyConfServersRewrite Run sedCmd:%s", sedCmd)
		_, err = util.RunBashCmd(sedCmd, "", nil, 10*time.Second)
		if err != nil {
			return err
		}
	}

	confDataBytes, _ = os.ReadFile(confFile)
	confData = string(confDataBytes)
	for removeSvr, _ := range toRemoveMap {
		if strings.Contains(confData, removeSvr) {
			sedCmd = fmt.Sprintf(`sed -i -e '/%s/d' %s`, removeSvr, confFile)
			mylog.Logger.Info("PredixyConfServersRewrite Run sedCmd:%s", sedCmd)
			_, err = util.RunBashCmd(sedCmd, "", nil, 10*time.Second)
			if err != nil {
				return err
			}
		}
	}
	mylog.Logger.Info("PredixyConfServersRewrite Run success")
	return
}

// Retry times
func (job *PredixyConfServersRewrite) Retry() uint {
	return 2
}

// Rollback rollback
func (job *PredixyConfServersRewrite) Rollback() error {
	return nil
}
