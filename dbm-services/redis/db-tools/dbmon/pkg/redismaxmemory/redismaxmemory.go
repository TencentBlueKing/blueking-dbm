// Package redismaxmemory TODO
package redismaxmemory

import (
	"encoding/json"
	"fmt"
	"math"
	"reflect"
	"sort"
	"strconv"
	"sync"
	"time"

	"github.com/shirou/gopsutil/v3/mem"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/models/myredis"
	"dbm-services/redis/db-tools/dbmon/models/mysqlite"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/sendwarning"
	"dbm-services/redis/db-tools/dbmon/util"
)

// globRedisMaxmemoryJob global var
var globRedisMaxmemoryJob *Job
var maxmemoryOnce sync.Once

// Job TODO
type Job struct {
	Conf                *config.Configuration `json:"conf"`
	IP                  string                `json:"ip"`
	OsAvailMem          int64                 `json:"host_avail_mem_for_redis"` // 本机器上可用内存
	UsedMemSum          int64                 `json:"redis_used_memory_sum"`    // 本机器上所有redis used_memory总和
	SortUsedMemItems    []*RedisUsedMemItem   `json:"sort_used_mem_items"`
	addrToUsedMem       map[string]int64      // 保存 addr 和used_memory的映射
	oldAddrToUsedMemRow *RedisNodesUsedMemSchema
	eventSender         *sendwarning.BkMonitorEventSender
	sqdb                *gorm.DB
	IsRunning           bool `json:"-"`
	Err                 error
}

// GetGlobRedisMaxmemorySet 新建maxmemory务
func GetGlobRedisMaxmemorySet(conf *config.Configuration) *Job {
	maxmemoryOnce.Do(func() {
		globRedisMaxmemoryJob = &Job{
			Conf: conf,
		}
	})
	return globRedisMaxmemoryJob
}

func (job *Job) reInit() {
	job.IP = ""
	job.OsAvailMem = 0
	job.UsedMemSum = 0
	job.SortUsedMemItems = []*RedisUsedMemItem{}
	job.addrToUsedMem = make(map[string]int64)
	job.oldAddrToUsedMemRow = nil
	job.sqdb = nil
}

// Run Command Run
func (job *Job) Run() {
	job.IsRunning = true
	defer func() {
		job.IsRunning = false
	}()
	if !job.Conf.RedisMaxmemorySet.Enable {
		// 配置中,这个集群不启用动态设置 maxmemory
		mylog.Logger.Info(fmt.Sprintf("redismaxmemory not enable"))
		return
	}
	mylog.Logger.Info(fmt.Sprintf("redismaxmemory wakeup,start running..."))
	defer func() {
		if job.Err != nil {
			mylog.Logger.Info(fmt.Sprintf("redismaxmemory end fail,err:%v", job.Err))
		} else {
			mylog.Logger.Info(fmt.Sprintf("redismaxmemory end succ"))
		}
	}()
	job.reInit()
	if job.Err != nil {
		return
	}
	job.SetEventSender()

	job.getSqlDB()
	if job.Err != nil {
		return
	}
	defer job.closeDB()

	// 获取本机器上可用内存
	job.GetHostAvailMem()
	if job.Err != nil {
		return
	}
	// 获取本机器上所有redis used_memory总和
	job.GetRedisUsedMemory()
	if job.Err != nil {
		return
	}
	if len(job.SortUsedMemItems) == 0 {
		return
	}
	defer job.DisConnectAllRedis()

	isSkip := job.isSkipMaxmemorySet()
	if job.Err != nil {
		return
	}
	if isSkip {
		return
	}
	// 计算每个redis实例的maxmemory
	job.CalculateRedisMaxMemory()
	if job.Err != nil {
		return
	}
	// 并发设置每个redis实例的maxmemory
	job.ConcurrentlyConfigSetMaxmemory()
	if job.Err != nil {
		return
	}
	job.saveUsedMemToLocalDB()
}

