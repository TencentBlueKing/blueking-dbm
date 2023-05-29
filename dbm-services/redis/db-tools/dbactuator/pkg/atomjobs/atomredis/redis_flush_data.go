package atomredis

import (
	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"sync"

	"github.com/go-playground/validator/v10"
)

// RedisFlushDataParams 清档参数
type RedisFlushDataParams struct {
	IP         string `json:"ip" validate:"required"`
	DbType     string `json:"db_type" validate:"required"`
	Ports      []int  `json:"ports" validate:"required"`
	Password   string `json:"password" validate:"required"`
	IsForce    bool   `json:"is_force"` // 这里应该是必传的，但是如果是false会报错
	DBList     []int  `json:"db_list"`
	IsFlushAll bool   `json:"is_flush_all"`
	Debug      bool   `json:"debug"`
}

// RedisFlushData atomjob
type RedisFlushData struct {
	runtime     *jobruntime.JobGenericRuntime
	params      RedisFlushDataParams
	RedisBinDir string // /usr/local/redis
	DataBases   int

	errChan chan error
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisFlushData)(nil)

// NewRedisFlushData new
func NewRedisFlushData() jobruntime.JobRunner {
	return &RedisFlushData{}
}

// Init 初始化
func (job *RedisFlushData) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisFlushData Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisFlushData Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	return nil
}

// InitRealDataDir 初始化参数
func (job *RedisFlushData) InitRealDataDir() {
	redisSoftLink := filepath.Join(consts.UsrLocal, "redis")
	job.RedisBinDir = filepath.Join(redisSoftLink, "bin")
	job.runtime.Logger.Info("GetRedisBinDir success,binDir:%s", job.RedisBinDir)
	job.errChan = make(chan error, len(job.params.Ports))

	//	获取DataBases

}

// Name 原子任务名
func (job *RedisFlushData) Name() string {
	return "redis_flush_data"
}

// Run 执行
func (job *RedisFlushData) Run() (err error) {
	job.InitRealDataDir()
	err = job.CheckParams()
	if err != nil {
		return
	}
	ports := job.params.Ports

	wg := sync.WaitGroup{}
	for _, port := range ports {
		wg.Add(1)
		go func(port int) {
			defer wg.Done()
			job.FlushData(port)
		}(port)
	}
	wg.Wait()
	close(job.errChan)

	errMsg := ""
	for err := range job.errChan {
		errMsg = fmt.Sprintf("%s\n%s", errMsg, err.Error())
	}
	if errMsg != "" {
		return fmt.Errorf(errMsg)
	}

	return nil
}

// FlushData 执行清档
func (job *RedisFlushData) FlushData(port int) {
	/*
		根据force检查请求
		根据db_type来执行不同的清档命令
		检查清档结果。用randomkey 命令来判断是否清理完成
	*/
	var err error

	if job.params.IsFlushAll {
		err = job.FlushAll(port)
	} else {
		err = job.FlushDB(port)
	}
	if err != nil {
		job.errChan <- err
		return
	}

	return
}

// FlushDB 清理指定DB
func (job *RedisFlushData) FlushDB(port int) error {
	job.runtime.Logger.Info("flush db port[%d] doing.......", port)
	params := job.params

	insAddr := fmt.Sprintf("%s:%d", job.params.IP, port)
	redisClient, err := myredis.NewRedisClient(insAddr, job.params.Password, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		return err
	}
	defer redisClient.Close()

	for _, db := range params.DBList {
		result, err := redisClient.DoCommand([]string{consts.FlushDBRename}, db)
		if err != nil {
			return err
		}

		if !strings.Contains(result.(string), "OK") {
			err = fmt.Errorf("flush db port[%d] db[%d] error [%+v]", port, db, result)
			return err
		}

		if err = job.CheckFlushResult(port, db); err != nil {
			return err
		}

		job.runtime.Logger.Info("flush db port[%d] db[%d] success", port, db)
	}
	// TODO 这里是不是要处理一下没有rename前的命令？
	return nil
}

// FlushAll 清理所有数据
func (job *RedisFlushData) FlushAll(port int) error {
	job.runtime.Logger.Info("flush all port[%d] doing.......", port)
	var cmd []string
	var err error
	insAddr := fmt.Sprintf("%s:%d", job.params.IP, port)
	redisClient, err := myredis.NewRedisClient(insAddr, job.params.Password, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		return err
	}
	defer redisClient.Close()

	params := job.params
	if consts.IsTendisSSDInstanceDbType(params.DbType) {
		cmd = []string{consts.SSDFlushAllRename}
	} else if consts.IsTendisplusInstanceDbType(params.DbType) || consts.IsRedisInstanceDbType(params.DbType) {
		cmd = []string{consts.CacheFlushAllRename}
	} else {
		err = fmt.Errorf("unknown dbType(%s)", params.DbType)
		return err
	}

	result, err := redisClient.DoCommand(cmd, 0)
	if err != nil {
		return err
	}

	if !strings.Contains(result.(string), "OK") {
		err = fmt.Errorf("flush all port[%d] error [%+v]", port, result)
		return err
	}

	if err = job.CheckFlushResult(port, 0); err != nil {
		return err
	}

	job.runtime.Logger.Info("flush all port[%d] success", port)
	return nil
}

