package atomredis

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"math/rand"
	"os"
	"sort"
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

// ClusterMigrateSlotsParams slots 迁移参数
type ClusterMigrateSlotsParams struct {
	SrcNode ClusterNodeItem `json:"src_node" validate:"required"`
	DstNode ClusterNodeItem `json:"dst_node" validate:"required"`
	// 用于缩容场景，迁移DstNode slot ，然后删除节点
	IsDeleteNode bool `json:"is_delete_node"`
	// 缩容节点的地址信息[aa.bb:port,cc.dd:port]
	ToBeDelNodesAddr []string `json:"to_be_del_nodes_addr"`
	// 迁移特定的slot,一般用于热点key情况，把该key所属slot迁移到单独节点
	MigrateSpecifiedSlot bool `json:"migrate_specified_slot" `
	// 如 0-4095 6000 6002-60010,
	Slots string `json:"slots"`
}

// ClusterMigrateSlots slots 迁移
type ClusterMigrateSlots struct {
	params  ClusterMigrateSlotsParams
	runtime *jobruntime.JobGenericRuntime
	Err     error `json:"_"`
}

// ClusterNodeItem  节点信息
type ClusterNodeItem struct {
	IP         string               `json:"ip"`
	Port       int                  `json:"port"`
	Password   string               `json:"password"`
	Role       string               `json:"role"`
	TendisType string               `json:"tendis_type"`
	redisCli   *myredis.RedisClient `json:"-"` // NOCC:vet/vet(设计如此)
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*ClusterMigrateSlots)(nil)

// NewClusterMigrateSlots new
func NewClusterMigrateSlots() jobruntime.JobRunner {
	return &ClusterMigrateSlots{}
}

// Init 初始化
func (job *ClusterMigrateSlots) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m

	err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("json.Unmarshal failed, err:%+v", err))
		return err
	}

	validate := validator.New()
	err = validate.Struct(job.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			job.runtime.Logger.Error("ClusterMigrateSlots Init params validate failed,err:%v,params:%+v", err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("ClusterMigrateSlots Init params validate failed,err:%v,params:%+v", err, job.params)
			return err
		}
	}
	if job.params.MigrateSpecifiedSlot && job.params.Slots == "" {

		err = fmt.Errorf("MigrateSpecifiedSlot=%v 和 slots:%s 指定迁移的slot不能为空",
			job.params.MigrateSpecifiedSlot, job.params.Slots)
		job.runtime.Logger.Error(err.Error())
		return err

	}

	job.runtime.Logger.Info("cluster migrate slots init success")

	return nil

}

// Name 原子任务名
func (job *ClusterMigrateSlots) Name() string {
	return "redis_migrate_slots"

}

// Retry 重试次数
func (job *ClusterMigrateSlots) Retry() uint {
	return 2
}

// Rollback rollback
func (job *ClusterMigrateSlots) Rollback() error {
	return nil

}

// Run 执行逻辑
// 扩容/缩容->本质上都是slot的再分配。 唯一区别是缩容可以指定删除的node
// 1、先计算出迁移后节点需要拥有的slot数，分段
// 2、统计当前节点拥有slot情况，分段统计、按段group、按量order
// 3、计算段与节点的对应关系
// 4、生成迁移计划，开始迁移
func (job *ClusterMigrateSlots) Run() error {
	if err := job.PreCheck(); err != nil {
		return err
	}
	if job.params.SrcNode.TendisType == consts.TendisTypeTendisplusInsance {
		// tendisplus迁移前设置这个参数，避免发生slave漂移情况
		job.TendisplusConfigSetParams("slave-reconf-enabled", "no")
		// 迁移前统一处理这个参数为10M,控制搬迁速度，避免速度过快造成影响，
		job.TendisplusConfigSetParams("cluster-migration-rate-limit", "10")
		defer job.TendisplusConfigSetParams("slave-reconf-enabled", "yes")

	}

	// 如果指定迁移slot,则跳过计算步骤
	if job.params.MigrateSpecifiedSlot {
		slots, _, _, _, err := myredis.DecodeSlotsFromStr(job.params.Slots, " ")
		if err != nil {
			job.Err = err
			return job.Err
		}
		if len(slots) == 0 {
			job.Err = fmt.Errorf("MigrateSpecifiedSlot=%v 和 slots:%s 指定迁移的slot不能为空",
				job.params.MigrateSpecifiedSlot, job.params.Slots)
			job.runtime.Logger.Error(job.Err.Error())
			return job.Err
		}
		job.MigrateSpecificSlots(job.srcNodeAddr(), job.dstNodeAddr(), slots, 20*time.Minute, 0)
		if job.Err != nil {
			return job.Err
		}
	} else {
		// RedisCluster 和 TendisPlus 使用不同的迁移规划策略
		if job.isRedisInstance() {
			err := job.redisClusterRebalanceSlot()
			if err != nil {
				job.Err = err
				return job.Err
			}
		} else {
			err := job.ReBalanceSlot()
			if err != nil {
				job.Err = err
				return job.Err
			}
		}
	}
	return nil
}

// srcNodeAddr 源节点地址
func (job *ClusterMigrateSlots) srcNodeAddr() string {
	return job.params.SrcNode.IP + ":" + strconv.Itoa(job.params.SrcNode.Port)
}

// dstNodeAddr 目标节点地址
func (job *ClusterMigrateSlots) dstNodeAddr() string {
	return job.params.DstNode.IP + ":" + strconv.Itoa(job.params.DstNode.Port)
}

// dstClusterMeetSrc 新建节点加入源集群
func (job *ClusterMigrateSlots) dstClusterMeetSrc() {
	var err error
	nodePasswordOnMachine, err := myredis.GetRedisPasswdFromConfFile(job.params.SrcNode.Port)
	if err != nil {
		job.Err = fmt.Errorf("SrcNode GetPassword GetPasswordFromLocalConfFile filed: %+v", err)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}

	// 增加验证密码一样
	if job.params.SrcNode.Password != nodePasswordOnMachine {
		job.Err = fmt.Errorf("SrcNode password != nodePasswordOnMachine: SrcNodePassword is %s nodePasswordOnMachine is %s",
			job.params.SrcNode.Password, nodePasswordOnMachine)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}

	// 增加验证密码一样
	if job.params.SrcNode.Password != job.params.DstNode.Password {
		job.Err = fmt.Errorf("SrcNode password != DstNode password: SrcNodePassword is %s DstNodePassword is %s",
			job.params.SrcNode.Password, job.params.DstNode.Password)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}

	job.runtime.Logger.Info("dstClusterMeetSrc : src password = dst password ")
	// SrcNode所属的原集群状态需要是ok， DstNode所属的新增节点集群状态是fail，且cluster_slots_assigend 是0
	// 以上两个状态是为了防止ip port 搞错，2个正常的集群meet到一起，这样会导致集群混乱
	srcStatusIsOk, _, err := job.clusterState(job.params.SrcNode.redisCli)
	if err != nil {
		job.Err = err
		job.runtime.Logger.Error(err.Error())
	}
	if !srcStatusIsOk {
		job.Err = fmt.Errorf("redisCluster:%s cluster_state not ok,please check !!! redisCluster", job.srcNodeAddr())
		job.runtime.Logger.Error(job.Err.Error())
		return
	}

	// DstNode所属的新增节点集群状态是fail，且cluster_slots_assigend 是0
	dstStateIsfaile, slotsAssigend, err := job.clusterState(job.params.DstNode.redisCli)
	if err != nil {
		job.Err = err
		job.runtime.Logger.Error(err.Error())
	}
	if dstStateIsfaile || slotsAssigend != 0 {
		job.Err = fmt.Errorf("redisCluster:%s cluster_state not fail or slotsAssigend !=0 please check !!!redisCluster ",
			job.dstNodeAddr())
		job.runtime.Logger.Error(job.Err.Error())
		return
	}
	// cluster meet 新节点加入集群
	_, err = job.params.SrcNode.redisCli.ClusterMeet(job.params.DstNode.IP, strconv.Itoa(job.params.DstNode.Port))
	if err != nil {
		job.Err = err
		return
	}
	// 这里 cluster meet 需要点时间，防止后续获取GetClusterNodes信息不全
	time.Sleep(10 * time.Second)
	job.runtime.Logger.Info("dstClusterMeetSrc  success ")

}

// clusterState 集群状态信息
func (job *ClusterMigrateSlots) clusterState(redisCli *myredis.RedisClient) (state bool,
	slotsAssigend int, err error) {
	clusterInfo, err := redisCli.ClusterInfo()
	if err != nil {
		err = fmt.Errorf("get cluster info fail:%v", err)
		return false, 0, err
	}
	if clusterInfo.ClusterState == consts.ClusterStateOK && clusterInfo.ClusterSlotsAssigned == consts.TotalSlots {
		return true, consts.TotalSlots, nil
	} else if clusterInfo.ClusterState == consts.ClusterStateFail && clusterInfo.ClusterSlotsAssigned == 0 {
		return false, 0, nil
	}
	err = fmt.Errorf("get cluster info fail")
	return false, 0, err
}

// checkNodeInfo 验证节点相关信息
func (job *ClusterMigrateSlots) checkNodeInfo() {
	// 获取源节点连接&信息
	job.params.SrcNode.redisCli, job.Err = myredis.NewRedisClient(job.srcNodeAddr(),
		job.params.SrcNode.Password, 0, consts.TendisTypeRedisInstance)
	if job.Err != nil {
		job.Err = fmt.Errorf("checkNodeInfo src NewRedisClient Err:%v", job.Err)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}

	job.params.SrcNode.TendisType, job.Err = job.params.SrcNode.redisCli.GetTendisType()
	if job.Err != nil {
		job.Err = fmt.Errorf("checkNodeInfo src GetTendisType Err:%v", job.Err)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}
	job.params.SrcNode.Role, job.Err = job.params.SrcNode.redisCli.GetRole()

	if job.Err != nil {
		job.Err = fmt.Errorf("checkNodeInfo src GetRole Err:%v", job.Err)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}

	job.runtime.Logger.Info("checkNodeInfo SrcNode GetTendisType:%s  success ", job.params.SrcNode.TendisType)

	// 获取目标节点连接&信息
	job.params.DstNode.redisCli, job.Err = myredis.NewRedisClient(job.dstNodeAddr(),
		job.params.DstNode.Password, 0, consts.TendisTypeRedisInstance)
	if job.Err != nil {
		job.Err = fmt.Errorf("checkNodeInfo DstNode NewRedisClient Err:%v", job.Err)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}

	job.params.DstNode.TendisType, job.Err = job.params.DstNode.redisCli.GetTendisType()
	if job.Err != nil {
		job.Err = fmt.Errorf("checkNodeInfo DstNode GetTendisType Err:%v", job.Err)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}
	job.runtime.Logger.Info("checkNodeInfo DstNode  GetTendisType:%s  success ", job.params.DstNode.TendisType)

	job.params.DstNode.Role, job.Err = job.params.DstNode.redisCli.GetRole()
	if job.Err != nil {
		job.Err = fmt.Errorf("checkNodeInfo dst GetRole Err:%v", job.Err)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}

	// 源节点和目标节点必须是master,因为迁移指定slot时（解决热点key），需要在master上执行
	if job.params.SrcNode.Role != consts.RedisMasterRole || job.params.DstNode.Role != consts.RedisMasterRole {
		job.Err = fmt.Errorf("node role != master ,please check ! srcNodeRole is %s,dstNodeRole is %s",
			job.params.SrcNode.Role, job.params.DstNode.Role)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}

	// 源端和目标端的类型必须一样, 并且是tendisplus或者rediscluster
	if job.params.SrcNode.TendisType != job.params.DstNode.TendisType {
		job.Err = fmt.Errorf("srcNode tendisType != DstNode tendisType ,please check ! srcNodeTendisType is %s"+
			" dsrNodeTendisType is %s", job.params.SrcNode.TendisType, job.params.DstNode.TendisType)
		job.runtime.Logger.Error(job.Err.Error())
	}
	if job.params.SrcNode.TendisType != consts.TendisTypeTendisplusInsance && job.params.SrcNode.TendisType !=
		consts.TendisTypeRedisInstance {
		job.Err = fmt.Errorf("node tendisType is %s!=(TendisplusInstance,TendisTypeRedisInstance),please check",
			job.params.SrcNode.TendisType)
		job.runtime.Logger.Error(job.Err.Error())
	}

	// 如果是rediscluster，需要检查版本>=6
	if job.isRedisInstance() {
		srcVersion, err := job.params.SrcNode.redisCli.GetTendisVersion()
		if err != nil {
			job.Err = fmt.Errorf("srcNode get version Err:%v", err)
			job.runtime.Logger.Error(job.Err.Error())
			return
		}
		_ok, _ := util.IsVersionGe(srcVersion, "6")
		if !_ok {
			job.Err = fmt.Errorf("rediscluster srcNode version < 6")
			job.runtime.Logger.Error(job.Err.Error())
			return
		}
	}

	clusterEnable, err := job.params.SrcNode.redisCli.IsClusterEnabled()
	if err != nil {
		job.Err = fmt.Errorf("srcNode Info get cluster enable Err:%v", err)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}
	if !clusterEnable {
		job.Err = fmt.Errorf("src cluster enable is false ,please check ")
		job.runtime.Logger.Error(job.Err.Error())
	}
	job.runtime.Logger.Info("checkNodeInfo tendisType success: DstNode tendisType %s",
		job.params.DstNode.TendisType)

	return
}