// GetRedisUsedMemory 并发获得redis实例的used_memory
func (job *Job) GetRedisUsedMemory() {
	job.SortUsedMemItems = []*RedisUsedMemItem{}
	for _, server := range job.Conf.Servers {
		if !consts.IsRedisMetaRole(server.MetaRole) {
			continue
		}
		for _, port := range server.ServerPorts {
			job.SortUsedMemItems = append(job.SortUsedMemItems, &RedisUsedMemItem{
				IP:   server.ServerIP,
				Port: port,
			})
		}
	}
	if len(job.SortUsedMemItems) == 0 {
		return
	}
	// 获取每个redis实例的password
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		redisItem.GetPassword()
		if redisItem.Err != nil {
			job.Err = redisItem.Err
			return
		}
	}
	// concurrently get multi redis used memory
	wg := sync.WaitGroup{}
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		wg.Add(1)
		go func(memItem *RedisUsedMemItem) {
			defer wg.Done()
			memItem.redisCli, memItem.Err = myredis.NewRedisClientWithTimeout(memItem.Addr(), memItem.Password,
				0, consts.TendisTypeRedisInstance, 5*time.Second)
			if memItem.Err != nil {
				return
			}
			memItem.DbType, memItem.Err = memItem.redisCli.GetTendisType()
			if memItem.Err != nil {
				memItem.Err = fmt.Errorf("get redis type fail,err:%v", memItem.Err)
			}
			if memItem.DbType != consts.TendisTypeRedisInstance {
				// 如果不是cache redis实例,不用继续
				return
			}
			// redisConn run command "info memory"
			infoRet, err := memItem.redisCli.Info("memory")
			if err != nil {
				memItem.Err = err
				return
			}
			memItem.UsedMemory, memItem.Err = strconv.ParseInt(infoRet["used_memory"], 10, 64)
			if memItem.Err != nil {
				memItem.Err = fmt.Errorf("redis(%s) 'info memory' [used_memory]:%s parseInt Fail,err:%v",
					memItem.Addr(), infoRet["used_memory"], memItem.Err)
				return
			}
			// 执行 config get maxmemoryStr
			maxmemoryStr, err := memItem.redisCli.ConfigGet("maxmemory")
			if err != nil {
				memItem.Err = err
				return
			}
			memItem.MaxMemory, memItem.Err = strconv.ParseInt(maxmemoryStr["maxmemory"], 10, 64)
			if memItem.Err != nil {
				memItem.Err = fmt.Errorf("redis(%s) 'config get maxmemory' [maxmemory]:%s parseInt Fail,err:%v",
					memItem.Addr(), maxmemoryStr["maxmemory"], memItem.Err)
				return
			}
			// 获取 role
			memItem.Role, memItem.Err = memItem.redisCli.GetRole()
			if memItem.Err != nil {
				return
			}
			// 获取 master role
			memItem.MasterRole, _ = memItem.redisCli.GetMasterRole()
		}(redisItem)
	}
	wg.Wait()
	job.UsedMemSum = 0
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		if redisItem.Err != nil {
			mylog.Logger.Error(redisItem.Err.Error())
			job.Err = redisItem.Err
			return
		}
		job.UsedMemSum += redisItem.UsedMemory
		job.addrToUsedMem[redisItem.Addr()] = redisItem.UsedMemory
	}
	sort.Slice(job.SortUsedMemItems, func(i, j int) bool {
		return job.SortUsedMemItems[i].UsedMemory < job.SortUsedMemItems[j].UsedMemory
	})
	return
}

// DisConnectAllRedis disconnect all redis client connection in job.SortUsedMemItems
func (job *Job) DisConnectAllRedis() {
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		if redisItem.redisCli != nil {
			redisItem.redisCli.Close()
		}
	}
	return
}

