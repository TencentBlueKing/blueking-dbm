package atomredis

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

/*
	支持集群切换
		1. Twemproxy + Tendis 架构支持
		2. Predixy + RedisCluster （TODO)

	单实例切换（TODO）
		1. 单实例绑定了 DNS/CLB/北极星
		2. 这里需要 直接调用 接口，进行切换

	是否同城：： 这里在Actor 不能校验！！！，所以， 这个参数传过来也没用 >_<

	// 输入参数
	{
    "cluster_meta":{
        "bk_biz_id":1,
        "immute_domain":"xx.db",
        "cluster_type":"xxx",
        "major_version":"sss",
        "twemproxy_set":[
            "1.1.a.1:50000"
        ],
        "redis_master_set":[
            "2.2.b.2:30000 1-10"
        ],
        "redis_slave_set":[
            "2.3.c.4:30000 1-10"
        ],
        "proxy_pass":"**",
        "storage_pass":"**"
    },
    "switch_info":[
        {
            "master":{
                "ip":"1.1.a.1",
                "port":30000,
            },
            "slave":{
                "ip":"1.1.b.2",
                "port":30000,
            }
        }
    ],
    "switch_condition":{
        "is_check_sync":true,
        "slave_master_diff_time":61,
        "last_io_second_ago":100,
        "can_write_before_switch":true,
        "sync_type":"msms"
    }
}
*/

// InstanceSwitchParam switch param
type InstanceSwitchParam struct {
	MasterInfo InstanceParam `json:"master"`
	SlaveInfo  InstanceParam `json:"slave"`
}

// InstanceParam instance (tendis/predixy/twemproxy) info
type InstanceParam struct {
	IP   string `json:"ip"`
	Port int    `json:"port"`
	// Passwrod string `json:"password"`
}

// SwitchSyncCheckParam swtich sync check param
type SwitchSyncCheckParam struct {
	IsCheckSync              bool `json:"is_check_sync"`          // 代表是否需要强制切换
	MaxSlaveMasterDiffTime   int  `json:"slave_master_diff_time"` // 最大心跳时间
	MaxSlaveLastIOSecondsAgo int  `json:"last_io_second_ago"`     // slave io线程最大时间
	// http://tendis.cn/#/Tendisplus/知识库/集群/manual_failover
	SwitchOpt string `json:"switch_opt"` // CLUSTER FAILOVER [FORCE|TAKEOVER]

	// CanWriteBeforeSwitch ,控制 slave 是否可写 【切换前可写、切换后可写】
	CanWriteBeforeSwitch bool   `json:"can_write_before_switch"`
	InstanceSyncType     string `json:"sync_type"` // mms msms
}

// ClusterInfo 集群信息，
type ClusterInfo struct {
	BkBizID         int      `json:"bk_biz_id"`
	ImmuteDomain    string   `json:"immute_domain"`
	ClusterType     string   `json:"cluster_type"`
	MajorVersion    string   `json:"major_version"`
	ProxySet        []string `json:"twemproxy_set"`    // addr ip:port
	RedisMasterSet  []string `json:"redis_master_set"` // addr ip:port [seg_start seg_end]
	RedisSlaveSet   []string `json:"redis_slave_set"`  // addr ip:port
	ProxyPassword   string   `json:"proxy_pass"`
	StoragePassword string   `json:"storage_pass"`
}

// SwitchParam cluster bind entry
type SwitchParam struct {
	ClusterMeta    ClusterInfo           `json:"cluster_meta"`
	SwitchRelation []InstanceSwitchParam `json:"switch_info"`
	SyncCondition  SwitchSyncCheckParam  `json:"switch_condition"`
}

// RedisSwitch entry
type RedisSwitch struct {
	runtime *jobruntime.JobGenericRuntime
	params  *SwitchParam

	errChan chan error
}

// NewRedisSwitch 创建一个redis switch对象
// TODO 1. cluster模式下， cluster forget
// TODO 2. cluster模式下， 切换逻辑验证
// TODO 3. cluster模式下， 同步状态校验
func NewRedisSwitch() jobruntime.JobRunner {
	return &RedisSwitch{}
}

var supportedClusterType map[string]struct{}