// ParallelMigrateSpecificSlots 并发执行slot迁移任务
func (job *ClusterMigrateSlots) ParallelMigrateSpecificSlots(migrateList []MigrateSomeSlots) error {
	// rediscluster 不允许并发迁移slot，会报：Please fix your cluster problems before resharding
	// 所以如果是rediscluster, 则串行执行
	if job.isRedisInstance() {
		job.runtime.Logger.Info("[rediscluster] serial migrate: total tasks=%d", len(migrateList))
		errList := []string{}
		totalMigrated := 0
		for i, item := range migrateList {
			count := item.MigrateCount
			if count == 0 {
				count = len(item.MigrateSlots)
			}
			job.runtime.Logger.Info("[rediscluster] task %d/%d: %s => %s, slotsCount:%d (reshard by count)",
				i+1, len(migrateList), item.SrcAddr, item.DstAddr, count)

			job.MigrateSpecificSlots(item.SrcAddr, item.DstAddr, item.MigrateSlots, 48*time.Hour, item.MigrateCount)
			if job.Err != nil {
				err := fmt.Errorf("srcAddr:%s => dstAddr:%s slotsCount:%d fail: %v",
					item.SrcAddr, item.DstAddr, count, job.Err)
				job.runtime.Logger.Error(err.Error())

				errList = append(errList, err.Error())
				job.Err = nil
				continue
			}

			totalMigrated += count
			job.runtime.Logger.Info("[rediscluster] task %d/%d: %s => %s, slotsCount:%d success",
				i+1, len(migrateList), item.SrcAddr, item.DstAddr, count)
		}

		job.runtime.Logger.Info("[rediscluster] serial migrate done: totalMigrated=%d, failed=%d",
			totalMigrated, len(errList))

		if len(errList) > 0 {
			return errors.New(strings.Join(errList, ";"))
		}
		return nil
	}

	// ========== TendisPlus 并发迁移 ==========
	// TODO: 优化点：在迁移开始之前对所有节点做一次cluster setslot clean操作
	// 不做并发限制，所有任务同时发起，谁抢到节点锁谁先执行
	job.runtime.Logger.Info("tendisplus parallel migrate: total tasks=%d, all tasks launched concurrently", len(migrateList))

	// 节点锁：确保同一节点同时只执行一个迁移任务
	nodeBusy := make(map[string]*sync.Mutex)
	nodeBusyLock := sync.Mutex{}
	for _, item := range migrateList {
		if _, ok := nodeBusy[item.SrcAddr]; !ok {
			nodeBusy[item.SrcAddr] = &sync.Mutex{}
		}
		if _, ok := nodeBusy[item.DstAddr]; !ok {
			nodeBusy[item.DstAddr] = &sync.Mutex{}
		}
	}

	// 结果收集
	retChan := make(chan MigrateSomeSlots, len(migrateList))
	wg := sync.WaitGroup{}

	// 正在执行的任务：拿到锁后加入，释放锁后移除
	runningTasks := make(map[int]MigrateSomeSlots)
	runningTasksLock := sync.Mutex{}

	// 监控协程：每分钟打印正在执行的任务
	// 注意：monitor 使用独立的 monitorWg，不与 worker 的 wg 混用，避免死锁
	monitorDone := make(chan struct{})
	monitorWg := sync.WaitGroup{}
	monitorWg.Add(1)
	go func() {
		defer monitorWg.Done()
		ticker := time.NewTicker(60 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				runningTasksLock.Lock()
				if len(runningTasks) == 0 {
					runningTasksLock.Unlock()
					continue
				}
				job.runtime.Logger.Info("===== 迁移进度监控: 正在执行 %d 个任务 =====", len(runningTasks))
				for idx, t := range runningTasks {
					job.runtime.Logger.Info("  running task %d: %s => %s, slotsCount:%d",
						idx, t.SrcAddr, t.DstAddr, len(t.MigrateSlots))
				}
				runningTasksLock.Unlock()
			case <-monitorDone:
				return
			}
		}
	}()

	// 所有任务同时发起，每个任务独立一个 goroutine
	for i, task := range migrateList {
		wg.Add(1)
		go func(task MigrateSomeSlots, idx int) {
			defer wg.Done()

			// 随机等待 10-60 秒，避免所有任务同时发起造成竞争
			time.Sleep(time.Duration(10+rand.Intn(51)) * time.Second)

			srcAddr := task.SrcAddr
			dstAddr := task.DstAddr

			// 按地址排序加锁，避免死锁
			var first, second string
			if srcAddr < dstAddr {
				first, second = srcAddr, dstAddr
			} else {
				first, second = dstAddr, srcAddr
			}

			nodeBusyLock.Lock()
			mutex1 := nodeBusy[first]
			mutex2 := nodeBusy[second]
			nodeBusyLock.Unlock()

			// 使用 tryLock 策略获取两把锁，避免锁链式阻塞：
			// 如果拿不到第二把锁，释放第一把锁，随机等待后重试
			// 这样不共享节点的任务（如 A→D 和 B→C）不会互相阻塞
			const maxTryLockAttempts = 300
			acquiredLocks := false
			for attempt := 0; attempt < maxTryLockAttempts; attempt++ {
				locked1 := mutex1.TryLock()
				if !locked1 {
					job.runtime.Logger.Info("task %d: tryLock first %s failed, retry %d", idx, first, attempt+1)
					time.Sleep(time.Duration(60+rand.Intn(19)) * time.Second)
					continue
				}
				job.runtime.Logger.Info("task %d: tryLock first %s success", idx, first)

				locked2 := mutex2.TryLock()
				if !locked2 {
					// 释放第一把锁，避免阻塞其他只需要 first 节点的任务
					mutex1.Unlock()
					job.runtime.Logger.Info("task %d: tryLock second %s failed, released first lock %s, retry %d",
						idx, second, first, attempt+1)
					time.Sleep(time.Duration(60+rand.Intn(19)) * time.Second)
					continue
				}
				job.runtime.Logger.Info("task %d: tryLock second %s success", idx, second)

				// 两把锁都获取成功
				acquiredLocks = true
				job.runtime.Logger.Info("task %d: got node lock (attempt %d), checking node status %s, %s",
					idx, attempt+1, srcAddr, dstAddr)
				break
			}

			// 兜底：tryLock 超过最大重试次数仍未获取到锁，回退到阻塞式加锁保证最终一定能执行
			if !acquiredLocks {
				job.runtime.Logger.Warn("task %d: tryLock exhausted %d attempts, fallback to blocking lock %s, %s",
					idx, maxTryLockAttempts, srcAddr, dstAddr)
				mutex1.Lock()
				mutex2.Lock()
			}

			// 等待 src 和 dst 节点上没有正在执行的迁移任务
			job.waitForNodeMigrationComplete(srcAddr, dstAddr)

			job.runtime.Logger.Info("task %d: nodes idle, start migrate %s => %s, slotsCount:%d",
				idx, srcAddr, dstAddr, len(task.MigrateSlots))

			// 记录为正在执行
			runningTasksLock.Lock()
			runningTasks[idx] = task
			runningTasksLock.Unlock()

			// 执行迁移
			job.MigrateSpecificSlots(srcAddr, dstAddr, task.MigrateSlots, 48*time.Hour, task.MigrateCount)
			if job.Err != nil {
				task.Err = job.Err
			}

			// 移除正在执行记录
			runningTasksLock.Lock()
			delete(runningTasks, idx)
			runningTasksLock.Unlock()

			// 释放锁
			mutex2.Unlock()
			mutex1.Unlock()

			job.runtime.Logger.Info("task %d: released lock, migrate done %s => %s", idx, srcAddr, dstAddr)
			retChan <- task
		}(task, i)
	}

	// 等待所有任务完成
	go func() {
		wg.Wait()
		close(monitorDone) // 先关闭 monitorDone，让 monitor 协程退出
		monitorWg.Wait()   // 等待 monitor 协程退出
		close(retChan)
	}()

	// 收集结果
	errList := []string{}
	for retItem := range retChan {
		if retItem.Err != nil {
			errList = append(errList, retItem.Err.Error())
			job.Err = fmt.Errorf("srcAddr:%s => dstAddr:%s slotsCount:%d fail",
				retItem.SrcAddr, retItem.DstAddr, len(retItem.MigrateSlots))
			job.runtime.Logger.Error(job.Err.Error())
			continue
		}
		msg := fmt.Sprintf("srcAddr:%s => dstAddr:%s slotsCount:%d success",
			retItem.SrcAddr, retItem.DstAddr, len(retItem.MigrateSlots))
		job.runtime.Logger.Info(msg)
	}

	if len(errList) > 0 {
		return errors.New(strings.Join(errList, ";"))
	}
	return nil
}

// waitForNodeMigrationComplete 等待 src 和 dst 节点上与当前迁移冲突的迁移任务完成
// 通过 GetClusterSetSlotInfo 检查节点的 importing/migrating 状态
// 改为只检查冲突：不共享节点的任务可以并行执行
func (job *ClusterMigrateSlots) waitForNodeMigrationComplete(srcAddr, dstAddr string) {
	maxWaitMinutes := 24 * 60 // 最长等待 24 小时
	waitInterval := 30 * time.Second

	for waitMinutes := 0; waitMinutes < maxWaitMinutes; waitMinutes++ {
		idle := true

		// 检查 src 节点：作为发送方，不能同时有多个迁移任务在发送（避免 TendisPlus 并发 bug）
		// 只要 src 节点有正在进行的 migrating/sending 就需要等待
		srcSlotInfo, srcErr := myredis.GetClusterSetSlotInfo(srcAddr, job.params.SrcNode.Password)
		if srcErr != nil {
			job.runtime.Logger.Warn("worker: failed to get src node %s slot info: %v", srcAddr, srcErr)
		} else if len(srcSlotInfo.MigratingSlotList) > 0 || srcSlotInfo.RunningSendTaskNum > 0 {
			job.runtime.Logger.Info("worker: src node %s has %d migrating slots, %d running sender tasks, waiting...",
				srcAddr, len(srcSlotInfo.MigratingSlotList), srcSlotInfo.RunningSendTaskNum)
			idle = false
		}

		// 检查 dst 节点：作为接收方，不能同时有多个迁移任务在接收（避免 TendisPlus 并发 bug）
		// 只要 dst 节点有正在进行的 importing/receiving 就需要等待
		dstSlotInfo, dstErr := myredis.GetClusterSetSlotInfo(dstAddr, job.params.SrcNode.Password)
		if dstErr != nil {
			job.runtime.Logger.Warn("worker: failed to get dst node %s slot info: %v", dstAddr, dstErr)
		} else if len(dstSlotInfo.ImportingSlotList) > 0 || dstSlotInfo.RunningRcvTaskNum > 0 {
			job.runtime.Logger.Info("worker: dst node %s has %d importing slots, %d running receiver tasks, waiting...",
				dstAddr, len(dstSlotInfo.ImportingSlotList), dstSlotInfo.RunningRcvTaskNum)
			idle = false
		}

		if idle {
			return
		}

		time.Sleep(waitInterval)
	}

	job.runtime.Logger.Warn("worker: waited %d minutes for nodes %s, %s to complete migration, proceeding anyway",
		maxWaitMinutes, srcAddr, dstAddr)
}

