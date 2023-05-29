package atomsys

import (
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// GetRequestParams get request参数
type GetRequestParams struct {
	DbToolsPkg    common.DbToolsMediaPkg `json:"dbtoolspkg"`
	IP            string                 `json:"ip" validate:"required"`
	Ports         []int                  `json:"ports" validate:"required"`
	MonitorTimeMs int                    `json:"monitor_time_ms" validate:"required" `
	IgnoreKeys    []string               `json:"ignore_keys"`
	Ignore        bool                   `json:"ignore"` // 是否忽略错误
}

// RedisCapturer get request 结构体
type RedisCapturer struct {
	runtime     *jobruntime.JobGenericRuntime
	params      *GetRequestParams
	Device      string
	monitorTool string
	errChan     chan error
}

// NewRedisCapturer 创建一个get request对象
func NewRedisCapturer() jobruntime.JobRunner {
	return &RedisCapturer{}
}

// Init 初始化
func (job *RedisCapturer) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisCapturer Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisCapturer Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	// 6379<= start_port <= 55535
	ports := job.params.Ports
	for _, p := range ports {
		if p > 55535 || p < 6379 {
			err = fmt.Errorf("RedisCapturer port[%d] must range [6379,5535]", p)
			job.runtime.Logger.Error(err.Error())
			return err
		}

	}
	job.errChan = make(chan error, len(ports))
	job.monitorTool = consts.MyRedisCaptureBin
	job.Device, err = util.GetIpv4InterfaceName(job.params.IP)
	if err != nil {
		return err
	}

	err = job.params.DbToolsPkg.Install()
	if err != nil {
		return err
	}
	return nil
}

// Run 运行监听请求任务
func (job *RedisCapturer) Run() (err error) {
	ports := job.params.Ports

	_, err = os.Stat(job.monitorTool)
	if err != nil && os.IsNotExist(err) {
		return fmt.Errorf("获取redis-capturer失败,请检查是否下发成功:err:%v", err)
	}

	wg := sync.WaitGroup{}
	for _, port := range ports {
		wg.Add(1)
		go func(port int) {
			defer wg.Done()
			job.Monitor(port)
		}(port)
	}
	wg.Wait()
	close(job.errChan)

	errMsg := ""
	for err := range job.errChan {
		errMsg = fmt.Sprintf("%s\n%s", errMsg, err.Error())
	}
	if errMsg != "" {
		// 如果忽略错误，则这里只报warning
		if job.params.Ignore {
			job.runtime.Logger.Warn(errMsg)
			return nil
		}
		return fmt.Errorf(errMsg)
	}

	return nil
}

// Monitor 监听请求
func (job *RedisCapturer) Monitor(port int) {
	job.runtime.Logger.Info("monitor port[%d] begin..", port)
	defer job.runtime.Logger.Info("monitor port[%d] end..", port)
	var err error
	running, err := job.IsRedisRunning(port)
	if err != nil || !running {
		job.errChan <- fmt.Errorf("port[%d] is not running", port)
		return
	}

	nowstr := time.Now().Local().Format("150405")
	capturelog := fmt.Sprintf("capture_%s_%d_%s.log", job.params.IP, port, nowstr)
	monitorCmd := fmt.Sprintf("%s --device=%s --ip=%s --port=%d --timeout=%d --log-file=%s", job.monitorTool,
		job.Device, job.params.IP, port, job.params.MonitorTimeMs/1000, capturelog)
	if len(job.params.IgnoreKeys) != 0 {
		ignoreStr := strings.Join(job.params.IgnoreKeys, "|")
		monitorCmd = fmt.Sprintf("%s |  grep -i -v -E '%s' || true", monitorCmd, ignoreStr)
	}
	job.runtime.Logger.Info("monitor cmd is [%s]", monitorCmd)
	// password, err := myredis.GetPasswordFromLocalConfFile(port)
	// if err != nil {
	// 	job.errChan <- err
	// 	return
	// }
	// monitorCmd := fmt.Sprintf("timeout %d %s --no-auth-warning -a %s -h %s -p %d monitor",
	// 	job.params.MonitorTimeMs/1000, consts.RedisCliBin, password, job.params.IP, port)
	// logCmd := fmt.Sprintf("timeout %d %s --no-auth-warning -a %s -h %s -p %d monitor",
	// 	job.params.MonitorTimeMs/1000, consts.RedisCliBin, "xxxxxx", job.params.IP, port)
	// if len(job.params.IgnoreKeys) != 0 {
	// 	ignoreStr := strings.Join(job.params.IgnoreKeys, "|")
	// 	monitorCmd = fmt.Sprintf("%s |  grep -i -v -E '%s' ", monitorCmd, ignoreStr)
	// 	logCmd = fmt.Sprintf("%s |  grep -i -v -E '%s' ", logCmd, ignoreStr)
	// }
	// monitorCmd += " || true"
	// logCmd += " || true"
	// job.runtime.Logger.Info("monitor cmd is [%s]", logCmd)

	cmdRet, err := util.RunLocalCmd("bash", []string{"-c", monitorCmd}, "", nil, 10*time.Minute)
	if err != nil {
		if err.Error() == "RunLocalCmd cmd wait fail,err:exit status 1" {
			return
		}
		job.errChan <- err
		return
	}
	if cmdRet != "" {
		// 只取前30条
		cmdText := ""
		num := 0
		for _, cmdLine := range strings.Split(cmdRet, "\n") {
			cmdText = fmt.Sprintf("%s\n%s", cmdText, cmdLine)
			num++
			if num >= 30 {
				break
			}
		}
		err = fmt.Errorf("check request failed. because have qps: %s", cmdText)
		job.errChan <- err
		return
	}
}

// IsRedisRunning 检查实例是否在运行。 下架流程中，实例没有运行到底算不算异常呢？
func (job *RedisCapturer) IsRedisRunning(port int) (installed bool, err error) {
	time.Sleep(10 * time.Second)
	portIsUse, err := util.CheckPortIsInUse(job.params.IP, strconv.Itoa(port))
	return portIsUse, err
}

// Name 原子任务名
func (job *RedisCapturer) Name() string {
	return "redis_capturer"
}

// Retry times
func (job *RedisCapturer) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisCapturer) Rollback() error {
	return nil
}