func init() {
	supportedClusterType = map[string]struct{}{}
	supportedClusterType[consts.TendisTypeTwemproxyTendisSSDInstance] = struct{}{}
	supportedClusterType[consts.TendisTypeTwemproxyRedisInstance] = struct{}{}
	supportedClusterType[consts.TendisTypePredixyTendisplusCluster] = struct{}{}
	supportedClusterType[consts.TendisTypePredixyRedisCluster] = struct{}{}
	supportedClusterType[consts.TendisTypeRedisCluster] = struct{}{}
}

// Init 初始化
func (job *RedisSwitch) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisSwitch Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisSwitch Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}

	// 集群类型支持校验
	if _, ok := supportedClusterType[job.params.ClusterMeta.ClusterType]; !ok {
		job.runtime.Logger.Error("unsupported cluster type :%s", job.params.ClusterMeta.ClusterType)
		return fmt.Errorf("unsupported cluster type :%s", job.params.ClusterMeta.ClusterType)
	}
	return nil
}

// Run 运行切换逻辑
func (job *RedisSwitch) Run() (err error) {
	job.runtime.Logger.Info("redisswitch start; params:%+v", job.params)

	// 前置检查
	if err := job.precheckForSwitch(); err != nil {
		job.runtime.Logger.Error("redisswitch precheck err:%v, params:%+v", err, job.params)
		return err
	}
	job.runtime.Logger.Info("redisswitch precheck all success !")

	job.runtime.Logger.Info("redisswitch begin do storages switch .")
	// 执行切换， proxy并行，instance 窜行
	for idx, storagePair := range job.params.SwitchRelation {
		if job.params.SyncCondition.CanWriteBeforeSwitch &&
			consts.IsTwemproxyClusterType(job.params.ClusterMeta.ClusterType) {
			if err := job.enableWrite4Slave(storagePair.SlaveInfo.IP,
				storagePair.SlaveInfo.Port, job.params.ClusterMeta.StoragePassword); err != nil {
				job.runtime.Logger.Error("enable write before change 2 master %d:[%+v];with err:%+v", idx, storagePair, err)
			}
		}
		// 这里需要区分集群类型， 不同架构切换方式不一致
		if consts.IsTwemproxyClusterType(job.params.ClusterMeta.ClusterType) {
			job.runtime.Logger.Info("do switch of twemproxy arch %s:%s",
				job.params.ClusterMeta.ImmuteDomain, job.params.ClusterMeta.ClusterType)
			if err := job.doTendisStorageSwitch4Twemproxy(storagePair); err != nil {
				job.runtime.Logger.Error("redisswitch switch failed when do %d:[%+v];with err:%+v", idx, storagePair, err)
				return err
			}
			if err := job.doSlaveOfNoOne4NewMaster(storagePair.SlaveInfo.IP,
				storagePair.SlaveInfo.Port, job.params.ClusterMeta.StoragePassword); err != nil {
				job.runtime.Logger.Error("redisswitch slaveof no one failed when do %d:[%+v];with err:%+v", idx, storagePair, err)
				return err
			}
			if err := job.checkProxyConsistency(); err != nil {
				job.runtime.Logger.Error("redisswitch after check all proxy backends consistency with err:%+v", err)
				return err
			}
		} else if consts.IsClusterDbType(job.params.ClusterMeta.ClusterType) {
			if err := job.doTendisStorageSwitch4Cluster(storagePair); err != nil {
				job.runtime.Logger.Error("redisswitch switch failed when do %d:[%+v];with err:%+v", idx, storagePair, err)
				return err
			}
		} else if consts.TendisTypeRedisInstance == job.params.ClusterMeta.ClusterType {
			if err := job.doSlaveOfNoOne4NewMaster(storagePair.SlaveInfo.IP,
				storagePair.SlaveInfo.Port, job.params.ClusterMeta.StoragePassword); err != nil {
				job.runtime.Logger.Error("redisswitch slaveof no one failed when do %d:[%+v];with err:%+v", idx, storagePair, err)
				return err
			}
			job.tryShutdownMasterInstance(storagePair.MasterInfo.IP,
				storagePair.MasterInfo.Port, job.params.ClusterMeta.StoragePassword)
		} else {
			job.runtime.Logger.Error("unsupported cluster type :%+v", job.params.ClusterMeta)
		}
		job.runtime.Logger.Info("switch from:%s:%d to:%s:%d success",
			storagePair.MasterInfo.IP, storagePair.MasterInfo.Port,
			storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port)
	}
	job.runtime.Logger.Info("redisswitch switch all success; domain:%s", job.params.ClusterMeta.ImmuteDomain)
	return nil
}