// MigrateSomeSlots ..(为并发迁移slot)
type MigrateSomeSlots struct {
	SrcAddr      string
	DstAddr      string
	MigrateSlots []int
	MigrateCount int // RedisCluster 场景下使用的按数量迁移数（reshard 不支持指定 slot）
	Err          error
}

// ReBalanceCluster 重新分配slots,
// 将slots尽量均匀的分配到新masterNode(没负责任何slot的master)上
// NOCC:golint/fnsize(设计如此)
func (job *ClusterMigrateSlots) ReBalanceCluster() error {
	job.runtime.Logger.Info("start ReBalanceCluster ...")
	defer job.runtime.Logger.Info("end ReBalanceCluster ...")

	var msg string
	_, err := job.params.SrcNode.redisCli.GetClusterNodes()
	if err != nil {
		return err
	}

	var expected int
	allRunningMasters, err := job.params.SrcNode.redisCli.GetRunningMasters()
	if err != nil {
		return err
	}
	allRunningCnt := len(allRunningMasters)

	expected = int(float64(consts.DefaultMaxSlots+1) / float64(allRunningCnt))

	for _, node01 := range allRunningMasters {
		nodeItem := node01
		nodeItem.SetBalance(len(nodeItem.Slots) - expected)
		nodeItem.SetEndSlotIdx(len(nodeItem.Slots))
	}
	totalBalance := 0
	runningMasterList := []*myredis.ClusterNodeData{}
	for _, node01 := range allRunningMasters {
		nodeItem := node01
		runningMasterList = append(runningMasterList, nodeItem)
		totalBalance += nodeItem.Balance()
	}

	// 先排序
	sort.Slice(runningMasterList, func(i, j int) bool {
		a := runningMasterList[i]
		b := runningMasterList[j]
		return a.Balance() < b.Balance()
	})

	// 逆序遍历，将余下的slot均摊到每个节点，减少需要变动的slot
	runningMasterIndex := allRunningCnt - 1
	for totalBalance > 0 && runningMasterIndex > 0 {
		nodeItem := runningMasterList[runningMasterIndex]
		// slot迁入节点，多迁入一个。 slot迁出节点，少迁出一个
		t01 := nodeItem.Balance() - 1
		nodeItem.SetBalance(t01)
		totalBalance -= 1
		runningMasterIndex -= 1
	}

	for _, node01 := range runningMasterList {
		nodeItem := node01
		msg = fmt.Sprintf("node=>%s balance:%d", nodeItem.Addr, nodeItem.Balance())
		job.runtime.Logger.Info(msg)
	}

	migrateTasks := []MigrateSomeSlots{}
	dstIdx := 0
	srcidx := len(runningMasterList) - 1

	for dstIdx < srcidx {
		dst := runningMasterList[dstIdx]
		src := runningMasterList[srcidx]

		var numSlots float64
		if math.Abs(float64(dst.Balance())) < math.Abs(float64(src.Balance())) {
			numSlots = math.Abs(float64(dst.Balance()))
		} else {
			numSlots = math.Abs(float64(src.Balance()))
		}
		if numSlots > 0 {
			msg = fmt.Sprintf("Moving %f slots from %s to %s,src.endSlotIdx:%d",
				numSlots, src.Addr, dst.Addr, src.EndSlotIdx())
			job.runtime.Logger.Info(msg)
			task01 := MigrateSomeSlots{
				SrcAddr:      src.Addr,
				DstAddr:      dst.Addr,
				MigrateSlots: []int{},
			}
			for idx01 := src.EndSlotIdx() - int(numSlots); idx01 < src.EndSlotIdx(); idx01++ {
				task01.MigrateSlots = append(task01.MigrateSlots, (src.Slots[idx01]))
			}
			src.SetEndSlotIdx(src.EndSlotIdx() - int(numSlots))
			migrateTasks = append(migrateTasks, task01)
		}
		dst.SetBalance(dst.Balance() + int(numSlots))
		src.SetBalance(src.Balance() - int(numSlots))
		msg = fmt.Sprintf("src:%s src.balance:%d,dst:%s dst.balance:%d",
			src.Addr, src.Balance(), dst.Addr, dst.Balance())
		job.runtime.Logger.Info(msg)
		if dst.Balance() == 0 {
			dstIdx++
		}
		if src.Balance() == 0 {
			srcidx--
		}
	}
	for _, task01 := range migrateTasks {
		msg := fmt.Sprintf("migrate plan=>srcNode:%s dstNode:%s slots:%v",
			task01.SrcAddr, task01.DstAddr, myredis.ConvertSlotToShellFormat(task01.MigrateSlots))
		job.runtime.Logger.Info(msg)
	}
	job.runtime.Logger.Info("migrateTasks:%+v", migrateTasks)
	job.runtime.Logger.Info("===== 迁移执行计划结束 =====")

	err = job.ParallelMigrateSpecificSlots(migrateTasks)
	if err != nil {
		return err
	}

	return nil
}

// MigrateSpecificSlots 迁移slots
// migrateCount: RedisCluster 场景下按数量迁移的 slot 数（reshard 不支持指定 slot），为 0 时使用 len(slots)
// NOCC:golint/fnsize(设计如此)
func (job *ClusterMigrateSlots) MigrateSpecificSlots(srcAddr,
	dstAddr string, slots []int, timeout time.Duration, migrateCount int) {
	job.runtime.Logger.Info("MigrateSpecificSlots start... srcAddr:%s desrAddr:%s"+
		" slots:%+v", srcAddr, dstAddr, myredis.ConvertSlotToShellFormat(slots))
	defer job.runtime.Logger.Info("MigrateSpecificSlots done... srcAddr:%s desrAddr:%s"+
		" slots:%+v", srcAddr, dstAddr, myredis.ConvertSlotToShellFormat(slots))

	// RedisCluster 场景下 reshard 按数量迁移，不需要指定具体 slot
	if len(slots) == 0 && migrateCount == 0 {
		job.Err = fmt.Errorf("MigrateSpecificSlots target slots count == %d and migrateCount == 0", len(slots))
		job.runtime.Logger.Error(job.Err.Error())
		return
	}

	if srcAddr == dstAddr {
		job.Err = fmt.Errorf("MigrateSpecificSlots slot srcAddr:%s = dstAddr:%s", srcAddr, dstAddr)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}

	// 获取tendisplus cluster nodes信息
	clusterNodes, err := job.params.SrcNode.redisCli.GetAddrMapToNodes()
	if err != nil {
		job.Err = err
		return
	}
	srcNodeInfo, ok := clusterNodes[srcAddr]
	if ok == false {
		job.Err = fmt.Errorf("MigrateSpecificSlots cluster not include the sre node,sreAddr:%s,clusterAddr:%s\n",
			srcAddr, job.params.SrcNode.redisCli.Addr)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}

	dstNodeInfo, ok := clusterNodes[dstAddr]
	if ok == false {
		job.Err = fmt.Errorf("MigrateSpecificSlots cluster not include the sre node,sreAddr:%s,clusterAddr:%s\n",
			srcAddr, job.params.SrcNode.redisCli.Addr)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}

	// 检查srcNode dstNode是否状态异常
	if len(srcNodeInfo.FailStatus) > 0 || srcNodeInfo.LinkState != consts.RedisLinkStateConnected {
		job.Err = fmt.Errorf(` src node is unnormal?
		srcAddr:%s,srcNodeFailStatus:%v,srcNodeLinkStatus:%s,`,
			srcAddr, srcNodeInfo.FailStatus, srcNodeInfo.LinkState)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}
	if len(dstNodeInfo.FailStatus) > 0 || dstNodeInfo.LinkState != consts.RedisLinkStateConnected {
		job.Err = fmt.Errorf(` dst node is unnormal?
		srcAddr:%s,dstNodeFailStatus:%v,dstNodeLinkStatus:%s,`,
			srcAddr, dstNodeInfo.FailStatus, dstNodeInfo.LinkState)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}
	// RedisCluster 按数量迁移时，不需要检查 slot 归属（reshard 会自动从 src 选择 slot）
	if !job.isRedisInstance() {
		allBelong, notBelongList, err := job.params.SrcNode.redisCli.IsSlotsBelongMaster(srcAddr, slots)
		if err != nil {
			job.Err = err
			job.runtime.Logger.Error(job.Err.Error())
			return
		}
		if allBelong == false {
			err = fmt.Errorf("MigrateSpecificSlots slots:%s not belong to srcNode:%s",
				myredis.ConvertSlotToShellFormat(notBelongList), srcAddr)
			job.Err = err
			job.runtime.Logger.Error(err.Error())
			return
		}
	}
	dstCli, err := myredis.NewRedisClient(dstAddr, job.params.SrcNode.Password, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		job.Err = err
		job.runtime.Logger.Error(job.Err.Error())
		return
	}
	defer dstCli.Close()

	srcCli, err := myredis.NewRedisClient(srcAddr, job.params.SrcNode.Password, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		job.Err = err
		job.runtime.Logger.Error(job.Err.Error())
		return
	}
	defer srcCli.Close()

	srcSlaves, err := srcCli.GetAllSlaveNodesByMasterAddr(srcAddr)
	if err != nil {
		job.Err = fmt.Errorf("srcAddr:%s get slave fail:%+v", srcAddr, err)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}
	dstSlaves, err := dstCli.GetAllSlaveNodesByMasterAddr(dstAddr)
	if err != nil {
		job.Err = fmt.Errorf("dstAddr:%s get slave fail:%+v", dstAddr, err)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}

	// 按照不同类型执行不同的slot搬迁步骤
	job.runtime.Logger.Info("Redis type is %s, begin slot migrate operate", job.params.SrcNode.TendisType)
	if job.isRedisInstance() {
		// 检查cli工具版本
		_, err = os.Stat(consts.RedisCliBin)
		if err != nil && os.IsNotExist(err) {
			err = fmt.Errorf("%s not exist", consts.RedisCliBin)
			job.runtime.Logger.Error(err.Error())
			return
		}
		if !util.IsCliSupportedClusterReshard(consts.RedisCliBin) {
			err = fmt.Errorf("%s not supported --cluster reshard", consts.RedisCliBin)
			job.runtime.Logger.Error(err.Error())
			return
		}
		// rediscluster集群架构没有封装迁移步骤，需要使用以下命令，为了简化行为，cluster先不支持指定slot迁移
		// 拆成多个命令执行
		needMigrateSlotCount := migrateCount
		if needMigrateSlotCount == 0 {
			needMigrateSlotCount = len(slots)
		}
		for needMigrateSlotCount > 0 {
			batchCount := needMigrateSlotCount
			if needMigrateSlotCount > 100 {
				needMigrateSlotCount -= 100
				batchCount = 100
			} else {
				needMigrateSlotCount = 0
			}
			migrateCmd := fmt.Sprintf("%s --no-raw --no-auth-warning -a %s --cluster reshard %s:%d "+
				"--cluster-from %s --cluster-to %s  --cluster-slots %d --cluster-yes > /dev/null",
				consts.RedisCliBin, job.params.SrcNode.Password, job.params.SrcNode.IP, job.params.SrcNode.Port,
				srcNodeInfo.NodeID, dstNodeInfo.NodeID, batchCount)
			migrateCmdLog := fmt.Sprintf("%s --no-raw --no-auth-warning -a %s --cluster reshard %s:%d "+
				"--cluster-from %s --cluster-to %s  --cluster-slots %d --cluster-yes ",
				consts.RedisCliBin, "xxxxxx", job.params.SrcNode.IP, job.params.SrcNode.Port,
				srcNodeInfo.NodeID, dstNodeInfo.NodeID, batchCount)

			job.runtime.Logger.Info("rediscluster slot migrate cmd is [%s]", migrateCmdLog)

			retStr, err := util.RunLocalCmdReplacePkey(
				"bash",
				[]string{"-c", migrateCmd},
				job.params.SrcNode.Password,
				"",
				nil,
				1*time.Hour)
			if err != nil {
				job.Err = err
				job.runtime.Logger.Error(fmt.Sprintf("rediscluster exec slot migrate cmd retStr:%v", retStr))
				job.runtime.Logger.Error(fmt.Sprintf("rediscluster exec slot migrate cmd error:%v", err))
				return
			}
			job.runtime.Logger.Info(fmt.Sprintf("rediscluster exec slot migrate cmd retStr:%v", retStr))
		}

	} else {
		cmd := []string{"cluster", "setslot", "importing", srcNodeInfo.NodeID}
		for _, slotItem := range slots {
			cmd = append(cmd, strconv.Itoa(slotItem))
		}
		var importRet interface{}
		deleteSlotErrRetryTimes := 1 // 发生slot in deleting错误,则重试,最多重试300次
		otherErrRetryTimes := 1
		for otherErrRetryTimes < 6 && deleteSlotErrRetryTimes < 301 {
			msg := fmt.Sprintf("MigrateSpecificSlots %d otherErrRetryTimes %d SlotErrRetryTimes,srcAddr:%s dstAddr:%s"+
				" migrateCommand:cluster setslot importing %s %s",
				otherErrRetryTimes, deleteSlotErrRetryTimes, srcAddr, dstAddr,
				srcNodeInfo.NodeID, myredis.ConvertSlotToShellFormat(slots))
			job.runtime.Logger.Info(msg)
			importRet, err = dstCli.DoCommand(cmd, 0)
			if err != nil && strings.Contains(err.Error(), "slot in deleting") == true {
				msg = fmt.Sprintf(
					`slot in deleting : MigrateSpecificSlots execute cluster setslot importing fail,err:%v,srcAddr:%s,dstAddr:%s,cmd:  cluster
			setslot importing %s %s`, err, srcAddr, dstAddr, srcNodeInfo.NodeID, myredis.ConvertSlotToShellFormat(slots))
				job.runtime.Logger.Warn(msg)
				time.Sleep(1 * time.Minute)
				deleteSlotErrRetryTimes++
				continue
			} else if err != nil && strings.Contains(err.Error(), "slot not empty") == true {
				dstCli.ClusterClear()
				srcCli.ClusterClear()
				msg = fmt.Sprintf(
					`slot not empty : MigrateSpecificSlots execute cluster setslot importing fail,err:%v,srcAddr:%s,dstAddr:%s,cmd: cluster
 			setslot importing %s %s`, err, srcAddr, dstAddr, srcNodeInfo.NodeID, myredis.ConvertSlotToShellFormat(slots))
				job.runtime.Logger.Warn(msg)
				time.Sleep(1 * time.Minute)
				deleteSlotErrRetryTimes++
				continue
			} else if err != nil {
				err = fmt.Errorf(
					`MigrateSpecificSlots execute cluster setslot importing fail,err:%v,srcAddr:%s,dstAddr:%s,cmd: cluster
 			setslot importing %s %s`, err, srcAddr, dstAddr, srcNodeInfo.NodeID, myredis.ConvertSlotToShellFormat(slots))
				job.runtime.Logger.Warn(err.Error())
				time.Sleep(1 * time.Minute)
				otherErrRetryTimes++
				continue
			}
			break

		}
		if (otherErrRetryTimes == 5 || deleteSlotErrRetryTimes == 30) && err != nil {
			job.Err = fmt.Errorf("otherErrRetryTimes is 5 and deleteSlotErrRetryTimes is 30 always failed:%v", err)
			job.runtime.Logger.Error(job.Err.Error())
			return
		}

		importingTaskID := importRet.(string)
		job.runtime.Logger.Info("importingTaskID %v:", importingTaskID)
		_, _, err = job.confirmMigrateSlotsStatus(srcNodeInfo, dstNodeInfo, importingTaskID, slots, timeout)
		if err != nil && err.Error() == "migrate fail" {
			// migrate fail,let's retry
			time.Sleep(2 * time.Minute) // 如果集群拓扑信息发生了变更,让信息充分广播
			job.Err = err
			err = job.retryMigrateSpecSlots(srcNodeInfo, dstNodeInfo, job.params.SrcNode.Password,
				importingTaskID, srcSlaves, dstSlaves, slots, timeout)
			if err != nil {
				job.Err = fmt.Errorf("retryMigrateSpecSlots fail: %v", err)
				job.runtime.Logger.Error(job.Err.Error())
			}
		}
	}
	return
}