// GetHostAvailMem 获得本地主机最大可用内存
func (job *Job) GetHostAvailMem() (err error) {
	job.OsAvailMem, err = GetLocalHostAvailMemory()
	if err != nil {
		err = fmt.Errorf("%s get local host available memory fail,err:%v",
			job.IP, err)
		mylog.Logger.Error(err.Error())
		return err
	}
	mylog.Logger.Debug(fmt.Sprintf("get local host available memory(%s): %s",
		job.IP, util.SizeToHumanStr(job.OsAvailMem)))
	return nil
}

// SetEventSender set event sender
func (job *Job) SetEventSender() {
	if job.eventSender != nil {
		return
	}
	job.eventSender, job.Err = sendwarning.NewBkMonitorEventSender(
		job.Conf.RedisMonitor.BkMonitorEventDataID,
		job.Conf.RedisMonitor.BkMonitorEventToken,
		job.Conf.BeatPath,
		job.Conf.AgentAddress,
	)
	if job.Err != nil {
		mylog.Logger.Error(fmt.Sprintf("set event sender fail,err:%v", job.Err))
		return
	}
	if len(job.Conf.Servers) == 0 {
		return
	}
	serverConf := job.Conf.Servers[0]
	instAddr := serverConf.ServerIP + ":0"
	job.IP = serverConf.ServerIP
	job.eventSender.
		SetBkBizID(serverConf.BkBizID).
		SetBkCloudID(serverConf.BkCloudID).
		SetApp(serverConf.App).
		SetAppName(serverConf.AppName).
		SetInstance(instAddr)
	return
}

func (job *Job) getSqlDB() {
	job.sqdb, job.Err = mysqlite.GetLocalSqDB()
	if job.Err != nil {
		return
	}
	job.Err = job.sqdb.AutoMigrate(&RedisNodesUsedMemSchema{})
	if job.Err != nil {
		job.Err = fmt.Errorf("RedisMaxmemoryBackendsSchema AutoMigrate fail,err:%v", job.Err)
		mylog.Logger.Info(job.Err.Error())
		return
	}
}

func (job *Job) closeDB() {
	mysqlite.CloseDB(job.sqdb)
}

func (job *Job) saveUsedMemToLocalDB() {
	if job.oldAddrToUsedMemRow == nil {
		job.oldAddrToUsedMemRow = &RedisNodesUsedMemSchema{}
	}
	job.oldAddrToUsedMemRow.IP = job.IP
	job.oldAddrToUsedMemRow.AddrToUsedMem = util.ToString(job.addrToUsedMem)
	job.oldAddrToUsedMemRow.UpdateTime = time.Now().Local()
	job.Err = job.sqdb.Clauses(clause.OnConflict{
		UpdateAll: true,
	}).Create(job.oldAddrToUsedMemRow).Error
	if job.Err != nil {
		mylog.Logger.Error(fmt.Sprintf("save redis backends data to local sqlite db fail,err:%v,ip:%s,row:%s",
			job.Err, job.IP, util.ToString(job.oldAddrToUsedMemRow)))
		return
	}
	return
}

// getOldUsedMem 从本地sqlite中获取旧的redis used_mem数据
func (job *Job) getOldUsedMem() {
	job.oldAddrToUsedMemRow = &RedisNodesUsedMemSchema{}
	job.Err = job.sqdb.Where("ip=?", job.IP).First(job.oldAddrToUsedMemRow).Error
	if job.Err != nil {
		if job.Err == gorm.ErrRecordNotFound {
			mylog.Logger.Debug(fmt.Sprintf("not found redis backends data in local sqlite db,ip:%s", job.IP))
			job.Err = nil
			return
		}
		mylog.Logger.Error(fmt.Sprintf("get redis backends data from local sqlite db fail,ip:%s,err:%v", job.IP, job.Err))
		return
	}
	return
}