func (job *RedisSwitch) enableWrite4Slave(ip string, port int, pass string) error {
	newMasterAddr := fmt.Sprintf("%s:%d", ip, port)
	newMasterConn, err := myredis.NewRedisClientWithTimeout(newMasterAddr,
		pass, 0, job.params.ClusterMeta.ClusterType, time.Second*10)
	if err != nil {
		return err
	}
	defer newMasterConn.Close()
	rst, err := newMasterConn.ConfigSet("slave-read-only", "no")
	if err != nil {
		job.runtime.Logger.Error("[%s] config set slave-read-only no for failed:%+v", newMasterAddr, err)
		return err
	}
	if rst != "OK" {
		job.runtime.Logger.Error("[%s] config set slave-read-only no failed:%s", newMasterAddr, rst)
		return fmt.Errorf("slaveofNooNE:%s", rst)
	}
	job.runtime.Logger.Info("[%s] config set slave-read-only no result:%s", newMasterAddr, rst)
	return nil
}

func (job *RedisSwitch) doSlaveOfNoOne4NewMaster(ip string, port int, pass string) error {
	newMasterAddr := fmt.Sprintf("%s:%d", ip, port)
	newMasterConn, err := myredis.NewRedisClientWithTimeout(newMasterAddr,
		pass, 1, job.params.ClusterMeta.ClusterType, time.Second*10)
	if err != nil {
		return fmt.Errorf("[%s] conn new master failed :%+v", newMasterAddr, err)
	}
	defer newMasterConn.Close()
	rst, err := newMasterConn.SlaveOf("No", "oNE")
	if err != nil {
		job.runtime.Logger.Error("[%s] exec slaveof No oNE for failed:%+v", newMasterAddr, err)
		return fmt.Errorf("[%s] exec slaveof No oNE for failed:%+v", newMasterAddr, err)
	}
	if rst != "OK" {
		job.runtime.Logger.Error("[%s] exec slaveof No oNE for failed:%s", newMasterAddr, rst)
		return fmt.Errorf("[%s] slaveofNooNE:%s", newMasterAddr, rst)
	}
	_, err = newMasterConn.ConfigRewrite()
	if err != nil {
		return fmt.Errorf("[%s] exec ConfigRewrite for failed:%+v", newMasterAddr, err)
	}
	job.runtime.Logger.Info("[%s] exec slaveof No oNE for result:%s", newMasterAddr, rst)
	return nil
}

// tryShutdownMasterInstance 尝试去关掉master实例，使得长链接断开，重连到新的master实例上去
func (job *RedisSwitch) tryShutdownMasterInstance(ip string, port int, pass string) {
	oldMasterAddr := fmt.Sprintf("%s:%d", ip, port)
	oldMasterConn, err := myredis.NewRedisClientWithTimeout(oldMasterAddr,
		pass, 1, job.params.ClusterMeta.ClusterType, time.Second*10)
	if err != nil {
		job.runtime.Logger.Warn("[%s] conn old master failed:%+v", oldMasterAddr, err)
		return
	}
	defer oldMasterConn.Close()
	if _, err := oldMasterConn.DoCommand([]string{"ShutDown"}, 0); err != nil {
		job.runtime.Logger.Warn("[%s] shutdown old master failed:%+v", oldMasterAddr, err)
	}
	return
}