// confirmMigrateSlotsStatus 在dstAddr上执行 cluster setslot info 确认slots是否迁移ok
func (job *ClusterMigrateSlots) confirmMigrateSlotsStatus(
	srcNodeInfo, dstNodeInfo *myredis.ClusterNodeData,
	taskID string, migrateSlots []int, timeout time.Duration) (mySuccImport, myFailImport []int, err error) {

	// rediscluster 直接返回，不支持cluster setslot 命令
	if job.isRedisInstance() {
		job.runtime.Logger.Info(" is redis cluster not exec cluster setslot info")
		return nil, nil, nil
	}
	mySuccImport = []int{}
	myFailImport = []int{}
	var importing, successImport, failImport, unknow []int
	timeLimit := int64(timeout.Seconds()) / 30

	for {
		time.Sleep(30 * time.Second) // 每30秒打印一次日志
		if timeLimit == 0 {
			break
		}
		dstSetSlotInfo, err := myredis.GetClusterSetSlotInfo(dstNodeInfo.Addr, job.params.SrcNode.Password)
		if err != nil {

			return mySuccImport, myFailImport, err
		}
		importing, successImport, failImport, unknow = dstSetSlotInfo.GetDstRedisSlotsStatus(migrateSlots)
		// 我们目的节点上,可能有多个迁移任务,我们只关心 当前迁移任务的slots情况
		mySuccImport = util.IntSliceInter(migrateSlots, successImport)
		myFailImport = util.IntSliceInter(migrateSlots, failImport)

		if len(importing) > 0 {
			// 等待所有importing结束,尽管正在迁移的slots不是我当前任务的slot,依然等待
			job.runtime.Logger.Info("confirmMigrateSlotsStatus there are some slots still importing on the dstNode"+
				"importingCount:%d srcNodeAddr:%s srcNodeID:%s dstNodeAddr:%s dstNodeID:%s importingTaskID:%s ",
				len(importing), srcNodeInfo.Addr, srcNodeInfo.NodeID, dstNodeInfo.Addr, dstNodeInfo.NodeID, taskID)
			timeLimit--
			continue
		} else if len(myFailImport) > 0 {
			job.runtime.Logger.Error("confirmMigrateSlotsStatus there are some slots migrating fail on the dstNode"+
				"failImportCount:%d srcNodeAddr:%s srcNodeID:%s dstNodeAddr:%s dstNodeID:%s failImportSlot:%v importingTaskID:%s ",
				len(myFailImport), srcNodeInfo.Addr, srcNodeInfo.NodeID, dstNodeInfo.Addr, dstNodeInfo.NodeID,
				myredis.ConvertSlotToStr(myFailImport), taskID)
			err = errors.New("migrate fail")
			return mySuccImport, myFailImport, err
		}
		job.runtime.Logger.Info("confirmMigrateSlotsStatus success "+
			"slots numbers:%d,srcNodeAddr:%s,dstNodeAddr:%s,dstNodeID:%s,slots:%s,importingTaskID:%s ,unknow:%d",
			len(successImport), srcNodeInfo.Addr, dstNodeInfo.Addr, dstNodeInfo.NodeID,
			myredis.ConvertSlotToStr(migrateSlots), taskID, len(unknow))
		break
	}
	return mySuccImport, myFailImport, nil

}

// retryMigrateSpecSlots TODO
// 1. 检查src master是否failover了? 如果发生了failover,找到new src master
// 2. 检查dst master是否failover了? 如果发生了failover,找到new dst master
// NOCC:golint/fnsize(设计如此)
func (job *ClusterMigrateSlots) retryMigrateSpecSlots(
	srcNodeInfo, dstNodeInfo *myredis.ClusterNodeData, passwd string, taskID string,
	srcSlaves, dstSlaves []*myredis.ClusterNodeData, slots []int, timeout time.Duration,
) (err error) {
	var msg string
	newSrcNode, srcFailovered, err := job.findNewMasterWhenFailover(srcNodeInfo, passwd, srcSlaves, slots)
	if err != nil {
		return err
	}
	newDstNode, dstFailovered, err := job.findNewMasterWhenFailover(dstNodeInfo, passwd, dstSlaves, slots)
	if err != nil {
		return err
	}

	newSrcCli, err := myredis.NewRedisClient(newSrcNode.Addr, passwd, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		return err
	}
	defer newSrcCli.Close()

	newDstCli, err := myredis.NewRedisClient(newDstNode.Addr, passwd, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		return err
	}
	defer newDstCli.Close()
	if srcFailovered == true {
		msg = fmt.Sprintf("migrate slots,srcNodeAddr:%s failovered,newSrcNode:%s", srcNodeInfo.Addr, newSrcNode.Addr)
		job.runtime.Logger.Info(msg)
	}
	if dstFailovered == true {
		msg = fmt.Sprintf("migrate slots,dstNodeAddr:%s failovered,newDstNode:%s", dstNodeInfo.Addr, newDstNode.Addr)
		job.runtime.Logger.Info(msg)
	}
	if srcFailovered == true || dstFailovered == true {
		// 如果发生了failover,重试迁移前,先做一些清理
		newSrcCli.ClusterClear()
		newDstCli.ClusterClear()
	}
	cmd := []interface{}{"cluster", "setslot", "restart", newSrcNode.NodeID}
	for _, slotItem := range slots {
		cmd = append(cmd, slotItem)
	}
	var importRet interface{}
	deleteSlotErrRetryTimes := 0 // 发生slot in deleting错误,则重试,最多重试300次(5小时)
	otherErrRetryTimes := 0
	for otherErrRetryTimes < 5 && deleteSlotErrRetryTimes < 300 {
		// 打印执行的迁移命令
		msg := fmt.Sprintf("retryMigrateSlots %d times,srcAddr:%s dstAddr:%s migrateCommand:cluster setslot restart %s %s",
			otherErrRetryTimes, newSrcNode.Addr, newDstNode.Addr, newSrcNode.NodeID, myredis.ConvertSlotToShellFormat(slots))
		job.runtime.Logger.Info(msg)

		importRet, err = newDstCli.InstanceClient.Do(context.TODO(), cmd...).Result()

		if err != nil && strings.Contains(err.Error(), "slot in deleting") == true {
			msg = fmt.Sprintf(
				`retryMigrateSlots execute cluster setslot restart fail,err:%v,srcAddr:%s,dstAddr:%s,
				cmd:cluster setslot restart %s %s,sleep 1min and retry`,
				err, newSrcNode.Addr, newDstNode.Addr, newSrcNode.NodeID, myredis.ConvertSlotToShellFormat(slots))
			job.runtime.Logger.Warn(msg)
			time.Sleep(1 * time.Minute)
			deleteSlotErrRetryTimes++
			continue
		} else if err != nil && strings.Contains(err.Error(), "slot not empty") == true {
			newSrcCli.ClusterClear()
			newDstCli.ClusterClear()
			msg = fmt.Sprintf(
				`retryMigrateSlots execute cluster setslot restart fail,err:%v,srcAddr:%s,dstAddr:%s,cmd:"+
				"cluster setslot restart %s %s,sleep 1min and retry`,
				err, newSrcNode.Addr, newDstNode.Addr, newSrcNode.NodeID, myredis.ConvertSlotToShellFormat(slots))
			job.runtime.Logger.Warn(msg)
			time.Sleep(1 * time.Minute)
			deleteSlotErrRetryTimes++
			continue
		} else if err != nil && strings.Contains(err.Error(), "json contain err") == true {
			newSrcCli.ClusterStopTaskID(taskID)
			newDstCli.ClusterStopTaskID(taskID)
			err = fmt.Errorf(
				`retryMigrateSlots execute cluster setslot restart fail,err:%v,srcAddr:%s,dstAddr:%s,cmd:"+
				"cluster setslot restart %s %s,sleep 1min and retry`,
				err, newSrcNode.Addr, newDstNode.Addr, newSrcNode.NodeID, myredis.ConvertSlotToShellFormat(slots))
			job.runtime.Logger.Warn(msg)
			time.Sleep(1 * time.Minute)
			deleteSlotErrRetryTimes++
			continue
		} else if err != nil {
			// network timeout,retry
			err = fmt.Errorf(`retryMigrateSlots execute cluster setslot restart fail,err:%v,
			srcAddr:%s,dstAddr:%s,cmd:cluster setslot restart %s %s`,
				err, newSrcNode.Addr, newDstNode.Addr, newSrcNode.NodeID, myredis.ConvertSlotToShellFormat(slots))
			job.runtime.Logger.Error(err.Error())
			time.Sleep(5 * time.Second)
			otherErrRetryTimes++
			continue
		}
		break
	}
	if (otherErrRetryTimes == 5 || deleteSlotErrRetryTimes == 300) && err != nil {
		job.runtime.Logger.Error(err.Error())
		return err
	}
	importingTaskID := importRet.(string)
	_, _, err = job.confirmMigrateSlotsStatus(newSrcNode, newDstNode, importingTaskID, slots, timeout)
	if err != nil {
		return err
	}
	return nil

}

