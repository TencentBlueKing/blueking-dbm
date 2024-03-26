package atomredis

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
)

// CliConnsKillParams 参数定义
type CliConnsKillParams struct {
	IP          string   `json:"ip" validate:"required"`
	Ports       []int    `json:"ports" validate:"required"`
	ExcludedIPs []string `json:"excluded_ips"`
	IsForce     bool     `json:"is_force"`
}

// RedisClientConnsKill 结构体定义
type RedisClientConnsKill struct {
	runtime       *jobruntime.JobGenericRuntime
	params        CliConnsKillParams
	excludedIpMap map[string]bool
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisBackup)(nil)

// NewRedisCliConnsKill new
func NewRedisCliConnsKill() jobruntime.JobRunner {
	return &RedisClientConnsKill{}
}

// Init 初始化
func (job *RedisClientConnsKill) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisClientKill Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisClientKill Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	return nil
}

// Name 原子任务名
func (job *RedisClientConnsKill) Name() string {
	return "redis_client_conns_kill"
}

// Run 执行
func (job *RedisClientConnsKill) Run() (err error) {
	if !job.params.IsForce {
		// 如果不是强制执行,先确认redis是否活着
		err = myredis.LocalRedisConnectTest(job.params.IP, job.params.Ports, "")
		if err != nil {
			return err
		}
	}
	err = job.GetExcludedIpMap()
	if err != nil {
		return err
	}
	// 连接redis实例，kill掉addr不在 excludedIpMap 中的连接
	var addr, password string
	for _, port := range job.params.Ports {
		addr = fmt.Sprintf("%s:%d", job.params.IP, port)
		password, err = myredis.GetRedisPasswdFromConfFile(port)
		if err != nil {
			continue
		}
		err = job.ConnectAndRunClientKill(addr, password)
		if err != nil {
			return err
		}
	}
	return nil
}

// GetExcludedIpMap 获取需要排除的ip列表
// - 先将 params.ExcludedIP 添加到 job.excludedIpMap中
// - 如果集群模式，则需要获取所有节点的ip地址添加到.excludedIpMap中
// - 如果有slave or master,则需要从库和主库的ip地址添加到.excludedIpMap中
func (job *RedisClientConnsKill) GetExcludedIpMap() (err error) {
	job.excludedIpMap = make(map[string]bool, len(job.params.ExcludedIPs))
	for _, ip := range job.params.ExcludedIPs {
		job.excludedIpMap[ip] = true
	}
	job.excludedIpMap[job.params.IP] = true
	// 连接第一个端口的redis实例，获取所有节点的ip地址
	firstPort := job.params.Ports[0]
	firstAddr := fmt.Sprintf("%s:%d", job.params.IP, firstPort)
	password, err := myredis.GetRedisPasswdFromConfFile(firstPort)
	if err != nil {
		return err
	}
	redisCli, err := myredis.NewRedisClientWithTimeout(firstAddr, password, 0,
		consts.TendisTypeRedisInstance, 5*time.Second)
	if err != nil {
		return err
	}
	defer redisCli.Close()
	clusterEnabled, err := redisCli.IsClusterEnabled()
	if err != nil {
		return err
	}
	// - 如果集群模式，则需要获取所有节点的ip地址添加到.excludedIpMap中
	if clusterEnabled {
		nodes, err := redisCli.GetClusterNodes()
		if err != nil {
			return err
		}
		for _, node := range nodes {
			nodeItem := node
			job.excludedIpMap[nodeItem.IP] = true
		}
	}
	// - 添加info replication中master_host
	masterHost, _, _, _, err := redisCli.GetMasterData()
	if err != nil {
		return err
	}
	if masterHost != "" {
		job.excludedIpMap[masterHost] = true
	}
	// - 添加info replication中slave_ip
	slaves, _, err := redisCli.GetInfoReplSlaves()
	if err != nil {
		return err
	}
	for _, slave := range slaves {
		slaveItem := slave
		job.excludedIpMap[slaveItem.IP] = true
	}
	return nil
}

// ConnectAndRunClientKill 连接并执行client kill操作
func (job *RedisClientConnsKill) ConnectAndRunClientKill(addr, password string) (err error) {
	// 连接redis
	redisCli, err := myredis.NewRedisClientWithTimeout(addr, password, 0,
		consts.TendisTypeRedisInstance, 5*time.Second)
	if err != nil {
		return err
	}
	defer redisCli.Close()
	lists, err := redisCli.ClientList()
	if err != nil {
		return err
	}
	var clientIP string
	for _, item := range lists {
		clientItem := item
		clientIP = clientItem.GetClientIP()
		if _, ok := job.excludedIpMap[clientIP]; !ok {
			redisCli.ClientKillAddr(clientItem.Addr)
		}
	}
	return
}

// Retry times
func (job *RedisClientConnsKill) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisClientConnsKill) Rollback() error {
	return nil
}