// doTendisStorageSwitch4Cluster rediscluster 类型架构切换姿势 http://redis.cn/commands/cluster-failover.html
func (job *RedisSwitch) doTendisStorageSwitch4Cluster(storagePair InstanceSwitchParam) error {
	newMasterAddr := fmt.Sprintf("%s:%d", storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port)
	newMasterConn, err := myredis.NewRedisClientWithTimeout(newMasterAddr,
		job.params.ClusterMeta.StoragePassword, 0, job.params.ClusterMeta.ClusterType, time.Second*10)
	if err != nil {
		return err
	}
	defer newMasterConn.Close()

	// 该命令只能在群集slave节点执行，让slave节点进行一次人工故障切换。
	if job.params.SyncCondition.SwitchOpt == "" {
		if rst := newMasterConn.InstanceClient.ClusterFailover(context.TODO()); rst.Err() != nil {
			job.runtime.Logger.Error("on [%s] exec %s  failed:%+v", newMasterAddr, rst.String(), err)
			return err
		}
	} else {
		if _, err := newMasterConn.DoCommand([]string{"CLUSTER", "FAILOVER",
			job.params.SyncCondition.SwitchOpt}, 0); err != nil {
			job.runtime.Logger.Error("exec cluster FAILOVER %s for %s failed:%+v",
				newMasterAddr, job.params.SyncCondition.SwitchOpt, err)
			return err
		}
	}

	time.Sleep(time.Second) // 预留足够的投票时间
	if infomap, err := newMasterConn.Info("replication"); err != nil {
		job.runtime.Logger.Error("exec info replication for %s failed:%s", newMasterAddr, err)
		return fmt.Errorf("ErrInfo:%s", err)
	} else {
		job.runtime.Logger.Info("on [%s] info replication : %+v", newMasterAddr, infomap)
		if strings.ToUpper(infomap["role"]) == "SLAVE" {
			job.runtime.Logger.Error("on [%s] exec cluster failover %s with no err, but role is <SLAVE>",
				newMasterAddr, job.params.SyncCondition.SwitchOpt)
			return fmt.Errorf("Err:SwitchFailed4Role<SLAVE>")
		} else {
			job.runtime.Logger.Info("on [%s] exec cluster failover %s with no err, and role is <MASTER>",
				newMasterAddr, job.params.SyncCondition.SwitchOpt)
		}
	}

	clusterNodes, _ := newMasterConn.GetClusterNodes()
	job.runtime.PipeContextData = clusterNodes
	job.runtime.Logger.Info("switch succ from:%s:%d to:%s:%d ^_^",
		storagePair.MasterInfo.IP, storagePair.MasterInfo.Port,
		storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port)
	return nil
}

// doTendisStorageSwitch4Twemproxy 刷新twemproxy 后端
func (job *RedisSwitch) doTendisStorageSwitch4Twemproxy(storagePair InstanceSwitchParam) error {
	wg := &sync.WaitGroup{}
	errCh := make(chan error, len(job.params.ClusterMeta.ProxySet))
	for _, proxy := range job.params.ClusterMeta.ProxySet {
		wg.Add(1)
		go func(wg *sync.WaitGroup, proxy string) {
			defer wg.Done()
			addrx := strings.Split(proxy, ":")
			port, _ := strconv.Atoi(addrx[1])
			rst, err := util.DoSwitchTwemproxyBackends(addrx[0], port,
				fmt.Sprintf("%s:%d", storagePair.MasterInfo.IP, storagePair.MasterInfo.Port),
				fmt.Sprintf("%s:%d", storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port))
			if err != nil || (!strings.Contains(rst, "success") &&
				!strings.Contains(rst, "exits in server pool nosqlproxy")) {
				errCh <- fmt.Errorf("[%s:%d]switch proxy [%s] to:%s:%d result:%s,err:%+v",
					storagePair.MasterInfo.IP, storagePair.MasterInfo.Port, proxy,
					storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port, rst, err)
			}
			job.runtime.Logger.Info("[%s:%d]switch proxy [%s] to:%s:%d result:%s",
				storagePair.MasterInfo.IP, storagePair.MasterInfo.Port, proxy,
				storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port, rst)
		}(wg, proxy)
	}
	wg.Wait()
	close(errCh)

	for someErr := range errCh {
		return someErr
	}
	job.runtime.Logger.Info("[%s:%d]all proxy switch succ to:%s:%d ^_^",
		storagePair.MasterInfo.IP, storagePair.MasterInfo.Port,
		storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port)
	return nil
}