// CheckFlushResult 检查清理结果
func (job *RedisFlushData) CheckFlushResult(port, db int) error {
	job.runtime.Logger.Info("check flush result port[%d] db[%d] doing.......", port, db)
	params := job.params
	var err error

	if !params.IsForce {
		// 强制清档不需要做这不检查了，因为可能会存在写入
		if consts.IsAllowRandomkey(params.DbType) {
			if err = job.RandomKey(port, db); err != nil {
				return err
			}
		} else {
			if err = job.Keys(port, db); err != nil {
				return err
			}
		}
	}
	job.runtime.Logger.Info("check flush result port[%d] db[%d] done.......", port, db)
	return nil
}

// Keys 检查tendisplus是否清理完成
func (job *RedisFlushData) Keys(port, db int) error {
	job.runtime.Logger.Info("exec keys port[%d] db[%d] doing.......", port, db)

	insAddr := fmt.Sprintf("%s:%d", job.params.IP, port)
	redisClient, err := myredis.NewRedisClient(insAddr, job.params.Password, db, consts.TendisTypeRedisInstance)
	if err != nil {
		return err
	}
	defer redisClient.Close()

	cmd := []string{consts.KeysRename, "*"}
	result, err := redisClient.DoCommand(cmd, db)
	if err != nil {
		return err
	}

	flushSucc := false
	switch result.(type) {
	case string:
		if result == "" {
			flushSucc = true
		}
	case []interface{}:
		if len(result.([]interface{})) == 0 {
			flushSucc = true
		}
	}
	if !flushSucc {
		return fmt.Errorf("flush port[%d] db[%d] failed pleach check key[%s]", port, db, result)
	}

	job.runtime.Logger.Info("exec keys port[%d] db[%d] done.......", port, db)
	return nil
}

// RandomKey 随机获取key,检查是否清理完成。 tendisplus不支持
func (job *RedisFlushData) RandomKey(port, db int) error {
	job.runtime.Logger.Info("exec randomkey port[%d] db[%d] doing.......", port, db)

	insAddr := fmt.Sprintf("%s:%d", job.params.IP, port)
	redisClient, err := myredis.NewRedisClient(insAddr, job.params.Password, db, consts.TendisTypeRedisInstance)
	if err != nil {
		return err
	}
	defer redisClient.Close()

	key, err := redisClient.Randomkey()
	if err != nil {
		return err
	}

	if key != "" {
		return fmt.Errorf("flush port[%d] db[%d] failed pleach check key[%s]", port, db, key)
	}
	job.runtime.Logger.Info("exec randomkey port[%d] db[%d] done.......", port, db)

	return nil
}

// CheckParams 检查参数是否符合
func (job *RedisFlushData) CheckParams() error {
	job.runtime.Logger.Info("check params doing.......")
	var err error
	if !job.params.IsFlushAll && len(job.params.DBList) == 0 {
		err = fmt.Errorf("flush type not flushall and db list is empty")
		job.runtime.Logger.Error(err.Error())
		return err
	}

	/* 不支持flushdb(或者说：只支持flush db 0)的集群类型有：
	原生cluster集群
	Tendisplus集群
	TendisSSD 只支持flushalldisk
	...
	*/

	if !job.params.IsFlushAll { // 清理DB
		if !consts.IsAllowFlushMoreDB(job.params.DbType) { // 不支持清理多db的架构类型
			if !(len(job.params.DBList) == 1 && job.params.DBList[0] == 0) { // 不止清理DB0
				err = fmt.Errorf("cluster type only allow flush db 0")
				job.runtime.Logger.Error(err.Error())
				return err
			}
		}
	}

	// 检查实例角色，检查,初始化 database
	job.DataBases, err = job.GetInsDatabase(job.params.Ports[0])
	if !job.params.IsFlushAll {
		for _, db := range job.params.DBList {
			if db >= job.DataBases {
				return fmt.Errorf("db num[%d] > ins databases[%d], pleace check", db, job.DataBases)
			}
		}
	}

	for _, port := range job.params.Ports {
		if err = job.CheckInsRole(port); err != nil {
			return err
		}
	}
	return nil
}

// CheckInsRole 检查
func (job *RedisFlushData) CheckInsRole(port int) error {
	insAddr := fmt.Sprintf("%s:%d", job.params.IP, port)
	redisClient, err := myredis.NewRedisClient(insAddr, job.params.Password, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		return err
	}
	defer redisClient.Close()

	role, err := redisClient.GetRole()
	if err != nil {
		return err
	}
	job.runtime.Logger.Info("redis port[%d] role is %s", port, role)

	if role != "master" {
		return fmt.Errorf("redis port[%d] role not's master, pleace check", port)
	}
	return nil
}

// GetInsDatabase 获取databases
func (job *RedisFlushData) GetInsDatabase(port int) (int, error) {
	insAddr := fmt.Sprintf("%s:%d", job.params.IP, port)
	redisClient, err := myredis.NewRedisClient(insAddr, job.params.Password, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		return 0, err
	}
	defer redisClient.Close()

	result, err := redisClient.ConfigGet("databases")
	if err != nil {
		return 0, err
	}
	return strconv.Atoi(result["databases"])
}

// Retry times
func (job *RedisFlushData) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisFlushData) Rollback() error {
	return nil
}
