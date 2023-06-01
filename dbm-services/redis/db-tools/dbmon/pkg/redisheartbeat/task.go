package redisheartbeat

import (
	"context"
	"fmt"
	"strconv"
	"time"

	"dbm-services/redis/db-tools/dbmon/models/myredis"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
)

// HeartbeatTask 心跳task
type HeartbeatTask struct { // NOCC:golint/naming(其他:)
	BkBizID        string               `json:"bk_biz_id"`
	BkCloudID      int64                `json:"bk_cloud_id"`
	ServerIP       string               `json:"server_ip"`
	ServerPort     int                  `json:"server_port"`
	Domain         string               `json:"domain"`
	Password       string               `json:"-"`
	DbType         string               `json:"db_type"` // RedisInstance or TendisplusInstance or TendisSSDInstance
	RealRole       string               `json:"role"`
	ClusterEnabled bool                 `json:"cluster_enabled"`
	DbSize         int64                `json:"dbsize"`
	MasterCli      *myredis.RedisClient `json:"-"`
	SlaveCli       *myredis.RedisClient `json:"-"`
	Err            error                `json:"-"`
}

// NewHeartbeatTask 新建心跳task
func NewHeartbeatTask(bkBizID string, bkCloudID int64,
	ip string, port int, domain, password string) *HeartbeatTask {
	return &HeartbeatTask{
		BkBizID:    bkBizID,
		BkCloudID:  bkCloudID,
		ServerIP:   ip,
		ServerPort: port,
		Domain:     domain,
		Password:   password,
	}
}

// Addr string
func (task *HeartbeatTask) Addr() string {
	return task.ServerIP + ":" + strconv.Itoa(task.ServerPort)
}

// UpdateHeartbeat 更新心跳信息
func (task *HeartbeatTask) UpdateHeartbeat() {
	task.newConnect()
	if task.Err != nil {
		return
	}
	defer func() {
		if task.MasterCli != nil {
			task.MasterCli.Close()
			task.MasterCli = nil
		}
		if task.SlaveCli != nil {
			task.SlaveCli.Close()
			task.SlaveCli = nil
		}
	}()
	task.UpdateInstanceHeartbeat()
	if task.Err != nil {
		return
	}
	task.UpdateTendisplusHeartbeat()
	if task.Err != nil {
		return
	}
}

func (task *HeartbeatTask) newConnect() {
	var masterIP, masterPort, masterAddr string
	var cli *myredis.RedisClient
	if task.Password == "" {
		task.Password, task.Err = myredis.GetRedisPasswdFromConfFile(task.ServerPort)
		if task.Err != nil {
			return
		}
	}
	cli, task.Err = myredis.NewRedisClientWithTimeout(task.Addr(), task.Password, 0,
		consts.TendisTypeRedisInstance, 5*time.Second)
	if task.Err != nil {
		return
	}
	masterIP, masterPort, _, task.RealRole, _, task.Err = cli.GetMasterData()
	if task.Err != nil {
		return
	}
	mylog.Logger.Debug(fmt.Sprintf("redis(%s) role:%s found master(%s:%s)", task.Addr(), task.RealRole, masterIP,
		masterPort))
	task.DbType, task.Err = cli.GetTendisType()
	if task.Err != nil {
		return
	}
	if !consts.IsTendisplusInstanceDbType(task.DbType) {
		// tendisplus执行dbsize很慢,所以不执行
		task.DbSize, task.Err = cli.DbSize()
		if task.Err != nil {
			return
		}
	}
	task.ClusterEnabled, task.Err = cli.IsClusterEnabled()
	if task.Err != nil {
		return
	}
	if task.RealRole == consts.RedisMasterRole {
		task.MasterCli = cli
	} else {
		task.SlaveCli = cli
		masterAddr = masterIP + ":" + masterPort
		task.MasterCli, task.Err = myredis.NewRedisClientWithTimeout(masterAddr, task.Password, 0,
			consts.TendisTypeRedisInstance, 5*time.Second)
		if task.Err != nil {
			return
		}
	}
}