// precheckForSwitch 切换前的检查
func (job *RedisSwitch) precheckForSwitch() error {
	// // 1. 检查密码相同 job.params.ClusterMeta.StoragePassword
	// for _, pair := range job.params.SwitchRelation {
	// 	if pair.MasterInfo.Passwrod != job.params.ClusterMeta.StoragePassword {
	// 		return fmt.Errorf("err password not equal %s VS %s",
	// 			pair.MasterInfo.Passwrod, job.params.ClusterMeta.StoragePassword)
	// 	}
	// 	if pair.SlaveInfo.Passwrod != job.params.ClusterMeta.StoragePassword {
	// 		return fmt.Errorf("err password not equal %s VS %s",
	// 			pair.SlaveInfo.Passwrod, job.params.ClusterMeta.StoragePassword)
	// 	}
	// }

	// 2. 检查old master 是集群的master节点
	oldmasters := map[string]struct{}{}
	for _, oldmaster := range job.params.ClusterMeta.RedisMasterSet {
		if strings.Contains(oldmaster, "-") { // "2.2.x.4:30000 0-1"
			oldmaster = strings.Split(oldmaster, " ")[0]
		}
		oldmasters[oldmaster] = struct{}{}
	}
	for _, pair := range job.params.SwitchRelation {
		switchFrom := fmt.Sprintf("%s:%d", pair.MasterInfo.IP, pair.MasterInfo.Port)
		if _, ok := oldmasters[switchFrom]; !ok {
			return fmt.Errorf("err switch from storage {%s} not in cluster {%s}",
				switchFrom, job.params.ClusterMeta.ImmuteDomain)
		}
	}

	if consts.TendisTypeRedisInstance != job.params.ClusterMeta.ClusterType {
		// 3. 检查 proxy 可登陆 & proxy 状态一致
		job.runtime.Logger.Info("precheck for all proxies; domain:%s, proxies:%+v",
			job.params.ClusterMeta.ImmuteDomain, job.params.ClusterMeta.ProxySet)
		if err := job.precheckForProxy(); err != nil {
			return err
		}
		job.runtime.Logger.Info("precheck for all proxies succ !")
	}
	// 4. 检查redis 可登陆
	job.runtime.Logger.Info("precheck for [switchlink storages sync] storages:%+v", job.params.SwitchRelation)
	if err := job.precheckStorageLogin(); err != nil {
		return err
	}
	job.runtime.Logger.Info("precheck for [switchlink storages sync] login succ !")

	// 5. 检查同步状态
	job.runtime.Logger.Info("precheck for [switchlink storages sync] status .")
	if err := job.precheckStorageSync(); err != nil {
		return err
	}
	return nil
}

func (job *RedisSwitch) precheckForProxy() error {
	if consts.IsTwemproxyClusterType(job.params.ClusterMeta.ClusterType) {
		// 3.1 检查 proxy 可登陆
		if err := job.precheckProxyLogin(); err != nil {
			job.runtime.Logger.Error("some [proxy login] failed :%+v", err)
			return err
		}
		job.runtime.Logger.Info("all [proxy login] succ !")

		// 3.2 检查proxy 状态一致
		if err := job.checkProxyConsistency(); err != nil {
			return err
		}
	} else {
		job.runtime.Logger.Warn("[%s] proxy check skiped !", job.params.ClusterMeta.ClusterType)
	}
	return nil
}

func (job *RedisSwitch) checkProxyConsistency() error {
	wg := &sync.WaitGroup{}
	md5Ch := make(chan string, len(job.params.ClusterMeta.ProxySet))

	for _, proxy := range job.params.ClusterMeta.ProxySet {
		wg.Add(1)
		go func(proxy string, wg *sync.WaitGroup, md5Ch chan string) {
			defer wg.Done()
			pmd5, err := util.GetTwemProxyBackendsMd5Sum(proxy)
			if err != nil {
				md5Ch <- fmt.Sprintf("%v", err)
			} else {
				md5Ch <- pmd5
			}
		}(proxy, wg, md5Ch)
	}
	wg.Wait()
	close(md5Ch)

	proxyMd5s := map[string]struct{}{}
	for pmd5 := range md5Ch {
		proxyMd5s[pmd5] = struct{}{}
	}
	if len(proxyMd5s) != 1 {
		return fmt.Errorf("err mutil [proxy backends md5] got [%+v]", proxyMd5s)
	}
	job.runtime.Logger.Info("all [proxy backends md5] consistency [%+v]", proxyMd5s)
	return nil
}

