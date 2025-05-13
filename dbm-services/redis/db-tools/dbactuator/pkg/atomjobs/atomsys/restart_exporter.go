package atomsys

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"time"

	"github.com/go-playground/validator/v10"
)

// ExporterParams
type ExporterParams struct {
	IP           string         `json:"ip" validate:"required"`
	MetaRole     string         `json:"role" validate:"required"`
	Ports        []int          `json:"ports"`
	Password     string         `json:"password"`
	ImmuteDomain string         `json:"cluster_domain"`
	PasswordMap  map[int]string `json:"password_map"`
	ClusterType  string         `json:"cluster_type"`
}

// ChangePwd atomjob
type RestartExporter struct {
	runtime *jobruntime.JobGenericRuntime
	params  ExporterParams

	errChan chan error
}

// NewRestartExporter
func NewRestartExporter() jobruntime.JobRunner {
	return &RestartExporter{}
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RestartExporter)(nil)

// Init 初始化
func (job *RestartExporter) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("ChangePwd Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("ChangePwd Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	return nil
}

// Name 原子任务名
func (job *RestartExporter) Name() string {
	return "restart_exporter"
}

// Run 执行
func (job *RestartExporter) Run() (err error) {
	exporterProcessName := "dbm_redis_exporter"
	if job.params.MetaRole == consts.MetaRolePredixy {
		exporterProcessName = "dbm_predixy_exporter"
	} else if job.params.MetaRole == consts.MetaRoleTwemproxy {
		exporterProcessName = "dbm_twemproxy_exporter"
	}

	if job.params.ClusterType == consts.TendisTypeRedisInstance {
		for port, password := range job.params.PasswordMap {
			job.runtime.Logger.Info("regenerate exporter config 4 instance :%d", port)
			// del first .
			common.DeleteExporterConfigFile(port)
			// re generate it .
			common.CreateLocalExporterConfigFile(job.params.IP, port, job.params.MetaRole, password)
		}
	} else {
		// send kill exporter
		for _, port := range job.params.Ports {
			job.runtime.Logger.Info("regenerate exporter config 4 instance :%d", port)
			// del first .
			common.DeleteExporterConfigFile(port)
			// re generate it .
			common.CreateLocalExporterConfigFile(job.params.IP, port, job.params.MetaRole, job.params.Password)
		}
	}

	// kill all exporter .
	job.runtime.Logger.Info("try restart exporter by running killall exporter.")
	if _, err := util.RunBashCmd(fmt.Sprintf("killall -9 %s", exporterProcessName), "",
		nil, 10*time.Second); err != nil {
		job.runtime.Logger.Warn("kill all %s maybe failed : %+v", exporterProcessName, err)
	}

	job.runtime.Logger.Info("try reload bkmonitorbeat;bkunifylogbeat plugin...")
	if _, err := util.RunBashCmd("/usr/local/gse2_bkte/plugins/bin/reload.sh bkmonitorbeat",
		"", nil, 10*time.Second); err != nil {
		job.runtime.Logger.Warn("reload bkmonitorbeat maybe failed : %+v", err)
	}

	if _, err := util.RunBashCmd("/usr/local/gse2_bkte/plugins/bin/reload.sh bkunifylogbeat",
		"", nil, 10*time.Second); err != nil {
		job.runtime.Logger.Warn("reload bkunifylogbeat maybe failed : %+v", err)
	}
	job.runtime.Logger.Info("job done.^_^")
	return nil
}

// Retry times
func (job *RestartExporter) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RestartExporter) Rollback() error {
	return nil
}