// UpdateTendisplusHeartbeat 更新tendisplus心跳(调用adminset命令,确保每个kvstore都有心跳写入)
// 对回档很重要
func (task *HeartbeatTask) UpdateTendisplusHeartbeat() {
	if task.DbType != consts.TendisTypeTendisplusInsance {
		return
	}
	// tendisplus master会写入心跳,tendisplus slave也会在master中写入心跳
	beatKey := fmt.Sprintf("%s_%d:heartbeat", task.ServerIP, task.ServerPort)
	nowVal := time.Now().Local().Unix()
	_, task.Err = task.MasterCli.AdminSet(beatKey, strconv.FormatInt(nowVal, 10))
	if task.Err != nil {
		return
	}
}

// UpdateInstanceHeartbeat 更新 非cluster的 心跳信息
func (task *HeartbeatTask) UpdateInstanceHeartbeat() {
	if task.ClusterEnabled {
		mylog.Logger.Debug(fmt.Sprintf("redis:%s cluster-enabled=%v skip...", task.Addr(), task.ClusterEnabled))
		return
	}
	var kvlist []interface{}
	var slaveBeatTime time.Time
	// 如果允许切换为 db1
	task.Err = task.MasterCli.SelectDB1WhenClusterDisabled()
	if task.Err != nil {
		return
	}
	// 只有'我'是master,才设置
	if task.RealRole == consts.RedisMasterRole {
		kvlist = []interface{}{
			"master_ip", task.ServerIP,
			"master_port", strconv.Itoa(task.ServerPort),
		}
		_, task.Err = task.MasterCli.Mset(kvlist)
		if task.Err != nil {
			return
		}
	}
	// 无论'我'是master还是slave,都需要在master上写入这两个key
	timeKey := fmt.Sprintf("%s:%d:time", task.ServerIP, task.ServerPort)
	timeVal := time.Now().Local().Unix()
	var timeStr string

	kvlist = []interface{}{
		timeKey, strconv.FormatInt(timeVal, 10),
	}
	dbsizeKey := fmt.Sprintf("%s:%d:0:dbsize", task.ServerIP, task.ServerPort)
	if !consts.IsTendisplusInstanceDbType(task.DbType) {
		// 非tendisplus写入dbsize key
		kvlist = append(kvlist, dbsizeKey, strconv.FormatInt(task.DbSize, 10))
	}
	_, task.Err = task.MasterCli.Mset(kvlist)
	if task.Err != nil {
		return
	}
	// 只有'我'是slave,才在master上写入 diff key
	if task.RealRole == consts.RedisSlaveRole {
		task.Err = task.SlaveCli.SelectDB1WhenClusterDisabled()
		if task.Err != nil {
			return
		}
		task.Err = task.SlaveCli.ReadOnlyOnClusterSlave()
		if task.Err != nil {
			return
		}
		timeStr, task.Err = task.SlaveCli.InstanceClient.Get(context.TODO(), timeKey).Result()
		if task.Err != nil {
			task.Err = fmt.Errorf("redis:%s db:1 'get %s' fail,err:%v", task.SlaveCli.Addr, timeKey, task.Err)
			mylog.Logger.Error(task.Err.Error())
			return
		}
		if timeStr == "" {
			return
		}
		timeVal, _ := strconv.ParseInt(timeStr, 10, 64)
		slaveBeatTime = time.Unix(timeVal, 0)
		diffSec := int(time.Now().Local().Sub(slaveBeatTime).Seconds())
		diffKey := fmt.Sprintf("%s:%d:timediff", task.ServerIP, task.ServerPort)
		kvlist = []interface{}{diffKey, strconv.Itoa(diffSec)}
		_, task.Err = task.MasterCli.Mset(kvlist)
		if task.Err != nil {
			return
		}
	}
}