// findNewMasterWhenFailover ..
// 检查old master是否failover了,如果failover了,尝试找到new master
// a. 检查,old master是否可连接
// - 不能连接代表 发生了 failover；从slaves中找new master;
// - 可连接，再检查old master的角色是否变成了slave，如果变成了slave,则old master的master就是new master;
// - 上面两种情况都必须保证new master至少和old master至少具有一个相同的slot
// - 如果old master可连接,且角色依然是master.则new master=old master;
// NOCC:golint/fnsize(设计如此)
func (job *ClusterMigrateSlots) findNewMasterWhenFailover(
	oldMaster *myredis.ClusterNodeData, passwd string, slaves []*myredis.ClusterNodeData, slots []int,
) (newMaster *myredis.ClusterNodeData, isFailovered bool, err error) {
	var msg string
	newMaserNode := oldMaster
	list01 := []string{}
	for _, srcSlave01 := range slaves {
		srcSlaveItem := srcSlave01
		addr := strings.Split(srcSlaveItem.Addr, ".")[0]
		list01 = append(list01, addr)
	}
	isFailovered = false
	srcCli, err := myredis.NewRedisClient(oldMaster.Addr, passwd, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		// src master disconnected
		msg = fmt.Sprintf(
			"oldMasterAddr:%s disconnected,maybe failover occured,now we find new master from it's slaves:%s",
			oldMaster.Addr, strings.Join(list01, ","))
		job.runtime.Logger.Warn(msg)
		isFailovered = true
		// find new src master from slaves
		var runningSlave01 *myredis.ClusterNodeData = nil
		for _, slave01 := range slaves {
			slaveItem := slave01
			if len(slaveItem.FailStatus) == 0 {
				runningSlave01 = slaveItem
				break
			}
		}
		if runningSlave01 == nil {
			err = fmt.Errorf("oldMasterAddr:%s disconnected and have no running slave,slaves:%s",
				oldMaster.Addr, strings.Join(list01, ","))
			job.runtime.Logger.Error(err.Error())
			return nil, isFailovered, err
		}

		runSlaveCli, err := myredis.NewRedisClient(runningSlave01.Addr, passwd, 0, consts.TendisTypeRedisInstance)
		if err != nil {
			return nil, isFailovered, err
		}
		_, err = runSlaveCli.GetClusterNodes()
		if err != nil {
			runSlaveCli.Close()
			return nil, isFailovered, err
		}
		// current running masters
		runningMasters, err := runSlaveCli.GetRunningMasters()
		if err != nil {
			runSlaveCli.Close()
			return nil, isFailovered, err
		}
		runSlaveCli.Close()
		for _, srcSlave01 := range slaves {
			srcSlaveItem := srcSlave01
			if _, ok := runningMasters[srcSlaveItem.Addr]; ok == true {
				newMaserNode = srcSlaveItem
				break
			}
		}
		// not find new src master
		if newMaserNode == oldMaster {
			err = fmt.Errorf("oldMasterAddr:%s disconnected and can't find new master from slaves:%s",
				oldMaster.Addr, strings.Join(list01, ","))
			job.runtime.Logger.Error(err.Error())
			return nil, isFailovered, err
		}
		interSlots := util.IntSliceInter(newMaserNode.Slots, slots)
		if len(interSlots) == 0 {
			// have no same slots;
			// There is reason to suspect that the new src master is not correct.
			err = fmt.Errorf(`
oldMasterAddr:%s disconnected and find a new master:%s,
but old master and new master do not have the same slots,
old master slots:%s, new master slots:%s`,
				oldMaster.Addr, newMaserNode.Addr, myredis.ConvertSlotToStr(slots),
				myredis.ConvertSlotToStr(newMaserNode.Slots))
			job.runtime.Logger.Error(err.Error())
			return nil, isFailovered, err
		}
	} else {
		defer srcCli.Close()
		selfNodeInfo, err := srcCli.GetMyself()
		if err != nil {
			return nil, isFailovered, err
		}
		if oldMaster.Role == "slave" {
			isFailovered = true
			msg = fmt.Sprintf(
				"oldMasterAddr:%s now is a slave,maybe failover occured,now we treat it's master as new master",
				oldMaster.Addr)
			job.runtime.Logger.Warn(msg)

			newMaserNode, err = srcCli.GetMasterNodeBySlaveAddr(selfNodeInfo.Addr)
			if err != nil {
				return nil, isFailovered, err
			}
			interSlots := util.IntSliceInter(newMaserNode.Slots, slots)
			if len(interSlots) == 0 {
				// have no same slots;
				// There is reason to suspect that the new src master is not correct.
				err = fmt.Errorf(`
oldMasterAddr:%s now is a slave and find a new master:%s,
but old master and new master do not have the same slots,
old master slots:%s, new master slots:%s`,
					oldMaster.Addr, newMaserNode.Addr, myredis.ConvertSlotToStr(slots), myredis.ConvertSlotToStr(newMaserNode.Slots))
				job.runtime.Logger.Error(err.Error())
				return nil, isFailovered, err
			}
		} else {
			// old master is connected and role is still master
			msg = fmt.Sprintf("oldMasterAddr:%s still  a master and is connected,not failover", oldMaster.Addr)
			job.runtime.Logger.Info(msg)

		}
	}
	return newMaserNode, isFailovered, nil
}

// MigrateSlotsFromToBeDelNode 将待删除Node上的slots 迁移到 剩余Node上
// NOCC:golint/fnsize(设计如此)
func (job *ClusterMigrateSlots) MigrateSlotsFromToBeDelNode(toBeDelNodesAddr []string) (err error) {
	var msg string
	msg = fmt.Sprintf("start migateSlotsFromToBeDeletedNodes toBeDelNodesAddr:%v", toBeDelNodesAddr)
	job.runtime.Logger.Info(msg)
	defer job.runtime.Logger.Info("end migateSlotsFromToBeDeletedNodes")

	_, err = job.params.SrcNode.redisCli.GetClusterNodes()
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return err
	}

	mastersWithSlot, err := job.params.SrcNode.redisCli.GetNodesByFunc(myredis.IsMasterWithSlot)
	if err != nil && util.IsNotFoundErr(err) {
		msg = fmt.Sprintf("cluster have no master with slots,no run migateSlotsFromToBeDeletedNodes")
		job.runtime.Logger.Warn(msg)
		return nil
	} else if err != nil {
		return err
	}

	// confirm cluster state ok
	clusterOK, _, err := job.clusterState(job.params.SrcNode.redisCli)
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return err
	}
	if clusterOK == false {
		err = fmt.Errorf("cluster_state is fail,addr:%s", job.srcNodeAddr())
		job.runtime.Logger.Error(err.Error())
		return err
	}

	// get to be deleted masters with slots
	toBeDelMastersWithSlots := []*myredis.ClusterNodeData{}
	toBeDelMastersWithSlotAddrs := []string{}
	toBeDelNodeMap := make(map[string]bool)
	for _, addr01 := range toBeDelNodesAddr {
		toBeDelNodeMap[addr01] = true
		if node01, ok := mastersWithSlot[addr01]; ok == true {
			node02 := *node01 // copy
			toBeDelMastersWithSlots = append(toBeDelMastersWithSlots, &node02)
			toBeDelMastersWithSlotAddrs = append(toBeDelMastersWithSlotAddrs, node02.Addr)
		}
	}
	if len(toBeDelMastersWithSlots) == 0 {
		msg = fmt.Sprintf("no need migate slots,no master with slots in the toBeDeletedNodes:%v", toBeDelNodesAddr)
		job.runtime.Logger.Info(msg)
		return nil
	}

	// get to be left masters (with or without slots)
	masterNodes, _ := job.params.SrcNode.redisCli.GetNodesByFunc(myredis.IsRunningMaster)
	leftMasters := []*myredis.ClusterNodeData{}
	for addr01, node01 := range masterNodes {
		node02 := *node01 // copy
		if _, ok := toBeDelNodeMap[addr01]; ok == false {
			leftMasters = append(leftMasters, &node02)
		}
	}
	if len(leftMasters) == 0 {
		msg = fmt.Sprintf("have no leftMasters,no need migate slots,toBeDeletedNodes:%v", toBeDelNodesAddr)
		job.runtime.Logger.Info(msg)
		return
	}

	leftMasterCnt := len(leftMasters)
	expectedSlotNum := int(math.Ceil(float64(consts.DefaultMaxSlots+1) / float64(leftMasterCnt)))
	type migrationInfo struct {
		FromAddr string
		ToAddr   string
	}
	migrateMap := make(map[migrationInfo][]int)

	for _, delNode01 := range toBeDelMastersWithSlots {
		delNodeItem := delNode01
		for _, slot01 := range delNodeItem.Slots {
			// loop all slots on toBeDeleltedNodes
			for _, leftNode01 := range leftMasters {
				leftNodeItem := leftNode01
				if len(leftNodeItem.Slots) >= expectedSlotNum {
					continue
				}
				leftNodeItem.Slots = append(leftNodeItem.Slots, slot01)
				migrate01 := migrationInfo{FromAddr: delNodeItem.Addr, ToAddr: leftNodeItem.Addr}
				migrateMap[migrate01] = append(migrateMap[migrate01], slot01)
				break // next slot
			}
		}
	}
	migrateTasks := []MigrateSomeSlots{}
	for migrate01, slots := range migrateMap {
		sort.Slice(slots, func(i, j int) bool {
			return slots[i] < slots[j]
		})

		migrateTasks = append(migrateTasks, MigrateSomeSlots{
			SrcAddr:      migrate01.FromAddr,
			DstAddr:      migrate01.ToAddr,
			MigrateSlots: slots,
		})
	}

	for _, task01 := range migrateTasks {
		msg = fmt.Sprintf("scale down migrate plan=>srcNode:%s dstNode:%s slots:%s",
			task01.SrcAddr, task01.DstAddr, myredis.ConvertSlotToShellFormat(task01.MigrateSlots))
		job.runtime.Logger.Info(msg)
	}

	// 获取 slot全部迁移主从对的NodeID,用于forget: 执行迁移slots前获取，因为迁移全部slot后，slvae 会replicate到其他节点
	toBeDelAllNodeNodeID := []string{}
	toBeDelAllNodeMap := make(map[string]bool)
	for _, addr01 := range toBeDelNodesAddr {
		toBeDelAllNodeMap[addr01] = true
		// TODO 这个地方只会获取拥有slot的node。 如果存在需要下架，并且没有slot的节点，不会去forget
		if node01, ok := mastersWithSlot[addr01]; ok == true {
			node02 := *node01
			dstCli01, err := myredis.NewRedisClient(addr01, job.params.DstNode.Password, 0, consts.TendisTypeRedisInstance)
			if err != nil {
				job.runtime.Logger.Error(err.Error())
				return err
			}
			defer dstCli01.Close()
			dstSlaves, err := dstCli01.GetAllSlaveNodesByMasterAddr(addr01)
			if err != nil {
				job.Err = fmt.Errorf("dstAddr:%s get slave fail:%+v", addr01, err)
				job.runtime.Logger.Error(job.Err.Error())
				return job.Err
			}
			toBeDelAllNodeNodeID = append(toBeDelAllNodeNodeID, node02.NodeID)
			for _, srcSlave01 := range dstSlaves {
				srcSlaveItem := srcSlave01
				toBeDelAllNodeNodeID = append(toBeDelAllNodeNodeID, srcSlaveItem.NodeID)
				toBeDelAllNodeMap[srcSlave01.Addr] = true
			}

		}
	}
	job.runtime.Logger.Info("get toBeDelAllNodeNodeID success :%v", toBeDelAllNodeNodeID)
	allNodes, _ := job.params.SrcNode.redisCli.GetAddrMapToNodes()
	if err != nil {
		return
	}

	err = job.ParallelMigrateSpecificSlots(migrateTasks)
	if err != nil {
		return err
	}

	// 如果任何待删除master节点正在migrate slots,则等待1分钟后重试,最长300分钟
	timeLimit := 0
	for {
		isToBeDelMasterMigrating, migratingAddr, migratingSlots, err1 := job.areTenplusMigrating(toBeDelMastersWithSlotAddrs)
		if err1 != nil {
			return err1
		}
		if isToBeDelMasterMigrating == true {
			time.Sleep(1 * time.Minute)
			// 直到"所有待删除master节点没有migrate slots",再继续搬迁slot;
			msg = fmt.Sprintf("MigrateSlotsFromToBeDelNode toBeDeletedMaster:%s migrating slots count:%d",
				migratingAddr, len(migratingSlots))
			job.runtime.Logger.Info(msg)
			timeLimit++
			continue
		}
		break

	}
	if timeLimit == 300 {
		err = fmt.Errorf("MigrateSlotsFromToBeDelNode  migrating 300 minute,please check")
		job.runtime.Logger.Error(err.Error())
		return err
	}

	// make sure that toBeDeletedNodes have no slots
	_, err = job.params.SrcNode.redisCli.GetClusterNodes()
	if err != nil {
		return err
	}
	var filterToBeDelNodeFunc = func(n *myredis.ClusterNodeData) bool {
		if _, ok := toBeDelNodeMap[n.Addr]; ok == true {
			return true
		}
		return false
	}
	toBeDeletedNodes, err := job.params.SrcNode.redisCli.GetNodesByFunc(filterToBeDelNodeFunc)
	if err != nil {
		return err
	}
	var errList []string
	for _, node01 := range toBeDeletedNodes {
		if myredis.IsRunningMaster(node01) == true && len(node01.Slots) > 0 {
			errList = append(errList, fmt.Sprintf("%s still have %d slots:%s",
				node01.Addr, len(node01.Slots),
				myredis.ConvertSlotToShellFormat(node01.Slots)))
		}
	}
	if len(errList) > 0 {
		err = fmt.Errorf("%s", strings.Join(errList, "\n"))
		job.runtime.Logger.Error(err.Error())
		return err
	}

	// 获取需要下线主从对 以外的nodes
	leftNodesAddr := []string{}
	for addr01 := range allNodes {
		if _, ok := toBeDelAllNodeMap[addr01]; ok == false {
			leftNodesAddr = append(leftNodesAddr, addr01)
		}
	}
	var errForgetList []string
	for _, addr03 := range leftNodesAddr {
		addrCli, err := myredis.NewRedisClient(addr03, job.params.SrcNode.Password, 0, consts.TendisTypeRedisInstance)
		if err != nil {
			job.runtime.Logger.Error(err.Error())
			return err
		}
		defer addrCli.Close()
		for _, nodeID := range toBeDelAllNodeNodeID {
			err := addrCli.ClusterForget(nodeID)
			if err != nil {
				errForgetList = append(errForgetList, fmt.Sprintf("node:%s cluster forget %s failed", addr03, nodeID))
				job.runtime.Logger.Error(err.Error())
			}
			job.runtime.Logger.Info("node:%s forget node:%s success.", addr03, nodeID)
		}

	}
	job.runtime.Logger.Info("get leftNodesAddr success :%v", leftNodesAddr)
	if len(errForgetList) > 0 {
		err = fmt.Errorf("%s", strings.Join(errForgetList, "\n"))
		job.runtime.Logger.Error(err.Error())
		return err
	}
	job.runtime.Logger.Info("cluster forget success")
	return nil
}