// isSkipMaxmemorySet 返回 true,表示跳过maxmemory设置; 返回false,表示需要设置maxmemory
func (job *Job) isSkipMaxmemorySet() bool {
	// 非cache redis返回true
	if len(job.SortUsedMemItems) == 0 {
		return true
	} else if job.SortUsedMemItems[0].DbType != consts.TendisTypeRedisInstance {
		mylog.Logger.Debug(fmt.Sprintf("redismaxmemory only support redis,not support %s,addr:%s",
			job.SortUsedMemItems[0].DbType, job.SortUsedMemItems[0].Addr()))
		return true
	}
	// 存在一个redis实例是master 或者 存在一个redis是slave且其master依然是slave(链式slave),则继续执行
	// 否则返回true
	isAnyMaster := false
	isMyMasterStillSlave := false
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		if redisItem.Role == consts.RedisMasterRole {
			isAnyMaster = true
			break
		}
		if redisItem.Role == consts.RedisSlaveRole && redisItem.MasterRole == consts.RedisSlaveRole {
			isMyMasterStillSlave = true
			break
		}
	}
	if !isAnyMaster && !isMyMasterStillSlave {
		mylog.Logger.Info("all redis is slave and not master->slave->slave chain,skip maxmemory set")
		return true
	}
	// 如果redis实例 maxmemory 加起来,小于可用内存的80%,则返回false
	var maxmemorySum int64 = 0
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		maxmemorySum = maxmemorySum + redisItem.MaxMemory
	}
	if maxmemorySum <= job.OsAvailMem*8/10 {
		mylog.Logger.Info(fmt.Sprintf("maxmemory sum:%d,os avail mem:%d,need maxmemory set", maxmemorySum, job.OsAvailMem))
		return false
	}
	job.getOldUsedMem()
	if job.Err != nil {
		return true
	}
	// oldAddrToUsedMemRow为空,代表是第一次设置maxmemory
	if job.oldAddrToUsedMemRow == nil || job.oldAddrToUsedMemRow.AddrToUsedMem == "" {
		mylog.Logger.Info(fmt.Sprintf("oldAddrToUsedMemRow is empty,firstly maxmemory set"))
		return false
	}
	oldAddrToUsedMem := map[string]int64{}
	if err := json.Unmarshal([]byte(job.oldAddrToUsedMemRow.AddrToUsedMem), &oldAddrToUsedMem); err != nil {
		job.Err = fmt.Errorf("unmarshal oldAddrToUsedMemRow.AddrToUsedMem fail,err:%v,addrToUsedMem:%s",
			err, job.oldAddrToUsedMemRow.AddrToUsedMem)
		mylog.Logger.Error(job.Err.Error())
		return false
	}
	//  如果某个redis的 used_mem >= maxmemroy*0.95,则返回false
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		if redisItem.UsedMemory >= redisItem.MaxMemory*95/100 {
			mylog.Logger.Info(fmt.Sprintf("redis %s used_mem:%d, maxmemory:%d,need maxmemory set",
				redisItem.Addr(), redisItem.UsedMemory, redisItem.MaxMemory))
			return false
		}
	}
	// 如果 addrs 变了,则返回false
	oldAddrs := make([]string, 0, len(oldAddrToUsedMem))
	for k, _ := range oldAddrToUsedMem {
		oldAddrs = append(oldAddrs, k)
	}
	newAddrs := make([]string, 0, len(job.SortUsedMemItems))
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		newAddrs = append(newAddrs, redisItem.Addr())
	}
	sort.Strings(oldAddrs)
	sort.Strings(newAddrs)
	if !reflect.DeepEqual(oldAddrs, newAddrs) {
		mylog.Logger.Info(fmt.Sprintf("addrs changed,need maxmemory set,oldAddrs:%v,newAddrs:%v", oldAddrs, newAddrs))
		return false
	}
	// 执行到这里,说明addrs没变
	// 如果某个redis的used_mem变化超过了200MB or 超过 20%,则返回false
	var oldUsedMem int64 = 0
	var currUsedMem int64 = 0
	var diffUsedMme int64 = 0
	var diffPercent float64
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		oldUsedMem = oldAddrToUsedMem[redisItem.Addr()]
		currUsedMem = redisItem.UsedMemory
		diffUsedMme = currUsedMem - oldUsedMem
		if math.Abs(float64(diffUsedMme)) > GetUsedMemoryChangeThreshold(job.Conf) {
			mylog.Logger.Info(fmt.Sprintf("redis %s used_mem changed:%s,need maxmemory set",
				redisItem.Addr(), util.SizeToHumanStr(diffUsedMme)))
			return false
		}
		signStr := "+"
		if diffUsedMme < 0 {
			signStr = "-"
		}
		diffPercent = math.Abs(float64(diffUsedMme)) * 100 / float64(oldUsedMem)
		if diffPercent > GetUsedMemoryChangePercent(job.Conf) {
			mylog.Logger.Info(fmt.Sprintf("redis %s used_mem changed:%s%.2f%%,need maxmemory set",
				redisItem.Addr(), signStr, diffPercent))
			return false
		}
	}
	return true
}

