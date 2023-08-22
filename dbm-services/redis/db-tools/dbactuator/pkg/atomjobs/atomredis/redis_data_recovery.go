package atomredis

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/backupsys"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"

	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// RedisDataRecoverParams redis 数据构造参数
type RedisDataRecoverParams struct {
	SourceIP          string                `json:"source_ip" validate:"required"`
	SourcePorts       []int                 `json:"source_ports" validate:"required"`
	NeWTempIP         string                `json:"new_temp_ip" validate:"required"`
	NewTempPorts      []int                 `json:"new_temp_ports" validate:"required" `
	RecoveryTimePoint string                `json:"recovery_time_point" validate:"required"`
	User              string                `json:"user" validate:"required"`
	Password          string                `json:"password" validate:"required"`
	IsIncludeSlave    bool                  `json:"is_include_slave" `
	IsPrecheck        bool                  `json:"is_precheck" `
	TendisType        string                `json:"tendis_type" validate:"required"`
	BaseInfo          backupsys.IBSBaseInfo `json:"base_info"`
}

// RedisDataRecover redis 数据构造
type RedisDataRecover struct {
	runtime     *jobruntime.JobGenericRuntime
	params      RedisDataRecoverParams
	query       backupsys.QueryReq
	RecoverDir  string
	successPort []int
	failPort    []int
	fileNames   []string
	password    string
	taskidList  string
	BackupSize  uint64
	TendisType  string `json:"tendis_type"`
}

// 无实际作用,仅确保实现了 taskruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisDataRecover)(nil)

// NewRedisDataRecover new
func NewRedisDataRecover() jobruntime.JobRunner {
	return &RedisDataRecover{}
}

// Init 初始化
func (task *RedisDataRecover) Init(m *jobruntime.JobGenericRuntime) error {
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
			task.runtime.Logger.Error("RedisDataRecover Init params validate failed,err:%v,params:%+v",
				err, task.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			task.runtime.Logger.Error("RedisDataRecover Init params validate failed,err:%v,params:%+v",
				err, task.params)
			return err
		}
	}
	// 检查传入的端口不能为空
	if len(task.params.SourcePorts) == 0 || len(task.params.NewTempPorts) == 0 {
		err = fmt.Errorf("RedisDataRecover SourcePorts(%d) or NewTempPorts(%d) =0 , is invalid ",
			task.params.SourcePorts, task.params.NewTempPorts)
		task.runtime.Logger.Error(err.Error())
		return err
	}

	//传入的源端口数应该等于临时节点端口数
	if len(task.params.SourcePorts) != len(task.params.NewTempPorts) {
		err = fmt.Errorf("RedisDataRecover SourcePorts(%d) != NewTempPorts(%d) , is invalid ",
			task.params.SourcePorts, task.params.NewTempPorts)
		task.runtime.Logger.Error(err.Error())
		return err
	}
	// 设置回档用户和密码
	backupsys.SetUserPassword(task.params.User, task.params.Password)
	// 设置备份系统信息
	backupsys.SetIBSBaseInfo(task.params.BaseInfo.Url, task.params.BaseInfo.SysID, task.params.BaseInfo.Key)
	return nil
}

// Name 原子任务名
func (task *RedisDataRecover) Name() string {
	return "redis_data_structure"
}

// Retry times
func (task *RedisDataRecover) Retry() uint {
	return 2
}

// Rollback rollback
func (task *RedisDataRecover) Rollback() error {
	return nil

}

