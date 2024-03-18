package atomredis

import (
	"encoding/json"
	"fmt"
	"sort"
	"strconv"
	"sync"
	"time"

	"github.com/go-playground/validator/v10"
	"github.com/shirou/gopsutil/v3/mem"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// MaxMemoryDynamicalSetParam maxmemory dynamical set param
type MaxMemoryDynamicalSetParam struct {
	IP    string `json:"ip" validate:"required"`
	Ports []int  `json:"ports" validate:"required"`
}

// RedisUsedMemItem redis used memory item
type RedisUsedMemItem struct {
	IP         string               `json:"ip"`
	Port       int                  `json:"port"`
	Password   string               `json:"-"`
	DbType     string               `json:"db_type"`
	UsedMemory int64                `json:"used_memory"`
	MaxMemory  int64                `json:"max_memory"`
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

// RedisMaxMemoryDynamicallySet redis max memory dynamical set
type RedisMaxMemoryDynamicallySet struct {
	params           MaxMemoryDynamicalSetParam
	runtime          *jobruntime.JobGenericRuntime
	OsAvailMem       int64               `json:"host_avail_mem_for_redis"`
	UsedMemSum       int64               `json:"redis_used_memory_sum"` // used_memory总和
	SortUsedMemItems []*RedisUsedMemItem `json:"sort_used_mem_items"`
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisMaxMemoryDynamicallySet)(nil)

// NewRedisMaxMemoryDynamicalSet  new
func NewRedisMaxMemoryDynamicalSet() jobruntime.JobRunner {
	return &RedisMaxMemoryDynamicallySet{}
}

// Init prepare run env
func (job *RedisMaxMemoryDynamicallySet) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("MaxMemoryDynamicallySet Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("MaxMemoryDynamicallySet Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	if len(job.params.Ports) == 0 {
		err = fmt.Errorf("MaxMemoryDynamicallySet ports(%+v) is invalid", job.params.Ports)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	return nil
}

// Name 原子任务名
func (job *RedisMaxMemoryDynamicallySet) Name() string {
	return "redis_maxmemory_dynamically_set"
}

// Run Command Run
func (job *RedisMaxMemoryDynamicallySet) Run() (err error) {
	err = job.GetHostAvailMem()
	if err != nil {
		return err
	}
	err = job.GetRedisUsedMemory()
	if err != nil {
		return err
	}
	defer job.DisConnectAllRedis()

	err = job.CalculateRedisMaxMemory()
	if err != nil {
		return err
	}
	err = job.ConcurrentlyConfigSetMaxmemory()
	if err != nil {
		return err
	}
	return nil
}

// GetRedisUsedMemory 获取redis实例的used_memory信息并排序
func (job *RedisMaxMemoryDynamicallySet) GetRedisUsedMemory() (err error) {
	job.SortUsedMemItems = make([]*RedisUsedMemItem, 0, len(job.params.Ports))
	for _, port := range job.params.Ports {
		job.SortUsedMemItems = append(job.SortUsedMemItems, &RedisUsedMemItem{
			IP:   job.params.IP,
			Port: port,
		})
	}
	// 获取每个redis实例的password
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		redisItem.GetPassword()
		if redisItem.Err != nil {
			return redisItem.Err
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
				memItem.Err = fmt.Errorf("%s not a cache instance,db_type:%s", memItem.Addr(), memItem.DbType)
				mylog.Logger.Error(memItem.Err.Error())
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
		}(redisItem)
	}
	wg.Wait()
	job.UsedMemSum = 0
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		if redisItem.Err != nil {
			job.runtime.Logger.Error(redisItem.Err.Error())
			return redisItem.Err
		}
		job.UsedMemSum += redisItem.UsedMemory
	}
	sort.Slice(job.SortUsedMemItems, func(i, j int) bool {
		return job.SortUsedMemItems[i].UsedMemory < job.SortUsedMemItems[j].UsedMemory
	})
	return nil
}

// DisConnectAllRedis disconnect all redis client connection in job.SortUsedMemItems
func (job *RedisMaxMemoryDynamicallySet) DisConnectAllRedis() {
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		if redisItem.redisCli != nil {
			redisItem.redisCli.Close()
		}
	}
	return
}