// precheckStorageSync 检查节点间同步状态
func (job *RedisSwitch) precheckStorageSync() error {
	wg := &sync.WaitGroup{}
	job.errChan = make(chan error, len(job.params.SwitchRelation)*3)

	for _, storagePair := range job.params.SwitchRelation {
		wg.Add(1)
		go func(storagePair InstanceSwitchParam, wg *sync.WaitGroup) {
			defer wg.Done()
			// oldMasterAddr := fmt.Sprintf("%s:%d", storagePair.MasterInfo.IP, storagePair.MasterInfo.Port)
			newMasterAddr := fmt.Sprintf("%s:%d", storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port)
			newMasterConn, err := myredis.NewRedisClientWithTimeout(newMasterAddr,
				job.params.ClusterMeta.StoragePassword, 0, job.params.ClusterMeta.ClusterType, time.Second*10)
			if err != nil {
				job.errChan <- fmt.Errorf("[%s]new master node, err:%+v", newMasterAddr, err)
				return
			}
			defer newMasterConn.Close()

			replic, err := newMasterConn.Info("replication")
			if err != nil {
				job.errChan <- fmt.Errorf("[%s]new master node,with info,err:%+v", newMasterAddr, err)
				return
			}
			job.runtime.Logger.Info("[%s]new master node replication info :%+v", newMasterAddr, replic)

			if _, ok := replic["slave0"]; !ok {
				job.runtime.Logger.Warn("[%s]new master node got no slave connected or replication , please note.", newMasterAddr)
			}

			if replic["role"] != "slave" || replic["master_link_status"] != "up" {
				job.runtime.Logger.Error("[%s]new master node role is %s(SLAVE), master_link_status is %s(UP)",
					newMasterAddr, replic["role"], replic["master_link_status"])
				job.errChan <- fmt.Errorf("[%s]new master node, bad role or link status", newMasterAddr)
			}

			if consts.IsTwemproxyClusterType(job.params.ClusterMeta.ClusterType) ||
				consts.TendisTypeRedisInstance == job.params.ClusterMeta.ClusterType {
				// 3. 检查监控写入心跳 master:PORT:time 时间差。 【重要！！！】 Twemproxy/单实例 架构才有，其他架构没有这个
				job.errChan <- job.checkReplicationSync(newMasterConn, storagePair, replic)
			}

			// 4. 检查信息对等 ，slave 的master 是真实的master
			realMasterIP := replic["master_host"]
			realMasterPort := replic["master_port"]
			job.errChan <- job.checkReplicationDetail(storagePair, realMasterIP, realMasterPort)
		}(storagePair, wg)
	}
	wg.Wait()
	close(job.errChan)

	var err error
	for err = range job.errChan {
		if err != nil {
			job.runtime.Logger.Error("got err :%+v", err)
		}
	}
	return err
}

// checkReplicationDetail 检查redis运行状态上真实的主从关系
func (job *RedisSwitch) checkReplicationDetail(
	storagePair InstanceSwitchParam, realIP, realPort string) error {

	if job.params.SyncCondition.InstanceSyncType == "mms" ||
		job.params.SyncCondition.InstanceSyncType == "ms" {
		// check slave's master
		if storagePair.MasterInfo.IP != realIP && strconv.Itoa(storagePair.MasterInfo.Port) != realPort {
			return fmt.Errorf("err switch type [%s] new master's [%s:%d] real master [%s:%s] not eq inputed [%s:%d]",
				job.params.SyncCondition.InstanceSyncType, storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port,
				realIP, realPort, storagePair.MasterInfo.IP, storagePair.MasterInfo.Port)
		}
		// check master && slave version compactiable.
		job.runtime.Logger.Info("[%s:%d] storage really had running confied master %s:%s in [ms] mode !",
			storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port, realIP, realPort)
	} else if job.params.SyncCondition.InstanceSyncType == "msms" {
		oldSlaveConn, err := myredis.NewRedisClientWithTimeout(fmt.Sprintf("%s:%s", realIP, realPort),
			job.params.ClusterMeta.StoragePassword, 1, job.params.ClusterMeta.ClusterType, time.Second*10)
		if err != nil {
			return fmt.Errorf("[%s:%d] conn addr:%s:%s,err:%+v",
				storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port, realIP, realPort, err)
		}
		defer oldSlaveConn.Close()
		slaveReplic, err := oldSlaveConn.Info("replication")
		if err != nil {
			return fmt.Errorf("[%s:%d] conn new master's master failed %s:%s,err:%+v",
				storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port, realIP, realPort, err)
		}
		job.runtime.Logger.Info("[%s:%d] cluster old slave: %s:%s replication info msms:%+v",
			storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port, realIP, realPort, slaveReplic)

		masterMasterHost := slaveReplic["master_host"]
		masterMasterPort := slaveReplic["master_port"]
		masterLastIOSeconds, _ := strconv.Atoi(slaveReplic["master_last_io_seconds_ago"])

		if slaveReplic["role"] != "slave" || slaveReplic["master_link_status"] != "up" {
			job.runtime.Logger.Error("[%s:%d] cluster old slave: %s:%s role:%s(SLAVE), master_link_status:%s(UP)",
				storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port,
				realIP, realPort, slaveReplic["role"], slaveReplic["master_link_status"])
			return fmt.Errorf("addr:%s:%s,new master bad role or link status", realIP, realPort)
		}
		job.runtime.Logger.Info("[%s:%d] cluster old slave: %s:%s role:%s, master_link_status:%s succ !",
			storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port,
			realIP, realPort, slaveReplic["role"], slaveReplic["master_link_status"])

		if masterMasterHost != storagePair.MasterInfo.IP || strconv.Itoa(storagePair.MasterInfo.Port) != masterMasterPort {
			return fmt.Errorf("addr:%s:%s,master bad run time with inputed old master :%s:%d",
				realIP, realPort, storagePair.MasterInfo.IP, storagePair.MasterInfo.Port)
		}
		job.runtime.Logger.Info("[%s:%d] cluster old slave: %s:%s really had confied master %s:%s succ !",
			storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port, realIP, realPort, masterMasterHost, masterMasterPort)

		if masterLastIOSeconds > job.params.SyncCondition.MaxSlaveLastIOSecondsAgo {
			return fmt.Errorf("err old slave's (%s:%s)[%s:%d] master_last_io_seconds_ago %d > %d ",
				realIP, realPort, storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port,
				masterLastIOSeconds, job.params.SyncCondition.MaxSlaveLastIOSecondsAgo)
		}
		job.runtime.Logger.Info("[%s:%d] cluster old slave: %s:%s master_last_io_seconds_ago:%d<(%d) succ !",
			storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port, realIP, realPort,
			masterLastIOSeconds, job.params.SyncCondition.MaxSlaveLastIOSecondsAgo)
	} else {
		return fmt.Errorf("[%s:%d] err unkown switch type : %s",
			storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port, job.params.SyncCondition.InstanceSyncType)
	}
	return nil
}