// areTenplusMigrating tendisplus 节点是否正在migrating slots
func (job *ClusterMigrateSlots) areTenplusMigrating(tenplusAddrs []string) (
	migratingOrNot bool, migratingAddr string, migatingSlots []int, err error,
) {

	// rediscluster 直接返回，不支持cluster setslot 命令
	if job.isRedisInstance() {
		job.runtime.Logger.Info(" is redis cluster not exec cluster setslot info")
		return
	}

	if len(tenplusAddrs) == 0 {
		return
	}

	var srcSetSlotInfo *myredis.ClusterSetSlotInfo = nil
	for _, addr01 := range tenplusAddrs {
		addr01 = strings.TrimSpace(addr01)
		if addr01 == "" {
			continue
		}
		srcSetSlotInfo, err = myredis.GetClusterSetSlotInfo(addr01, job.params.SrcNode.Password)
		if err != nil {
			job.runtime.Logger.Error(err.Error())
			return
		}
		if len(srcSetSlotInfo.MigratingSlotList) > 0 {
			return true, addr01, srcSetSlotInfo.MigratingSlotList, nil
		}
	}
	return
}

// TendisplusConfigSetParams 在迁移前后需要设置plus参数，避免触发特殊逻辑
func (job *ClusterMigrateSlots) TendisplusConfigSetParams(configName, configValue string) {
	// 获取源节点连接&信息
	job.params.SrcNode.redisCli, job.Err = myredis.NewRedisClient(job.srcNodeAddr(),
		job.params.SrcNode.Password, 0, consts.TendisTypeRedisInstance)
	if job.Err != nil {
		job.Err = fmt.Errorf("checkNodeInfo src NewRedisClient Err:%v", job.Err)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}

	job.params.SrcNode.TendisType, job.Err = job.params.SrcNode.redisCli.GetTendisType()
	if job.Err != nil {
		job.Err = fmt.Errorf("checkNodeInfo src GetTendisType Err:%v", job.Err)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}
	// 由于迁移slot逻辑不一样，所以只有tendisplus需要处理参数
	if job.params.SrcNode.TendisType != consts.TendisTypeTendisplusInsance || job.params.DstNode.TendisType !=
		consts.TendisTypeTendisplusInsance {
		msg := fmt.Sprintf("node tendisType != TendisplusInstance ,please check ! srcNodeTendisType is %s"+
			" dsrNodeTendisType is %s", job.params.SrcNode.TendisType, job.params.DstNode.TendisType)
		job.runtime.Logger.Info(msg)
		return
	}

	job.runtime.Logger.Info("checkNodeInfo tendisType success: DstNode tendisType %s",
		job.params.DstNode.TendisType)

	// tendisplus 所有nodes config 设置参数
	allNodes, err := job.params.SrcNode.redisCli.GetClusterNodes()
	if err != nil {
		job.runtime.Logger.Warn(fmt.Sprintf("get cluster nodes error:%s", err.Error()))
		return
	}

	for _, node := range allNodes {
		nodeCli, err := myredis.NewRedisClient(node.Addr,
			job.params.SrcNode.Password, 0, consts.TendisTypeRedisInstance)
		if err != nil {
			job.runtime.Logger.Warn(fmt.Sprintf("get %s redis cli error:%s", node.Addr, err.Error()))
			continue
		}

		ret, err := nodeCli.ConfigSet(configName, configValue)
		if err != nil {
			job.runtime.Logger.Warn(fmt.Sprintf("node %s config set[%s:%s] error:%s, ret:%s",
				node.Addr, configName, configValue, err.Error(), ret))
		}
		nodeCli.Close()

		job.runtime.Logger.Info("node %s config set[%s:%s] success ",
			node.Addr, configName, configValue)
	}

	return
}

// 是否是rediscluster协议的集群
func (job *ClusterMigrateSlots) isRedisInstance() bool {
	return job.params.SrcNode.TendisType == consts.TendisTypeRedisInstance
}

// GetMigrateNodes 获取保留节点、删除节点
func (job *ClusterMigrateSlots) GetMigrateNodes() ([]string, []string, error) {
	// 当前状态下的所有节点
	var runningMasterNodesAddr []string
	// 需要forget的节点
	var toBeDelNodesAddr []string
	// 最终存在的节点
	var finalNodesAddr []string

	runningMasterNodes, err := job.params.SrcNode.redisCli.GetRunningMasters()
	if err != nil {
		return finalNodesAddr, toBeDelNodesAddr, err
	}
	for nodeInfo := range runningMasterNodes {
		runningMasterNodesAddr = append(runningMasterNodesAddr, runningMasterNodes[nodeInfo].IP+":"+strconv.Itoa(runningMasterNodes[nodeInfo].Port))
	}
	job.runtime.Logger.Info("get running master:%+v", runningMasterNodesAddr)

	// 缩容
	if job.params.IsDeleteNode {
		// 指定了要forget的节点
		if len(job.params.ToBeDelNodesAddr) != 0 {
			toBeDelNodesAddr = job.params.ToBeDelNodesAddr
		} else {
			toBeDelNodesAddr = append(toBeDelNodesAddr, job.dstNodeAddr())
			job.params.ToBeDelNodesAddr = toBeDelNodesAddr
		}
	}
	for _, addr := range runningMasterNodesAddr {
		isDel := false
		for _, delAddr := range toBeDelNodesAddr {
			if addr == delAddr {
				isDel = true
				break
			}
		}
		if !isDel {
			finalNodesAddr = append(finalNodesAddr, addr)
		}
	}
	return finalNodesAddr, toBeDelNodesAddr, nil
}

// GetBESlot 获取idx段的起始slot编号，左闭右闭
func GetBESlot(idxCount, idx, slotCount int) (beginSlotNum, endSlotNum int) {
	beginSlotNum = idx * slotCount
	endSlotNum = beginSlotNum + slotCount - 1
	if idx == idxCount-1 {
		endSlotNum = consts.DefaultMaxSlots
	}
	return
}