// GetHostAvailMem TODO
func (job *RedisMaxMemoryDynamicallySet) GetHostAvailMem() (err error) {
	job.OsAvailMem, err = GetLocalHostAvailMemory()
	if err != nil {
		err = fmt.Errorf("%s get local host available memory fail,err:%v",
			job.params.IP, err)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	job.runtime.Logger.Info("get local host available memory(%s): %s",
		job.params.IP, util.SizeToHumanStr(job.OsAvailMem))
	return nil
}

// CalculateRedisMaxMemory 计算每个redis实例的maxmemory,考虑剩余内存和已使用内存
// 1. 如果 所有redis的used_memory 总和 已经大于 系统hostAvailMem了，则直接将当前 used_memory设置为maxmemory;
// 2. 否则，计算每个redis的maxmemory:
// 当前redis的used_memry/当前服务器上所有redis的used_memory总和*(当前服务器上所有redis的最大可用内存 - 当前服务器上所有redis的used_memory总和) + 当前redis的used_memry
// 整体思路就是: 按照当前每个redis的used_memory来分配 系统剩余可用内存
// 如果某个redis的 used_memory 小于 最大used_memory的1/10, 则给redis的 maxmemory 增加 500MiB。
// 避免严重数据倾斜, 导致部分数据量小的redis分配不到内存的情况
func (job *RedisMaxMemoryDynamicallySet) CalculateRedisMaxMemory() (err error) {
	// 1. 如果 所有redis的used_memory 总和 已经大于 系统hostAvailMem了，则直接将当前 used_memory设置为maxmemory;
	if job.UsedMemSum > job.OsAvailMem {
		job.runtime.Logger.Warn(
			"%s redis UsedMemSum:%s > HostAvailMemForRedis:%s,set maxmemory will result into write operate fail",
			job.params.IP, util.SizeToHumanStr(job.UsedMemSum), util.SizeToHumanStr(job.OsAvailMem))
		for _, item := range job.SortUsedMemItems {
			redis := item
			redis.MaxMemory = redis.UsedMemory
		}
		return nil
	}
	// 2. 计算每个redis的maxmemory:

	// 获取最大的used_memory的redis节点
	maxUsedMemItem := job.SortUsedMemItems[len(job.SortUsedMemItems)-1]
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		redisItem.MaxMemory = int64(float64(redisItem.UsedMemory)/float64(job.UsedMemSum)*float64(job.OsAvailMem-
			job.UsedMemSum) +
			float64(redisItem.UsedMemory))
		if maxUsedMemItem.UsedMemory > 10*redisItem.UsedMemory {
			redisItem.MaxMemory = redisItem.MaxMemory + 500*consts.MiByte
		}
	}
	return nil
}

// ConcurrentlyConfigSetMaxmemory 并发为redis和其slave节点设置 maxmemory
func (job *RedisMaxMemoryDynamicallySet) ConcurrentlyConfigSetMaxmemory() error {
	wg := sync.WaitGroup{}
	for _, item := range job.SortUsedMemItems {
		redisItem := item
		wg.Add(1)
		go func(memItem *RedisUsedMemItem) {
			defer wg.Done()
			mylog.Logger.Info("redis(%s) used_memory:%s maxmemory:%s",
				memItem.Addr(), util.SizeToHumanStr(memItem.UsedMemory), util.SizeToHumanStr(memItem.MaxMemory))
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
				mylog.Logger.Info("redis(%s) slave %s maxmemory set to %s",
					memItem.Addr(), slaveItem.Addr(), util.SizeToHumanStr(memItem.MaxMemory))
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
			return redisItem.Err
		}
	}
	return nil
}

// Retry times
func (job *RedisMaxMemoryDynamicallySet) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisMaxMemoryDynamicallySet) Rollback() error {
	return nil
}

// 每种资源规格对应的redis可用内存量，单位byte
var resourceSpecOsMem = map[string]int64{
	"2g_min":     consts.GiByte * 3 / 2,
	"2g_max":     consts.GiByte * 2,
	"2g_avail":   consts.GiByte * 2 * 6 / 10,
	"4g_min":     consts.GiByte * 7 / 2,
	"4g_max":     consts.GiByte * 4,
	"4g_avail":   consts.GiByte * 4 * 6 / 10,
	"8g_min":     consts.GiByte * 15 / 2,
	"8g_max":     consts.GiByte * 8,
	"8g_avail":   consts.GiByte * 8 * 8 / 10,
	"16g_min":    consts.GiByte * 15,
	"16g_max":    consts.GiByte * 16,
	"16g_avail":  consts.GiByte * 16 * 85 / 100,
	"32g_min":    consts.GiByte * 30,
	"32g_max":    consts.GiByte * 32,
	"32g_avail":  consts.GiByte * 32 * 85 / 100,
	"64g_min":    consts.GiByte * 61,
	"64g_max":    consts.GiByte * 64,
	"64g_avail":  consts.GiByte * 64 * 9 / 10,
	"128g_min":   consts.GiByte * 125,
	"128g_max":   consts.GiByte * 128,
	"128g_avail": consts.GiByte * 128 * 9 / 10,
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