// CalculateRedisMaxMemory 计算每个redis实例的maxmemory,考虑剩余内存和已使用内存
// 1. 如果 所有redis的used_memory 总和 已经大于 系统hostAvailMem了，则直接将当前 used_memory设置为maxmemory;
// 2. 否则，计算每个redis的maxmemory:
// 当前redis的used_memry/当前服务器上所有redis的used_memory总和*(当前服务器上所有redis的最大可用内存 - 当前服务器上所有redis的used_memory总和) + 当前redis的used_memry
// 整体思路就是: 按照当前每个redis的used_memory来分配 系统剩余可用内存
// 如果某个redis的 used_memory 小于 最大used_memory的1/10, 则给redis的 maxmemory 增加 500MiB。
// 避免严重数据倾斜, 导致部分数据量小的redis分配不到内存的情况
func (job *Job) CalculateRedisMaxMemory() {
	// 1. 如果 所有redis的used_memory 总和 已经大于 系统hostAvailMem了，则直接将当前 used_memory设置为maxmemory;
	if job.UsedMemSum > job.OsAvailMem {
		mylog.Logger.Warn(fmt.Sprintf(
			"%s redis UsedMemSum:%s > HostAvailMemForRedis:%s,set maxmemory will result into write operate fail",
			job.IP, util.SizeToHumanStr(job.UsedMemSum), util.SizeToHumanStr(job.OsAvailMem)))
		for _, item := range job.SortUsedMemItems {
			redis := item
			redis.MaxMemory = redis.UsedMemory
		}
		return
	}
	// 2. 计算每个redis的maxmemory:

	// 获取最大的used_memory的redis节点
	maxUsedMemItem := job.SortUsedMemItems[len(job.SortUsedMemItems)-1]
	var sumMaxmemory int64 = 0
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		redisItem.MaxMemory = int64(float64(redisItem.UsedMemory)/float64(job.UsedMemSum)*float64(job.OsAvailMem-
			job.UsedMemSum) +
			float64(redisItem.UsedMemory))
		sumMaxmemory = sumMaxmemory + redisItem.MaxMemory
		if maxUsedMemItem.UsedMemory > 10*redisItem.UsedMemory {
			redisItem.MaxMemory = redisItem.MaxMemory + 500*consts.MiByte
			// 超小的redis,则其maxmemory不添加到 sumMaxmemory
		}
	}
	if sumMaxmemory > job.OsAvailMem {
		// 如果sumMaxmemory大于OsAvailMem,则说明计算出来的maxmemory总和大于系统可用内存,则直接报错
		job.Err = fmt.Errorf("sumMaxmemory:%s > OsAvailMem:%s",
			util.SizeToHumanStr(sumMaxmemory), util.SizeToHumanStr(job.OsAvailMem))
		mylog.Logger.Error(job.Err.Error())
		return
	}
	return
}