// ForgetDelNodes 删除节点
func (job *ClusterMigrateSlots) ForgetDelNodes(toBeDelNodes []string) error {
	clusterOK, _, err := job.clusterState(job.params.SrcNode.redisCli)
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return err
	}
	if clusterOK == false {
		err = fmt.Errorf("cluster_state is fail,addr:%s", job.srcNodeAddr())
		job.runtime.Logger.Error(err.Error())
		return err
	}

	// 如果任何待删除master节点正在migrate slots,则等待1分钟后重试,最长300分钟
	timeLimit := 0
	for {
		isToBeDelMasterMigrating, migratingAddr, migratingSlots, err1 := job.areTenplusMigrating(toBeDelNodes)
		if err1 != nil {
			return err1
		}
		if isToBeDelMasterMigrating == true {
			time.Sleep(1 * time.Minute)
			// 直到"所有待删除master节点没有migrate slots",再继续搬迁slot;
			msg := fmt.Sprintf("MigrateSlotsFromToBeDelNode toBeDeletedMaster:%s migrating slots count:%d",
				migratingAddr, len(migratingSlots))
			job.runtime.Logger.Info(msg)
			timeLimit++
			continue
		}
		break

	}
	if timeLimit == 300 {
		err = fmt.Errorf("MigrateSlotsFromToBeDelNode  migrating 300 minute,please check")
		job.runtime.Logger.Error(err.Error())
		return err
	}

	clusterNodes, err := job.params.SrcNode.redisCli.GetClusterNodes()
	if err != nil {
		return err
	}
	for _, node := range clusterNodes {
		job.runtime.Logger.Info("after migrate cluster nodes:%s -> slots:%+v", node.Addr, myredis.ConvertSlotToShellFormat(node.Slots))
	}

	job.runtime.Logger.Info("begin to forget nodes:%+v", toBeDelNodes)
	if len(toBeDelNodes) == 0 {
		return nil
	}

	var toBeDelAllNodeId []string
	var finalAllNodeAddr []string

	// 检查拥有的slot是否已经为0
	for _, node := range clusterNodes {
		isDel := false
		for _, addr := range toBeDelNodes {
			if addr == node.Addr {
				if len(node.Slots) != 0 {
					err = fmt.Errorf("toBeDelNode:%s  still have %d slots ", node.Addr, len(node.Slots))
					job.runtime.Logger.Error(err.Error())
					return err
				}
				isDel = true
				toBeDelAllNodeId = append(toBeDelAllNodeId, node.NodeID)
				break
			}
		}
		if !isDel {
			finalAllNodeAddr = append(finalAllNodeAddr, node.Addr)
		}
	}
	job.runtime.Logger.Info("get finalAllNodeAddr success :%v", finalAllNodeAddr)

	// 获取待删master节点的所有slave，将其NodeID也加入待forget列表
	for _, addr01 := range toBeDelNodes {
		dstCli01, err := myredis.NewRedisClient(addr01, job.params.DstNode.Password, 0, consts.TendisTypeRedisInstance)
		if err != nil {
			job.runtime.Logger.Error(err.Error())
			return err
		}
		defer dstCli01.Close()
		dstSlaves, err := dstCli01.GetAllSlaveNodesByMasterAddr(addr01)
		if err != nil {
			job.Err = fmt.Errorf("dstAddr:%s get slave fail:%+v", addr01, err)
			job.runtime.Logger.Error(job.Err.Error())
			return job.Err
		}
		for _, srcSlave01 := range dstSlaves {
			srcSlaveItem := srcSlave01
			toBeDelAllNodeId = append(toBeDelAllNodeId, srcSlaveItem.NodeID)
			job.runtime.Logger.Info("toBeDelNode:%s slave:%s will also be forgot, nodeID:%s",
				addr01, srcSlaveItem.Addr, srcSlaveItem.NodeID)
		}
	}
	job.runtime.Logger.Info("get toBeDelAllNodeNodeID success :%v", toBeDelAllNodeId)

	// 收集待删节点的所有地址（master+slave），用于从finalAllNodeAddr中排除
	toBeDelAllNodeAddr := make(map[string]bool)
	for _, addr := range toBeDelNodes {
		toBeDelAllNodeAddr[addr] = true
	}
	for _, node := range clusterNodes {
		for _, nodeID := range toBeDelAllNodeId {
			if node.NodeID == nodeID {
				toBeDelAllNodeAddr[node.Addr] = true
				break
			}
		}
	}

	// 重新构建finalAllNodeAddr，排除待删节点及其slave
	finalAllNodeAddr = []string{}
	for _, addr := range finalAllNodeAddr {
		if !toBeDelAllNodeAddr[addr] {
			finalAllNodeAddr = append(finalAllNodeAddr, addr)
		}
	}
	job.runtime.Logger.Info("finalAllNodeAddr after excluding slaves of toBeDelNodes: %v", finalAllNodeAddr)

	// 最终节点forget要下架节点（只从保留节点发起forget）
	var errForgetList []string
	for _, addr03 := range finalAllNodeAddr {
		addrCli, err := myredis.NewRedisClient(addr03, job.params.SrcNode.Password, 0, consts.TendisTypeRedisInstance)
		if err != nil {
			job.runtime.Logger.Error(err.Error())
			return err
		}
		defer addrCli.Close()
		for _, nodeID := range toBeDelAllNodeId {
			err := addrCli.ClusterForget(nodeID)
			if err != nil {
				errForgetList = append(errForgetList, fmt.Sprintf("node:%s cluster forget %s failed", addr03, nodeID))
				job.runtime.Logger.Error(err.Error())
			}
			job.runtime.Logger.Info("node:%s forget node:%s success.", addr03, nodeID)
		}

	}
	if len(errForgetList) > 0 {
		err = fmt.Errorf("%s", strings.Join(errForgetList, "\n"))
		job.runtime.Logger.Error(err.Error())
		return err
	}
	job.runtime.Logger.Info("cluster forget round 1 done, waiting 60s for gossip propagation...")

	// 等待 60 秒，让 gossip 协议充分传播，确保所有节点都完成了第一轮 forget
	// 同时等待被删节点的黑名单过期（60s），防止被删节点通过 gossip 把自己广播回来
	time.Sleep(60 * time.Second)

	// 第二轮 forget（双保险）：防止第一轮 forget 后被删节点或其 slave 通过 gossip 又被重新广播回来
	// 在黑名单过期前再次 forget，刷新黑名单计时器
	job.runtime.Logger.Info("start cluster forget round 2 (double check)...")
	errForgetList = nil
	for _, addr03 := range finalAllNodeAddr {
		addrCli, err := myredis.NewRedisClient(addr03, job.params.SrcNode.Password, 0, consts.TendisTypeRedisInstance)
		if err != nil {
			job.runtime.Logger.Error(err.Error())
			return err
		}
		defer addrCli.Close()
		for _, nodeID := range toBeDelAllNodeId {
			err := addrCli.ClusterForget(nodeID)
			if err != nil {
				errForgetList = append(errForgetList, fmt.Sprintf("node:%s cluster forget %s failed (round 2)", addr03, nodeID))
				job.runtime.Logger.Error(err.Error())
			} else {
				job.runtime.Logger.Info("node:%s forget node:%s success (round 2).", addr03, nodeID)
			}
		}
	}
	if len(errForgetList) > 0 {
		job.runtime.Logger.Warn("cluster forget round 2 has some errors (may be already forgot): %s",
			strings.Join(errForgetList, ";"))
		// 第二轮失败不返回错误，因为节点可能已经被成功 forget 了
	}
	job.runtime.Logger.Info("cluster forget (round 1 + round 2) all done")
	return nil
}

// ReBalanceSlot 计算发起迁移任务。重新分配slot
func (job *ClusterMigrateSlots) ReBalanceSlot() error {
	// 最终保留节点、 删除节点
	finalNodes, toBeDelNodes, err := job.GetMigrateNodes()
	if err != nil {
		return err
	}
	job.runtime.Logger.Info("finalNodes:%+v, toBeDelNodesAddr:%+v", finalNodes, toBeDelNodes)

	// 集群最终master节点数
	finalNodeCount := len(finalNodes)
	// 最终每一个节点的slot数。如果除不尽，那么余数全部放在最后一个node去
	finalSlotCount2Node := int(float64(consts.DefaultMaxSlots+1) / float64(finalNodeCount))
	// 段是否已被选择，被那个节点选择
	segmentIsChose := make(map[int]bool, finalNodeCount)
	node2Segment := make(map[string]int, finalNodeCount)
	// 初始化每个段都没被选择
	for idx := 0; idx < finalNodeCount; idx++ {
		segmentIsChose[idx] = false
	}

	// 缩容：保留节点肯定在集群里。扩容：保留节点已经加入集群了
	clusterNodes, err := job.params.SrcNode.redisCli.GetClusterNodes()
	if err != nil {
		return err
	}

	for _, node := range clusterNodes {
		job.runtime.Logger.Info("before migrate cluster nodes:%s -> slots:%+v", node.Addr, myredis.ConvertSlotToShellFormat(node.Slots))
	}

	// 按照拥有slot的个数排序，优先分配slot多的
	sort.Slice(clusterNodes, func(i, j int) bool {
		a := len(clusterNodes[i].Slots)
		b := len(clusterNodes[j].Slots)
		return a > b
	})

	// 保存slot当前所属节点（需要遍历所有master节点，包括待删除节点）
	slotSrcNodeMap := make(map[int]string)
	for _, node := range clusterNodes {
		if node.Role != consts.RedisMasterRole {
			continue
		}
		for _, slot := range node.Slots {
			slotSrcNodeMap[slot] = node.Addr
		}
	}

	// 生成迁移任务，并发执行迁移
	migrateTasks := []MigrateSomeSlots{}

	// ========== 缩容优化：只迁移待删节点的slot，保留节点slot不动 ==========
	toBeDelNodesMap := make(map[string]bool)
	for _, addr := range toBeDelNodes {
		toBeDelNodesMap[addr] = true
	}

	if len(toBeDelNodes) > 0 {
		// 缩容场景：保留节点的slot段尽量连续，同时尽量少迁移
		// 策略：将slot分成finalNodeCount段，先统计每个保留节点在各段中的匹配度，
		// 然后按匹配度降序依次选段，避免"先到先得"导致的错配
		job.runtime.Logger.Info("缩容模式: 保留节点slot段尽量连续, 最小化迁移量")

		// 第一步：统计每个保留节点在各段的匹配度
		type nodeSegStat struct {
			addr       string
			segIdx     int
			matchCount int // 该节点在该段中拥有的slot数
			isDelNode  bool
		}
		var allNodeSegStats []nodeSegStat

		for _, node := range clusterNodes {
			if node.Role != consts.RedisMasterRole {
				continue
			}
			addr := node.Addr
			isFinal := false
			for _, finalNode := range finalNodes {
				if addr == finalNode {
					isFinal = true
					break
				}
			}
			if !isFinal {
				continue
			}
			nodeSlotMap := node.SlotsMap
			for idx := 0; idx < finalNodeCount; idx++ {
				matchCount := 0
				beginSlotNum, endSlotNum := GetBESlot(finalNodeCount, idx, finalSlotCount2Node)
				for slot := beginSlotNum; slot <= endSlotNum; slot++ {
					if ex, ok := nodeSlotMap[slot]; ok && ex {
						matchCount++
					}
				}
				allNodeSegStats = append(allNodeSegStats, nodeSegStat{
					addr:       addr,
					segIdx:     idx,
					matchCount: matchCount,
				})
				job.runtime.Logger.Info("缩容 node stats: [node:%s, seg:%d, range:[%d-%d], count:%d]",
					addr, idx, beginSlotNum, endSlotNum, matchCount)
			}
		}

		// 第二步：按匹配度降序排序（匹配度相同则按段号升序，优先保持段序）
		sort.Slice(allNodeSegStats, func(i, j int) bool {
			if allNodeSegStats[i].matchCount != allNodeSegStats[j].matchCount {
				return allNodeSegStats[i].matchCount > allNodeSegStats[j].matchCount
			}
			return allNodeSegStats[i].segIdx < allNodeSegStats[j].segIdx
		})

		// 第三步：贪心分配，匹配度最高的先选
		for _, stat := range allNodeSegStats {
			if _, chosen := node2Segment[stat.addr]; chosen {
				continue // 该节点已经选了段
			}
			if segmentIsChose[stat.segIdx] {
				continue // 该段已被占用
			}
			node2Segment[stat.addr] = stat.segIdx
			segmentIsChose[stat.segIdx] = true
			beginSlotNum, endSlotNum := GetBESlot(finalNodeCount, stat.segIdx, finalSlotCount2Node)
			job.runtime.Logger.Info("缩容 final nodes:%s chose segment:%d, slot range:[%d-%d], matchCount:%d",
				stat.addr, stat.segIdx, beginSlotNum, endSlotNum, stat.matchCount)
		}

		// 根据段分配生成迁移任务：每个保留节点接收自己段内、但不属于当前自己的slot
		for addr, segIdx := range node2Segment {
			beginSlotNum, endSlotNum := GetBESlot(finalNodeCount, segIdx, finalSlotCount2Node)
			srcAddrSlots := make(map[string][]int)
			for slot := beginSlotNum; slot <= endSlotNum; slot++ {
				srcAddr := slotSrcNodeMap[slot]
				if srcAddr == addr {
					continue // 该slot已经在本节点上，不需要迁移
				}
				srcAddrSlots[srcAddr] = append(srcAddrSlots[srcAddr], slot)
			}
			for srcAddr, slots := range srcAddrSlots {
				migrateTasks = append(migrateTasks, MigrateSomeSlots{
					SrcAddr:      srcAddr,
					DstAddr:      addr,
					MigrateSlots: slots,
				})
				if len(slots) > 0 {
					job.runtime.Logger.Info("缩容迁移: %s => %s, slots:%v, slotsCount:%d",
						srcAddr, addr, myredis.ConvertSlotToShellFormat(slots), len(slots))
				}
			}
		}
	} else {
		// ========== 扩容场景：使用原来的分段分配算法 ==========
		job.runtime.Logger.Info("扩容模式: 使用分段分配算法")
		for _, node := range clusterNodes {
			isFinal := false
			if node.Role != consts.RedisMasterRole {
				continue
			}
			for _, finalNode := range finalNodes {
				if node.Addr == finalNode {
					isFinal = true
					break
				}
			}
			if !isFinal {
				continue
			}

			type seg struct {
				idx   int
				count int
			}
			var nodeSlot4SegStat []seg

			addr := node.Addr
			nodeSlotMap := node.SlotsMap
			for idx := 0; idx < finalNodeCount; idx++ {
				sc := seg{
					idx:   idx,
					count: 0,
				}
				beginSlotNum, endSlotNum := GetBESlot(finalNodeCount, sc.idx, finalSlotCount2Node)
				for slot := beginSlotNum; slot <= endSlotNum; slot++ {
					if ex, ok := nodeSlotMap[slot]; ok && ex {
						sc.count++
					}
				}
				nodeSlot4SegStat = append(nodeSlot4SegStat, sc)
				job.runtime.Logger.Info("src node stats: [node:%s, seg:%d, count:%d]", addr, sc.idx, sc.count)
			}
			sort.Slice(nodeSlot4SegStat, func(i, j int) bool {
				a := nodeSlot4SegStat[i].count
				b := nodeSlot4SegStat[j].count
				return a > b
			})

			// 从高到低遍历seg,优先选择当前拥有slot多的seg
			for _, sc := range nodeSlot4SegStat {
				// 如果seg还没被选择，则将这个段设置为该Node的最终态。 顺便计算出迁移任务
				if !segmentIsChose[sc.idx] {
					node2Segment[addr] = sc.idx
					segmentIsChose[sc.idx] = true

					beginSlotNum, endSlotNum := GetBESlot(finalNodeCount, sc.idx, finalSlotCount2Node)
					job.runtime.Logger.Info("final nodes:%s slot will is [%d-%d]", addr, beginSlotNum, endSlotNum)

					// 记录slot的来源addr和slots
					srcAddrSlots := make(map[string][]int)
					for slot := beginSlotNum; slot <= endSlotNum; slot++ {
						srcAddr := slotSrcNodeMap[slot]
						job.runtime.Logger.Info("slot:%+v running src addr:%+v", slot, srcAddr)
						// 该slot不需要迁移
						if srcAddr == addr {
							continue
						}
						srcAddrSlots[srcAddr] = append(srcAddrSlots[srcAddr], slot)
					}

					// 生成task
					for srcAddr := range srcAddrSlots {
						task01 := MigrateSomeSlots{
							SrcAddr:      srcAddr,
							DstAddr:      addr,
							MigrateSlots: srcAddrSlots[srcAddr],
						}
						migrateTasks = append(migrateTasks, task01)
					}
					break
				}
			}
		}
	} // end else (扩容场景)

	// 随机打乱迁移任务顺序，避免单节点在短时间内slot过多或过少
	rand.Shuffle(len(migrateTasks), func(i, j int) {
		migrateTasks[i], migrateTasks[j] = migrateTasks[j], migrateTasks[i]
	})

	// 打印分组计划汇总
	job.runtime.Logger.Info("===== slot 分组计划开始 =====")
	job.runtime.Logger.Info("finalNodeCount:%d, finalSlotCount2Node:%d", finalNodeCount, finalSlotCount2Node)
	for addr, segIdx := range node2Segment {
		beginSlotNum, endSlotNum := GetBESlot(finalNodeCount, segIdx, finalSlotCount2Node)
		job.runtime.Logger.Info("node:%s => segment:%d, slot range:[%d-%d]", addr, segIdx, beginSlotNum, endSlotNum)
	}
	job.runtime.Logger.Info("===== slot 分组计划结束 =====")

	// 打印迁移执行计划
	job.runtime.Logger.Info("===== 迁移执行计划开始 =====")
	for _, task01 := range migrateTasks {
		msg := fmt.Sprintf("migrate plan=>srcNode:%s dstNode:%s slots:%v",
			task01.SrcAddr, task01.DstAddr, myredis.ConvertSlotToShellFormat(task01.MigrateSlots))
		job.runtime.Logger.Info(msg)
	}
	job.runtime.Logger.Info("migrateTasks:%+v", migrateTasks)
	job.runtime.Logger.Info("===== 迁移执行计划结束 =====")

	err = job.ParallelMigrateSpecificSlots(migrateTasks)
	if err != nil {
		return err
	}

	err = job.ForgetDelNodes(toBeDelNodes)
	if err != nil {
		return err
	}
	return nil
}