// checkReplicationSync # here we just check the master heartbeat:
func (job *RedisSwitch) checkReplicationSync(newMasterConn *myredis.RedisClient,
	storagePair InstanceSwitchParam, replic map[string]string) error {
	var err error
	var masterTime, masterDbsize, slaveTime int64
	oldMasterAddr := fmt.Sprintf("%s:%d", storagePair.MasterInfo.IP, storagePair.MasterInfo.Port)
	newMasterAddr := fmt.Sprintf("%s:%d", storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port)

	if err := newMasterConn.SelectDB(1); err != nil {
		return fmt.Errorf("[%s] select db 1, exec cmd err:%+v", newMasterAddr, err)
	}
	rst := newMasterConn.InstanceClient.Get(context.TODO(), fmt.Sprintf("%s:time", oldMasterAddr))
	if rst.Err() != nil {
		return fmt.Errorf("[%s]new master node, exec cmd err:%+v", newMasterAddr, err)
	}
	if masterTime, err = rst.Int64(); err != nil {
		return fmt.Errorf("[%s]new master node, time2Int64 err:%+v", newMasterAddr, err)
	}

	if rst = newMasterConn.InstanceClient.Get(context.TODO(),
		fmt.Sprintf("%s:0:dbsize", oldMasterAddr)); rst.Err() != nil {
		return fmt.Errorf("[%s]new master node, exec cmd err:%+v", newMasterAddr, err)
	}
	if masterDbsize, err = rst.Int64(); err != nil {
		job.runtime.Logger.Warn("[%s]new master node, get db0,dbsize2Int64 err:%+v", newMasterAddr, err)
	}

	slaveTime = time.Now().Unix() // here gcs.perl use redis-cli time
	lastIOseconds, _ := strconv.Atoi(replic["master_last_io_seconds_ago"])

	slaveMasterDiffTime := math.Abs(float64(slaveTime) - float64(masterTime))
	if slaveMasterDiffTime > float64(job.params.SyncCondition.MaxSlaveMasterDiffTime) {
		if job.params.SyncCondition.IsCheckSync {
			return fmt.Errorf("err master slave sync too long %s => %s diff: %.0f(%d)",
				oldMasterAddr, newMasterAddr, slaveMasterDiffTime, job.params.SyncCondition.MaxSlaveMasterDiffTime)
		}
		job.runtime.Logger.Warn("master slave sync too long %s => %s diff: %.0f(%d)",
			oldMasterAddr, newMasterAddr, slaveMasterDiffTime, job.params.SyncCondition.MaxSlaveMasterDiffTime)
	}
	if lastIOseconds > job.params.SyncCondition.MaxSlaveLastIOSecondsAgo {
		if job.params.SyncCondition.IsCheckSync {
			return fmt.Errorf("err slave's (%s) master_last_io_seconds_ago %d > %d ",
				newMasterAddr, lastIOseconds, job.params.SyncCondition.MaxSlaveLastIOSecondsAgo)
		}
		job.runtime.Logger.Warn("slave's (%s) master_last_io_seconds_ago %d > %d ",
			newMasterAddr, lastIOseconds, job.params.SyncCondition.MaxSlaveLastIOSecondsAgo)
	}

	job.runtime.Logger.Info(
		"[%s]new master node, master on slave time:%d, diff:%.0f dbsize:%d; slave time:%d, master_last_io_seconds_ago:%d",
		newMasterAddr, masterTime, slaveMasterDiffTime, masterDbsize, slaveTime, lastIOseconds)
	return nil
}

