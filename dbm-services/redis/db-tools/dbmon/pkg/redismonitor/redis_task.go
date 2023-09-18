package redismonitor

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/models/myredis"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"

	"github.com/dustin/go-humanize"
)

// RedisMonitorTask redis monitor task
type RedisMonitorTask struct {
	baseTask
	redisClis []*myredis.RedisClient `json:"-"`
	Err       error                  `json:"-"`
}

// NewRedisMonitorTask new
func NewRedisMonitorTask(conf *config.Configuration, serverConf config.ConfServerItem,
	password string) (task *RedisMonitorTask, err error) {
	task = &RedisMonitorTask{}
	task.baseTask, err = newBaseTask(conf, serverConf, password)
	if err != nil {
		return
	}
	return
}

func (task *RedisMonitorTask) getRedisAddr(ip string, port int) string {
	return ip + ":" + strconv.Itoa(port)
}

// RunMonitor 每次执行只会产生一种告警,否则告警可能太多了
func (task *RedisMonitorTask) RunMonitor() {
	defer func() {
		for _, cliItem := range task.redisClis {
			cli01 := cliItem
			cli01.Close()
		}
		task.redisClis = []*myredis.RedisClient{}
	}()
	task.CheckRedisConn()
	if task.Err != nil {
		return
	}
	task.SetDbmonKeyOnMaster()
	if task.Err != nil {
		return
	}
	task.CheckSyncOnSlave()
	if task.Err != nil {
		return
	}
	task.CheckPersist()
	if task.Err != nil {
		return
	}
	task.TendisSSDCheck()
	if task.Err != nil {
		return
	}
	task.CheckCacheMaxmemory()
	if task.Err != nil {
		return
	}
	task.CheckClusterState()
	if task.Err != nil {
		return
	}
	return
}

// CheckRedisConn check redis whether can connect
func (task *RedisMonitorTask) CheckRedisConn() {
	var cli01 *myredis.RedisClient
	var addr01 string
	for _, port := range task.ServerConf.ServerPorts {
		addr01 = task.getRedisAddr(task.ServerConf.ServerIP, port)
		cli01, task.Err = myredis.NewRedisClientWithTimeout(addr01, task.Password, 0,
			consts.TendisTypeRedisInstance, 5*time.Second)
		if task.Err != nil {
			task.eventSender.SetInstance(addr01)
			task.eventSender.SendWarning(consts.EventRedisLogin, task.Err.Error(), consts.WarnLevelError,
				task.ServerConf.ServerIP)
			return
		}
		task.redisClis = append(task.redisClis, cli01)
	}
}

// SetDbmonKeyOnMaster 如果'我'是master,则写入 dbmon:$master_ip:$master_port key
func (task *RedisMonitorTask) SetDbmonKeyOnMaster() {
	var role, dbmonKey string
	var clusterEnabled bool
	timeVal := time.Now().Local().Unix()
	timeStr := strconv.FormatInt(timeVal, 10)
	for idx, cli01 := range task.redisClis {
		cliItem := cli01
		task.eventSender.SetInstance(cliItem.Addr)
		role, task.Err = cliItem.GetRole()
		if task.Err != nil {
			task.eventSender.SendWarning(consts.EventRedisLogin, task.Err.Error(),
				consts.WarnLevelError, task.ServerConf.ServerIP)
			return
		}
		if role != consts.RedisMasterRole {
			continue
		}
		clusterEnabled, task.Err = cliItem.IsClusterEnabled()
		if task.Err != nil {
			task.eventSender.SendWarning(consts.EventRedisLogin, task.Err.Error(),
				consts.WarnLevelError, task.ServerConf.ServerIP)
			return
		}
		// cluster 集群不写入dbmon:* keys
		if clusterEnabled {
			continue
		}
		cliItem.SelectDB(1)

		dbmonKey = fmt.Sprintf("dbmon:%s:%d", task.ServerConf.ServerIP, task.ServerConf.ServerPorts[idx])
		_, task.Err = cliItem.Set(dbmonKey, timeStr, 0)
		if task.Err != nil {
			task.eventSender.SendWarning(consts.EventRedisLogin, task.Err.Error(),
				consts.WarnLevelError, task.ServerConf.ServerIP)
			return
		}
	}
}