// ConcurrentlyConfigSetMaxmemory 并发为redis和其slave节点设置 maxmemory
func (job *Job) ConcurrentlyConfigSetMaxmemory() {
	wg := sync.WaitGroup{}
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		wg.Add(1)
		go func(memItem *RedisUsedMemItem) {
			defer wg.Done()
			mylog.Logger.Info(fmt.Sprintf("redis(%s) used_memory:%s maxmemory:%s",
				memItem.Addr(), util.SizeToHumanStr(memItem.UsedMemory), util.SizeToHumanStr(memItem.MaxMemory)))
			_, memItem.Err = memItem.redisCli.ConfigSet("maxmemory", strconv.FormatInt(memItem.MaxMemory, 10))
			if memItem.Err != nil {
				return
			}
			_, memItem.Err = memItem.redisCli.ConfigSet("maxmemory-policy", consts.PolicyNoeviction)
			if memItem.Err != nil {
				return
			}
			var slaves []*myredis.InfoReplSlave
			slaves, _, memItem.Err = memItem.redisCli.GetInfoReplSlaves()
			if memItem.Err != nil {
				return
			}
			for _, slave := range slaves {
				slaveItem := slave
				mylog.Logger.Info(fmt.Sprintf("redis(%s) slave %s maxmemory set to %s",
					memItem.Addr(), slaveItem.Addr(), util.SizeToHumanStr(memItem.MaxMemory)))
				func(tmpItem *myredis.InfoReplSlave, password string, maxmemory int64) {
					var err error
					// 连接slave 并设置maxmemory
					slaveCli, err := myredis.NewRedisClientWithTimeout(tmpItem.Addr(), password, 0, consts.TendisTypeRedisInstance,
						10*time.Second)
					if err != nil {
						return
					}
					defer slaveCli.Close()
					_, err = slaveCli.ConfigSet("maxmemory", strconv.FormatInt(maxmemory, 10))
					if err != nil {
						return
					}
					_, err = slaveCli.ConfigSet("maxmemory-policy", consts.PolicyNoeviction)
					if err != nil {
						return
					}
					return
				}(slaveItem, memItem.Password, memItem.MaxMemory)
			}
		}(redisItem)
	}
	wg.Wait()
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		if redisItem.Err != nil {
			job.Err = redisItem.Err
			return
		}
	}
	return
}

// 每种资源规格对应的redis可用内存量，单位byte
var resourceSpecOsMem = map[string]int64{
	"2g_min":     consts.GiByte * 3 / 2,
	"2g_max":     consts.GiByte * 2,
	"2g_avail":   consts.GiByte * 2 * 5 / 10, // 1GB可用
	"4g_min":     consts.GiByte * 7 / 2,
	"4g_max":     consts.GiByte * 4,
	"4g_avail":   consts.GiByte * 4 * 5 / 10, // 2GB可用
	"8g_min":     consts.GiByte * 15 / 2,
	"8g_max":     consts.GiByte * 8,
	"8g_avail":   consts.GiByte * 8 * 75 / 100, // 6GB可用
	"16g_min":    consts.GiByte * 15,
	"16g_max":    consts.GiByte * 16,
	"16g_avail":  consts.GiByte * 16 * 81 / 100, // 13GB可用
	"32g_min":    consts.GiByte * 30,
	"32g_max":    consts.GiByte * 32,
	"32g_avail":  consts.GiByte * 32 * 85 / 100, // 27.2GB可用
	"64g_min":    consts.GiByte * 61,
	"64g_max":    consts.GiByte * 64,
	"64g_avail":  consts.GiByte * 64 * 87 / 100, // 55.68GB可用
	"128g_min":   consts.GiByte * 125,
	"128g_max":   consts.GiByte * 128,
	"128g_avail": consts.GiByte * 128 * 90 / 100, // 115.2GB可用
}

