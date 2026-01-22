package atomsys

import (
	"bufio"
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"os"
	"time"

	"github.com/go-playground/validator/v10"
)

// ReverseAPIParams
type ReverseAPIParams struct {
	NginxAddrs []string `json:"nginx_addrs"`
}

// ChangePwd atomjob
type ReverseAPIConfig struct {
	runtime *jobruntime.JobGenericRuntime
	params  ReverseAPIParams

	errChan chan error
}

// NewRestartExporter
func NewReverseAPIConfig() jobruntime.JobRunner {
	return &ReverseAPIConfig{}
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*ReverseAPIConfig)(nil)

// Init 初始化
func (job *ReverseAPIConfig) Init(m *jobruntime.JobGenericRuntime) error {
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
func (job *ReverseAPIConfig) Name() string {
	return "redis_reverse_config"
}

// Run 执行
func (job *ReverseAPIConfig) Run() (err error) {
	reverseConfig := common.GetResrveAPIConfig()
	// 以追加模式打开文件，如果文件不存在则创建
	file, err := os.OpenFile(reverseConfig, os.O_TRUNC|os.O_CREATE|os.O_WRONLY, 0755)
	if err != nil {
		job.runtime.Logger.Error("open file %s failed: %+v", reverseConfig, err)
		return err
	}
	defer file.Close()

	if _, err := util.RunBashCmd(fmt.Sprintf("chown -R mysql:mysql %s", reverseConfig), "",
		nil, 10*time.Second); err != nil {
		job.runtime.Logger.Warn("chown %s 2 mysql failed: %+v", reverseConfig, err)
	}

	// 创建带缓冲的写入器
	writer := bufio.NewWriter(file)
	// 写入每个字符串
	for _, str := range job.params.NginxAddrs {
		_, err := writer.WriteString(str + "\n")
		job.runtime.Logger.Debug("write %s 2 file %s", str, reverseConfig)
		if err != nil {
			job.runtime.Logger.Error("write 2 file %s failed: %+v", reverseConfig, err)
			return err
		}
	}

	// 刷新缓冲区
	err = writer.Flush()
	if err != nil {
		job.runtime.Logger.Error("flush file %s failed: %+v", reverseConfig, err)
		return err
	}

	job.runtime.Logger.Info("job done.^_^")
	return nil
}

// Retry times
func (job *ReverseAPIConfig) Retry() uint {
	return 2
}

// Rollback rollback
func (job *ReverseAPIConfig) Rollback() error {
	return nil
}