// setSlaveDbmonKey 从slave上连接master,并执行set dbmon:$slaveIP:$slaveport $time
func (task *RedisMonitorTask) setSlaveDbmonKey(selfAddr, masterIP, masterPort string) {
	var masterCli *myredis.RedisClient = nil
	var msg, dbmonKey string
	var clusterEnabled bool
	masterAddr := masterIP + ":" + masterPort
	masterCli, task.Err = myredis.NewRedisClientWithTimeout(masterAddr, task.Password, 0,
		consts.TendisTypeRedisInstance, 5*time.Second)
	if task.Err != nil {
		msg = fmt.Sprintf("redis(%s) conn_master fail,master is %s:%s", selfAddr, masterIP, masterPort)
		mylog.Logger.Error(msg)
		task.eventSender.SendWarning(consts.EventRedisSync, msg, consts.WarnLevelError, task.ServerConf.ServerIP)
		return
	}
	defer masterCli.Close()

	clusterEnabled, task.Err = masterCli.IsClusterEnabled()
	if task.Err != nil {
		return
	}
	// cluster 集群不写入dbmon:* keys
	if clusterEnabled {
		return
	}

	task.Err = masterCli.SelectDB1WhenClusterDisabled()
	if task.Err != nil {
		return
	}
	dbmonKey = fmt.Sprintf("dbmon:%s", selfAddr)
	timeVal := time.Now().Local().Unix()
	timeStr := strconv.FormatInt(timeVal, 10)
	_, task.Err = masterCli.Set(dbmonKey, timeStr, 0)
	if task.Err != nil {
		msg = fmt.Sprintf("redis_master(%s) 'set %s %s' fail", masterAddr, dbmonKey, timeStr)
		mylog.Logger.Error(msg)
		task.eventSender.SendWarning(consts.EventRedisSync, msg, consts.WarnLevelError, task.ServerConf.ServerIP)
		return
	}
}

func (task *RedisMonitorTask) checkSlaveTimediff(idx int) {
	var clusterEnabled bool
	var timeDiffKey, timeDiffStr, msg string
	var timeDiffVal int
	var warnLevel string
	cliItem := task.redisClis[idx]
	clusterEnabled, task.Err = cliItem.IsClusterEnabled()
	if task.Err != nil {
		return
	}
	// cluster 集群不写入dbmon:* keys
	if clusterEnabled {
		return
	}
	task.Err = cliItem.SelectDB1WhenClusterDisabled()
	if task.Err != nil {
		return
	}
	timeDiffKey = fmt.Sprintf("%s:timediff", cliItem.Addr)
	timeDiffStr, task.Err = cliItem.Get(timeDiffKey)
	if task.Err != nil {
		return
	}
	timeDiffVal, _ = strconv.Atoi(timeDiffStr)
	if timeDiffVal > consts.EventTimeDiffWarning {
		warnLevel = consts.WarnLevelWarning
		if timeDiffVal > consts.EventTimeDiffError {
			warnLevel = consts.WarnLevelError
		}
		task.eventSender.AppendMetrcs(map[string]float64{
			"timediff": float64(timeDiffVal),
		})

		msg = fmt.Sprintf("redis_slave(%s) SYNC timediff(%d) > %ds", cliItem.Addr, timeDiffVal, 120)
		mylog.Logger.Warn(msg)
		task.eventSender.SendWarning(consts.EventRedisSync, msg, warnLevel, task.ServerConf.ServerIP)
		return
	}
}