// precheckStorageLogin make sure all todo switch redis can login
func (job *RedisSwitch) precheckStorageLogin() error {
	wg := &sync.WaitGroup{}
	job.errChan = make(chan error, len(job.params.SwitchRelation))
	for _, storagePair := range job.params.SwitchRelation {
		wg.Add(1)
		go func(storagePair InstanceSwitchParam, clusterType string, wg *sync.WaitGroup) {
			defer wg.Done()
			addr := fmt.Sprintf("%s:%d", storagePair.MasterInfo.IP, storagePair.MasterInfo.Port)
			if err := job.precheckLogin(addr, job.params.ClusterMeta.StoragePassword, clusterType); err != nil {
				// job.errChan <- fmt.Errorf("addr:%s,err:%+v", addr, err)
				job.runtime.Logger.Warn("old master login failed :%s:%+v", addr, err)
			}
			if err := job.precheckLogin(fmt.Sprintf("%s:%d", storagePair.SlaveInfo.IP, storagePair.SlaveInfo.Port),
				job.params.ClusterMeta.StoragePassword, clusterType); err != nil {
				job.errChan <- fmt.Errorf("addr:%s,err:%+v", addr, err)
			}
		}(storagePair, job.params.ClusterMeta.ClusterType, wg)
	}
	wg.Wait()
	close(job.errChan)

	var err error
	for err = range job.errChan {
		if err != nil {
			job.runtime.Logger.Error("got err :%+v", err)
		}
	}
	return err
}

// precheckProxyLogin proxy 链接性检查
func (job *RedisSwitch) precheckProxyLogin() error {
	wg := &sync.WaitGroup{}
	job.errChan = make(chan error, len(job.params.ClusterMeta.ProxySet))
	for _, proxy := range job.params.ClusterMeta.ProxySet {
		wg.Add(1)
		go func(proxy string, clusterType string, wg *sync.WaitGroup) {
			defer wg.Done()
			if err := job.precheckLogin(proxy, job.params.ClusterMeta.ProxyPassword, clusterType); err != nil {
				job.errChan <- fmt.Errorf("addr:%s,err:%+v", proxy, err)
			}
		}(proxy, job.params.ClusterMeta.ClusterType, wg)
	}
	wg.Wait()
	close(job.errChan)

	var err error
	for err = range job.errChan {
		if err != nil {
			job.runtime.Logger.Error("precheck for [proxy login] got err :%+v", err)
		}
	}
	return err

}

// precheckLogin 检查 proxy/redis 可以登录
func (job *RedisSwitch) precheckLogin(addr, pass, clusterType string) error {
	rconn, err := myredis.NewRedisClientWithTimeout(addr, pass, 0, clusterType, time.Second*10)
	if err != nil {
		return fmt.Errorf("conn redis %s failed:%+v", addr, err)
	}
	defer rconn.Close()

	if _, err := rconn.DoCommand([]string{"PING"}, 0); err != nil {
		if strings.Contains(fmt.Sprintf("%s", err), "MOVED") {
			job.runtime.Logger.Warn("precheck for [redis login] got moved :%+v", err)
			return nil
		}
		return fmt.Errorf("do cmd failed %s:%+v", addr, err)
	}
	return nil
}

// Name 原子任务名
func (job *RedisSwitch) Name() string {
	return "redis_switch"
}

// Retry times
func (job *RedisSwitch) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisSwitch) Rollback() error {
	return nil
}