// GetLocalHostAvailMemory TODO
func GetLocalHostAvailMemory() (maxAvailMem int64, err error) {
	memInfo, err := mem.VirtualMemory()
	if err != nil {
		err = fmt.Errorf("mem.VirtualMemory fail,err:%v", err)
		return 0, err
	}
	osTotalSize := int64(memInfo.Total)
	if osTotalSize >= resourceSpecOsMem["2g_min"] && osTotalSize <= resourceSpecOsMem["2g_max"] {
		return resourceSpecOsMem["2g_avail"], nil
	} else if osTotalSize >= resourceSpecOsMem["4g_min"] && osTotalSize <= resourceSpecOsMem["4g_max"] {
		return resourceSpecOsMem["4g_avail"], nil
	} else if osTotalSize >= resourceSpecOsMem["8g_min"] && osTotalSize <= resourceSpecOsMem["8g_max"] {
		return resourceSpecOsMem["8g_avail"], nil
	} else if osTotalSize >= resourceSpecOsMem["16g_min"] && osTotalSize <= resourceSpecOsMem["16g_max"] {
		return resourceSpecOsMem["16g_avail"], nil
	} else if osTotalSize >= resourceSpecOsMem["32g_min"] && osTotalSize <= resourceSpecOsMem["32g_max"] {
		return resourceSpecOsMem["32g_avail"], nil
	} else if osTotalSize >= resourceSpecOsMem["64g_min"] && osTotalSize <= resourceSpecOsMem["64g_max"] {
		return resourceSpecOsMem["64g_avail"], nil
	} else if osTotalSize >= resourceSpecOsMem["128g_min"] && osTotalSize <= resourceSpecOsMem["128g_max"] {
		return resourceSpecOsMem["128g_avail"], nil
	}
	// 如果没有匹配到
	// - 系统总内存小于4g，则返回总内存的60%作为可用内存;
	// - 系统总内存大于等于4g小于8g，则返回总内存的80%作为可用内存;
	// - 系统总内存大于等于8g小于128g，则返回总内存的90%作为可用内存;
	// - 系统总内存大于等于128g，则返回总内存的95%作为可用内存;
	if osTotalSize < consts.GiByte*4 {
		return osTotalSize * 6 / 10, nil
	} else if osTotalSize < consts.GiByte*8 {
		return osTotalSize * 8 / 10, nil
	} else if osTotalSize < consts.GiByte*128 {
		return osTotalSize * 9 / 10, nil
	}
	return osTotalSize * 95 / 100, nil
}

// RedisNodesUsedMemSchema redis nodes used memory
type RedisNodesUsedMemSchema struct {
	IP            string    `json:"ip" gorm:"column:ip;size:128;not null;default:'';primaryKey"`
	AddrToUsedMem string    `json:"addr_to_used_mem" gorm:"column:addr_to_used_mem;not null;default:''"`
	UpdateTime    time.Time `json:"update_time" gorm:"column:update_time;not null;default:'';index"`
}

// TableName table name
func (r *RedisNodesUsedMemSchema) TableName() string {
	return "redis_nodes_used_mem"
}

// RedisUsedMemItem redis used memory item
type RedisUsedMemItem struct {
	IP         string               `json:"ip"`
	Port       int                  `json:"port"`
	Password   string               `json:"-"`
	DbType     string               `json:"db_type"`
	UsedMemory int64                `json:"used_memory"`
	MaxMemory  int64                `json:"max_memory"`
	Role       string               `json:"role"`
	MasterRole string               `json:"master_role"`
	redisCli   *myredis.RedisClient `json:"-"`
	Err        error                `json:"-"`
}

// Addr return addr
func (r *RedisUsedMemItem) Addr() string {
	return fmt.Sprintf("%s:%d", r.IP, r.Port)
}

// GetPassword get password from conf file
func (r *RedisUsedMemItem) GetPassword() {
	r.Password, r.Err = myredis.GetRedisPasswdFromConfFile(r.Port)
	if r.Err != nil {
		mylog.Logger.Error(r.Err.Error())
	}
	return
}