// CheckSyncOnSlave 检查slave上的sync状态
func (task *RedisMonitorTask) CheckSyncOnSlave() {
	var msg, warnLevel string
	var masterHost, masterPort, linkStatus, selfRole string
	var masterLastIOSec int64
	for idx, cli01 := range task.redisClis {
		cliItem := cli01
		task.eventSender.SetInstance(cliItem.Addr)
		masterHost, masterPort, linkStatus, selfRole, masterLastIOSec, task.Err = cliItem.GetMasterData()
		if task.Err != nil {
			// task.trigger.SendWarning(consts.WarnRedisSync, task.Err.Error(), task.ServerConf.ServerIP)
			// return
			continue
		}
		if selfRole != consts.RedisSlaveRole {
			continue
		}
		task.setSlaveDbmonKey(cliItem.Addr, masterHost, masterPort)
		if task.Err != nil {
			return
		}
		if linkStatus != consts.MasterLinkStatusUP {
			msg = fmt.Sprintf("redis_slave(%s) master_link_status=%s", cliItem.Addr, linkStatus)
			mylog.Logger.Error(msg)
			task.eventSender.SendWarning(consts.EventRedisSync, msg, consts.WarnLevelError, task.ServerConf.ServerIP)
			return
		}
		if masterLastIOSec > consts.EventMasterLastIOSecWarning {
			warnLevel = consts.WarnLevelWarning
			if masterLastIOSec > consts.EventMasterLastIOSecError {
				warnLevel = consts.WarnLevelError
			}
			task.eventSender.AppendMetrcs(map[string]float64{
				"master_last_io_seconds_ago": float64(masterLastIOSec),
			})
			msg = fmt.Sprintf("redis_slave(%s) master_last_io_seconds_ago:%d > %d",
				cliItem.Addr, masterLastIOSec, consts.EventMasterLastIOSecWarning)
			mylog.Logger.Warn(msg)
			task.eventSender.SendWarning(consts.EventRedisSync, msg, warnLevel, task.ServerConf.ServerIP)
			return
		}
		task.checkSlaveTimediff(idx)
		if task.Err != nil {
			return
		}
	}
}

// CheckPersist 检查master是否有slave,检查cache redis slave是否开启aof
func (task *RedisMonitorTask) CheckPersist() {
	var role, dbtype, appendonly string
	var msg string
	var connectedSlaves int
	var confmap map[string]string
	for _, cli01 := range task.redisClis {
		cliItem := cli01
		task.eventSender.SetInstance(cliItem.Addr)
		role, task.Err = cliItem.GetRole()
		if task.Err != nil {
			// task.trigger.SendWarning(consts.WarnRedisLogin, task.Err.Error(), task.ServerConf.ServerIP)
			// return
			continue
		}
		connectedSlaves, task.Err = cliItem.ConnectedSlaves()
		if task.Err != nil {
			// task.trigger.SendWarning(consts.WarnRedisLogin, task.Err.Error(), task.ServerConf.ServerIP)
			// return
			continue
		}
		if role == consts.RedisMasterRole && connectedSlaves == 0 {
			msg = fmt.Sprintf("redis_master(%s) no slave", cliItem.Addr)
			mylog.Logger.Error(msg)
			task.eventSender.SendWarning(consts.EventRedisPersist, msg, consts.WarnLevelError, task.ServerConf.ServerIP)
			return
		}
		dbtype, task.Err = cliItem.GetTendisType()
		if task.Err != nil {
			continue
		}
		if dbtype != consts.TendisTypeRedisInstance || role != consts.RedisSlaveRole {
			continue
		}
		// 检查 cache redis slave, aof 是否开启
		// TODO 无法知道远程配置的情况下,如果是人为关闭的aof,如何不告警
		confmap, task.Err = cliItem.ConfigGet("appendonly")
		if task.Err != nil {
			continue
		}
		appendonly, _ = confmap["appendonly"]
		if strings.ToLower(appendonly) == "no" {
			msg = fmt.Sprintf("redis_slave(%s) appendonly==%s", cliItem.Addr, appendonly)
			mylog.Logger.Warn(msg)
			task.eventSender.SendWarning(consts.EventRedisPersist, msg, consts.WarnLevelWarning, task.ServerConf.ServerIP)
			return
		}
	}
}