// redisClusterRebalanceSlot 为 RedisCluster 重新规划迁移任务。
// 与 ReBalanceSlot 的区别：RedisCluster 的 redis-cli --cluster reshard 不支持指定具体 slot，
// 只能指定迁移数量（从 src 随机选 slot 迁出），因此需要从全局视角计算最少迁移量。
// 算法：
// 1. 计算每个 finalNode 的期望 slot 数 = 16384 / finalNodeCount
// 2. 计算每个节点的 balance = 当前 slot 数 - 期望数（正数=多余，负数=不足）
// 3. 多余节点迁出，不足节点接收，贪心配对最小化迁移次数
func (job *ClusterMigrateSlots) redisClusterRebalanceSlot() error {
	finalNodes, toBeDelNodes, err := job.GetMigrateNodes()
	if err != nil {
		return err
	}
	job.runtime.Logger.Info("[rediscluster] finalNodes:%+v, toBeDelNodes:%+v", finalNodes, toBeDelNodes)

	clusterNodes, err := job.params.SrcNode.redisCli.GetClusterNodes()
	if err != nil {
		return err
	}

	for _, node := range clusterNodes {
		if node.Role == consts.RedisMasterRole {
			job.runtime.Logger.Info("[rediscluster] before migrate node:%s -> slots:%d",
				node.Addr, len(node.Slots))
		}
	}

	finalNodeCount := len(finalNodes)
	expectedSlotNum := (consts.DefaultMaxSlots + 1) / finalNodeCount

	// 构建待删节点集合
	toBeDelNodesMap := make(map[string]bool)
	for _, addr := range toBeDelNodes {
		toBeDelNodesMap[addr] = true
	}

	// 计算每个 finalNode 的当前 slot 数和期望数
	type nodeBalance struct {
		addr     string
		curSlots int
		expected int
		balance  int // 正数=多余需要迁出, 负数=不足需要接收
	}
	var balances []nodeBalance
	totalMigrateSlots := 0

	for _, addr := range finalNodes {
		curSlots := 0
		for _, node := range clusterNodes {
			if node.Role == consts.RedisMasterRole && node.Addr == addr {
				curSlots = len(node.Slots)
				break
			}
		}
		b := curSlots - expectedSlotNum
		balances = append(balances, nodeBalance{
			addr:     addr,
			curSlots: curSlots,
			expected: expectedSlotNum,
			balance:  b,
		})
		if b > 0 {
			totalMigrateSlots += b
		}
	}

	// 缩容场景：待删节点的 slot 也需要被迁出
	toBeDelTotalSlots := 0
	for _, node := range clusterNodes {
		if node.Role == consts.RedisMasterRole && toBeDelNodesMap[node.Addr] {
			toBeDelTotalSlots += len(node.Slots)
		}
	}
	if toBeDelTotalSlots > 0 {
		// 缩容时，待删节点的 slot 全部需要迁出，重新计算期望
		// 期望数 = (所有master的slot总数) / finalNodeCount
		totalSlotsInCluster := 0
		for _, node := range clusterNodes {
			if node.Role == consts.RedisMasterRole {
				totalSlotsInCluster += len(node.Slots)
			}
		}
		newExpected := totalSlotsInCluster / finalNodeCount
		totalMigrateSlots = 0
		for i := range balances {
			balances[i].expected = newExpected
			balances[i].balance = balances[i].curSlots - newExpected
			if balances[i].balance < 0 {
				totalMigrateSlots += -balances[i].balance
			}
		}
	}

	// 打印平衡表
	for _, b := range balances {
		job.runtime.Logger.Info("[rediscluster] node:%s curSlots:%d expected:%d balance:%d",
			b.addr, b.curSlots, b.expected, b.balance)
	}
	job.runtime.Logger.Info("[rediscluster] total migrate slots needed:%d", totalMigrateSlots)

	// 分离迁出方（balance > 0）和接收方（balance < 0）
	type srcNode struct {
		addr   string
		remain int // 还需要迁出的 slot 数
	}
	type dstNode struct {
		addr string
		need int // 还需要接收的 slot 数
	}

	var srcs []srcNode
	var dsts []dstNode
	for _, b := range balances {
		if b.balance > 0 {
			srcs = append(srcs, srcNode{addr: b.addr, remain: b.balance})
		} else if b.balance < 0 {
			dsts = append(dsts, dstNode{addr: b.addr, need: -b.balance})
		}
	}

	// 缩容场景：待删节点的 slot 全部需要迁出
	for _, node := range clusterNodes {
		if node.Role == consts.RedisMasterRole && toBeDelNodesMap[node.Addr] && len(node.Slots) > 0 {
			srcs = append(srcs, srcNode{addr: node.Addr, remain: len(node.Slots)})
		}
	}

	// 贪心配对：生成迁移任务
	// 对于 RedisCluster，不需要指定具体 slot，只指定数量
	migrateTasks := []MigrateSomeSlots{}

	for len(dsts) > 0 {
		if len(srcs) == 0 {
			job.runtime.Logger.Warn("[rediscluster] no more src nodes but dst nodes still need slots")
			break
		}

		dst := &dsts[0]
		need := dst.need
		if need <= 0 {
			dsts = dsts[1:]
			continue
		}

		// 从有余额的 src 节点迁出
		for i := range srcs {
			if srcs[i].remain <= 0 {
				continue
			}
			if need <= 0 {
				break
			}

			migrateCount := srcs[i].remain
			if migrateCount > need {
				migrateCount = need
			}

			// 为 RedisCluster 生成迁移任务，使用 MigrateCount 记录迁移数量
			// MigrateSpecificSlots 中会按数量执行 redis-cli --cluster reshard
			migrateTasks = append(migrateTasks, MigrateSomeSlots{
				SrcAddr:      srcs[i].addr,
				DstAddr:      dst.addr,
				MigrateCount: migrateCount,
			})
			job.runtime.Logger.Info("[rediscluster] migrate plan: %s => %s, slotsCount:%d (by count)",
				srcs[i].addr, dst.addr, migrateCount)

			srcs[i].remain -= migrateCount
			need -= migrateCount
		}

		dst.need = need
		if need <= 0 {
			dsts = dsts[1:]
		}
	}

	// 打印迁移计划汇总
	totalPlannedMigrate := 0
	for _, task := range migrateTasks {
		totalPlannedMigrate += len(task.MigrateSlots)
	}
	// 用实际的 reshard 数量统计
	job.runtime.Logger.Info("[rediscluster] ===== 迁移执行计划开始 =====")
	job.runtime.Logger.Info("[rediscluster] total migrate tasks:%d", len(migrateTasks))
	for i, task := range migrateTasks {
		job.runtime.Logger.Info("[rediscluster] task %d: %s => %s (按数量迁移, 通过 reshard 命令)",
			i, task.SrcAddr, task.DstAddr)
	}
	job.runtime.Logger.Info("[rediscluster] ===== 迁移执行计划结束 =====")

	if len(migrateTasks) == 0 {
		job.runtime.Logger.Info("[rediscluster] no migration needed, cluster is already balanced")
		return nil
	}

	err = job.ParallelMigrateSpecificSlots(migrateTasks)
	if err != nil {
		return err
	}

	err = job.ForgetDelNodes(toBeDelNodes)
	if err != nil {
		return err
	}
	return nil
}

// PreCheck 迁移前置检查
func (job *ClusterMigrateSlots) PreCheck() error {
	job.checkNodeInfo()
	if job.Err != nil {
		return job.Err
	}

	return nil
}
