package atomredis

import (
	"encoding/json"
	"fmt"
	"os"

	"strconv"
	"sync"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/datastructure"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
)

// RedisDataStructureParams redis 数据构造参数
type RedisDataStructureParams struct {
	SourceIP          string                     `json:"source_ip" validate:"required"`
	SourcePorts       []int                      `json:"source_ports" validate:"required"`
	NeWTempIP         string                     `json:"new_temp_ip" validate:"required"`
	NewTempPorts      []int                      `json:"new_temp_ports" validate:"required" `
	RecoveryTimePoint string                     `json:"recovery_time_point" validate:"required"`
	IsIncludeSlave    bool                       `json:"is_include_slave" `
	TendisType        string                     `json:"tendis_type" validate:"required"`
	DestDir           string                     `json:"dest_dir"`                           // 备份下载/存放目录
	FullFileList      []datastructure.FileDetail `json:"full_file_list" validate:"required"` // 全备文件列表
	BinlogFileList    []datastructure.FileDetail `json:"binlog_file_list" `                  // binlog文件列表
}

// RedisDataStructure redis 数据构造
type RedisDataStructure struct {
	runtime    *jobruntime.JobGenericRuntime
	params     RedisDataStructureParams
	RecoverDir string
	password   string
	TendisType string `json:"tendis_type"`
}

// 无实际作用,仅确保实现了 taskruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisDataStructure)(nil)

// NewRedisDataStructure new
func NewRedisDataStructure() jobruntime.JobRunner {
	return &RedisDataStructure{}
}

// Init 初始化
func (task *RedisDataStructure) Init(m *jobruntime.JobGenericRuntime) error {
	task.runtime = m

	err := json.Unmarshal([]byte(task.runtime.PayloadDecoded), &task.params)
	if err != nil {
		task.runtime.Logger.Error(fmt.Sprintf("json.Unmarshal failed,err:%+v", err))
		return err
	}
	// 参数有效性检查
	validate := validator.New()
	err = validate.Struct(task.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			task.runtime.Logger.Error("RedisDataStructure Init params validate failed,err:%v,params:%+v",
				err, task.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			task.runtime.Logger.Error("RedisDataStructure Init params validate failed,err:%v,params:%+v",
				err, task.params)
			return err
		}
	}
	// 检查传入的端口不能为空
	if len(task.params.SourcePorts) == 0 || len(task.params.NewTempPorts) == 0 {
		err = fmt.Errorf("RedisDataStructure SourcePorts(%d) or NewTempPorts(%d) =0 , is invalid ",
			task.params.SourcePorts, task.params.NewTempPorts)
		task.runtime.Logger.Error(err.Error())
		return err
	}

	// 传入的源端口数应该等于临时节点端口数
	if len(task.params.SourcePorts) != len(task.params.NewTempPorts) {
		err = fmt.Errorf("RedisDataStructure SourcePorts(%d) != NewTempPorts(%d) , is invalid ",
			task.params.SourcePorts, task.params.NewTempPorts)
		task.runtime.Logger.Error(err.Error())
		return err
	}

	return nil
}

// Name 原子任务名
func (task *RedisDataStructure) Name() string {
	return "redis_data_structure"
}

// Retry times
func (task *RedisDataStructure) Retry() uint {
	return 2
}

// Rollback rollback
func (task *RedisDataStructure) Rollback() error {
	return nil

}

// Run 执行
// NOCC:golint/fnsize(设计如此)
func (task *RedisDataStructure) Run() (err error) {

	// 检查构造目录是否存在
	task.RecoverDir = task.params.DestDir
	err = task.CheckRecoverDir()
	if err != nil {
		return err
	}

	task.runtime.Logger.Info(task.params.RecoveryTimePoint)
	// 构造任务初始化
	recoverTasks := make([]*datastructure.TendisInsRecoverTask, 0, len(task.params.SourcePorts))
	for idx, sourceRort := range task.params.SourcePorts {
		newTmpPort := task.params.NewTempPorts[idx]
		task.TendisType = task.params.TendisType
		task.password = ""
		// 数据构造时从本地获取密码信息
		task.password, err = myredis.GetRedisPasswdFromConfFile(newTmpPort)
		if err != nil {
			return err
		}

		redisAddr := fmt.Sprintf("%s:%s", task.params.NeWTempIP, strconv.Itoa(task.params.NewTempPorts[0]))
		// 验证节点是否可连接
		redisCli, err := myredis.NewRedisClient(redisAddr, task.password, 0, consts.TendisTypeRedisInstance)
		if err != nil {
			return err
		}
		defer redisCli.Close()
		// 获取节点类型
		task.TendisType, err = redisCli.GetTendisType()
		if err != nil {
			err = fmt.Errorf("GetTendisType Err:%v", err)
			task.runtime.Logger.Error(err.Error())
			return err
		}
		task.runtime.Logger.Info("TendisType:%s", task.TendisType)

		// 构造任务
		recoverTask, err := datastructure.NewTendisInsRecoverTask(task.params.SourceIP, sourceRort,
			task.params.NeWTempIP, newTmpPort, task.password,
			task.params.RecoveryTimePoint, task.RecoverDir, task.TendisType,
			task.params.IsIncludeSlave, task.runtime,
			task.params.FullFileList, task.params.BinlogFileList)
		if err != nil {
			return err
		}
		// 获取链接
		err = recoverTask.GetRedisCli()
		if err != nil {
			return err
		}

		recoverTasks = append(recoverTasks, recoverTask)

	}

	wg := sync.WaitGroup{}
	genChan := make(chan *datastructure.TendisInsRecoverTask)
	limit := 3 // 并发度
	for worker := 0; worker < limit; worker++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for taskItem := range genChan {
				// 执行回档任务
				taskItem.Run()
			}
		}()
	}
	go func() {
		// 关闭genChan,以便让所有goroutine退出
		defer close(genChan)
		for _, task := range recoverTasks {
			recoverItem := task
			genChan <- recoverItem
		}
	}()
	wg.Wait()
	for _, task := range recoverTasks {
		recoverItem := task
		if recoverItem.Err != nil {
			return recoverItem.Err
		}
	}

	return nil
}

// CheckRecoverDir 数据构造本地数据目录
func (task *RedisDataStructure) CheckRecoverDir() (err error) {

	// 检查构造目录是否存在
	_, err = os.Stat(task.RecoverDir)
	if err != nil && os.IsNotExist(err) {
		err = fmt.Errorf("目录:%s不存在,err:%v", task.RecoverDir, err)
		task.runtime.Logger.Error(err.Error())
		return err
	} else if err != nil {
		err = fmt.Errorf("访问目录:%s 失败,err:%v", task.RecoverDir, err)
		task.runtime.Logger.Error(err.Error())
		return err

	}
	task.runtime.Logger.Info("CheckRecoverDir:%s success", task.RecoverDir)
	return nil
}