// TendisSSDCheck tendisssd check
// - check binloglen
func (task *RedisMonitorTask) TendisSSDCheck() {
	var dbtype, msg, warnLevel string
	var binlogRange myredis.TendisSSDBinlogSize
	var binlogLen uint64
	for _, cli01 := range task.redisClis {
		cliItem := cli01
		task.eventSender.SetInstance(cliItem.Addr)
		dbtype, task.Err = cliItem.GetTendisType()
		if task.Err != nil {
			continue
		}
		if dbtype != consts.TendisTypeTendisSSDInsance {
			continue
		}
		binlogRange, task.Err = cliItem.TendisSSDBinlogSize()
		if task.Err != nil {
			continue
		}
		binlogLen = binlogRange.EndSeq - binlogRange.FirstSeq
		if binlogLen > consts.EventSSDBinlogLenWarnning {
			warnLevel = consts.WarnLevelWarning
			if binlogLen > consts.EventSSDBinlogLenError {
				warnLevel = consts.WarnLevelError
			}
			task.eventSender.AppendMetrcs(map[string]float64{
				"binloglen": float64(binlogLen),
			})
			msg = fmt.Sprintf("tendisSSD(%s) binlogrange[%d,%d] binloglen %d > %d ",
				cliItem.Addr,
				binlogRange.FirstSeq, binlogRange.EndSeq, binlogLen,
				consts.EventSSDBinlogLenWarnning)
			mylog.Logger.Warn(msg)
			task.eventSender.SendWarning(consts.EventTendisBinlogLen, msg, warnLevel, task.ServerConf.ServerIP)
			return
		}
	}
}

// CheckCacheMaxmemory 检查cache redis的memused 与 maxmemory比值
func (task *RedisMonitorTask) CheckCacheMaxmemory() {
	var dbtype, msg, warnLevel string
	var maxmemory uint64
	var memoryUsed uint64
	var usedPercent float64
	for _, cli01 := range task.redisClis {
		cliItem := cli01
		task.eventSender.SetInstance(cliItem.Addr)
		dbtype, task.Err = cliItem.GetTendisType()
		if task.Err != nil {
			continue
		}
		if dbtype != consts.TendisTypeRedisInstance {
			continue
		}
		maxmemory, task.Err = cliItem.MaxMemory()
		if task.Err != nil {
			continue
		}
		if maxmemory == 0 {
			continue
		}
		memoryUsed, _, task.Err = cliItem.GetMemUsed()
		if task.Err != nil {
			continue
		}
		usedPercent = float64(memoryUsed*1.0) / float64(maxmemory)
		if usedPercent > consts.EventMemoryUsedPercentWarnning {
			warnLevel = consts.WarnLevelWarning
			if usedPercent > consts.EventMemoryUsedPercentError {
				warnLevel = consts.WarnLevelError
			}
			task.eventSender.AppendMetrcs(map[string]float64{
				"used_memory":  float64(memoryUsed),
				"maxmemory":    float64(maxmemory),
				"used_percent": usedPercent,
			})
			msg = fmt.Sprintf("redis(%s) used_memory:%s maxmemory:%s used_percent:%.2f%%",
				cliItem.Addr,
				humanize.IBytes(memoryUsed), humanize.IBytes(maxmemory), usedPercent,
			)
			mylog.Logger.Warn(msg)
			task.eventSender.SendWarning(consts.EventRedisMaxmemory, msg, warnLevel, task.ServerConf.ServerIP)
		}
	}
}

// CheckClusterState 检查集群状态
func (task *RedisMonitorTask) CheckClusterState() {
	var clusterEnabled bool
	var clusterInfo *myredis.CmdClusterInfo
	var msg string
	for _, cli01 := range task.redisClis {
		cliItem := cli01
		task.eventSender.SetInstance(cliItem.Addr)
		clusterEnabled, task.Err = cliItem.IsClusterEnabled()
		if task.Err != nil {
			return
		}
		if !clusterEnabled {
			continue
		}
		clusterInfo, task.Err = cliItem.ClusterInfo()
		if task.Err != nil {
			return
		}
		if clusterInfo.ClusterState != consts.ClusterStateOK {
			msg = fmt.Sprintf("redis(%s) cluster_state:%s != %s", cliItem.Addr, clusterInfo.ClusterState, consts.ClusterStateOK)
			mylog.Logger.Warn(msg)
			task.eventSender.SendWarning(consts.EventRedisClusterState, msg, consts.WarnLevelError, task.ServerConf.ServerIP)
			return
		}
	}
}