// Run 执行
// NOCC:golint/fnsize(设计如此)
func (task *RedisDataRecover) Run() (err error) {
	// 构造目录初始化
	recoverDir := filepath.Join(consts.GetRedisBackupDir(), "dbbak/recover_redis")
	task.RecoverDir = recoverDir
	err = task.CheckRecoverDir()
	if err != nil {
		return err
	}

	task.runtime.Logger.Info(task.params.RecoveryTimePoint)
	// 恢复任务初始化
	recoverTasks := make([]*backupsys.RedisInsRecoverTask, 0, len(task.params.SourcePorts))
	for idx, sourceRort := range task.params.SourcePorts {
		newTmpPort := task.params.NewTempPorts[idx]
		task.TendisType = task.params.TendisType
		// 前置检查备份信息时，因为还没安装节点，所以password信息还拿不到
		task.password = ""
		// 提前检查备份信息
		if task.params.IsPrecheck {
			// 恢复任务
			recoverTask, err := backupsys.NewRedisInsRecoverTask(task.params.SourceIP, sourceRort,
				task.params.NeWTempIP, newTmpPort, task.password,
				task.params.RecoveryTimePoint, recoverDir, task.TendisType,
				task.params.IsIncludeSlave, task.params.IsPrecheck, task.runtime)
			if err != nil {
				return err
			}
			recoverTasks = append(recoverTasks, recoverTask)

		} else {
			// 数据构造时从本地获取密码信息
			task.password, err = myredis.GetPasswordFromLocalConfFile(newTmpPort)
			if err != nil {
				return err
			}

			// 获取回档类型
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

			// 恢复任务
			recoverTask, err := backupsys.NewRedisInsRecoverTask(task.params.SourceIP, sourceRort,
				task.params.NeWTempIP, newTmpPort, task.password,
				task.params.RecoveryTimePoint, recoverDir, task.TendisType,
				task.params.IsIncludeSlave, task.params.IsPrecheck, task.runtime)
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

	}
	// 如果是构造数据时才停dbmon,前置检查备份信息时，还没安装dbmon
	if !task.params.IsPrecheck {
		// 停BkDbmon
		err = task.stopBkDbmon()
		if err != nil {
			return err
		}
	}

	wg := sync.WaitGroup{}
	genChan := make(chan *backupsys.RedisInsRecoverTask)
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
	// 如果是构造数据时才拉dbmon,前置检查备份信息时，还没dbmon相关文件
	if !task.params.IsPrecheck {
		// 	拉起BkDbmon
		err = task.startBkDbmon()
		if err != nil {
			return err
		}

	}

	return nil
}

// CheckRecoverDir 数据构造本地数据目录
func (task *RedisDataRecover) CheckRecoverDir() (err error) {

	// 检查构造目录是否存在
	_, err = os.Stat(task.RecoverDir)
	if err != nil && os.IsNotExist(err) {
		mkCmd := fmt.Sprintf("mkdir -p %s ", task.RecoverDir)
		_, err = util.RunLocalCmd("bash", []string{"-c", mkCmd}, "", nil, 10*time.Minute)
		if err != nil {
			err = fmt.Errorf("创建目录:%s失败,err:%v", task.RecoverDir, err)
			task.runtime.Logger.Error(err.Error())
			return err
		}
		util.LocalDirChownMysql(task.RecoverDir)
	} else if err != nil {
		err = fmt.Errorf("访问目录:%s 失败,err:%v", task.RecoverDir, err)
		task.runtime.Logger.Error(err.Error())
		return err

	}
	task.runtime.Logger.Info("CheckRecoverDir:%s success", task.RecoverDir)
	return nil
}

// // StopBkDbmon 停 bk-dbmon
func (task *RedisDataRecover) stopBkDbmon() (err error) {

	task.runtime.Logger.Info("stop dbmon start")
	// 调用脚本，路径是固定的
	stopScript := filepath.Join(consts.BkDbmonPath, "stop.sh")
	if !util.FileExists(stopScript) {
		err = fmt.Errorf("%s stop.sh not exists", consts.BkDbmonPath)
		task.runtime.Logger.Error(err.Error())
		return err

	}

	stopCmd := fmt.Sprintf("su %s -c '%s'", consts.MysqlAaccount, "sh "+stopScript)
	task.runtime.Logger.Info(stopCmd)
	_, err = util.RunLocalCmd("su", []string{consts.MysqlAaccount, "-c", "sh " + stopScript},
		"", nil, 1*time.Minute)
	if err != nil {
		err = fmt.Errorf("执行关闭dbmon命令:%s失败:%v", stopCmd, err)
		task.runtime.Logger.Error(err.Error())
		return err
	}
	task.runtime.Logger.Info("stop dbmon success")
	return nil
}

// startBkDbmon 拉起 bk-dbmon
func (task *RedisDataRecover) startBkDbmon() (err error) {
	task.runtime.Logger.Info("start dbmon ...")
	startScript := filepath.Join(consts.BkDbmonPath, "start.sh")
	if !util.FileExists(startScript) {
		err = fmt.Errorf("%s start.sh not exists", consts.BkDbmonPath)
		task.runtime.Logger.Error(err.Error())
		return err
	}
	//用mysql权限
	startCmd := fmt.Sprintf("su %s -c 'nohup %s &'", consts.MysqlAaccount, "sh "+startScript)
	task.runtime.Logger.Info(startCmd)
	_, err = util.RunLocalCmd("su", []string{consts.MysqlAaccount, "-c", "nohup sh " + startScript + " &"},
		"", nil, 1*time.Minute)
	if err != nil {
		err = fmt.Errorf("执行启动dbmon命令:%s失败:%v", startCmd, err)
		task.runtime.Logger.Error(err.Error())
		return err
	}
	task.runtime.Logger.Info("start dbmon success")
	return nil
}
