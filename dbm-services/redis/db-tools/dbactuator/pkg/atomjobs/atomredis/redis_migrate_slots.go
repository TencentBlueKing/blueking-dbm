package atomredis

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"math"
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

// TendisPlusMigrateSlotsParams slots 迁移参数
type TendisPlusMigrateSlotsParams struct {
	SrcNode TendisPlusNodeItem `json:"src_node" validate:"required"`
	DstNode TendisPlusNodeItem `json:"dst_node" validate:"required"`
	// 用于缩容场景，迁移DstNode slot ，然后删除节点
	IsDeleteNode bool `json:"is_delete_node"`
	// 迁移特定的slot,一般用于热点key情况，把该key所属slot迁移到单独节点
	MigrateSpecifiedSlot bool `json:"migrate_specified_slot" `
	// 如 0-4095 6000 6002-60010,
	Slots string `json:"slots"`
}

// TendisPlusMigrateSlots slots 迁移
type TendisPlusMigrateSlots struct {
	params  TendisPlusMigrateSlotsParams
	runtime *jobruntime.JobGenericRuntime
	Err     error `json:"_"`
}

// TendisPlusNodeItem  节点信息
type TendisPlusNodeItem struct {
	IP         string               `json:"ip"`
	Port       int                  `json:"port"`
	Password   string               `json:"password"`
	Role       string               `json:"role"`
	TendisType string               `json:"tendis_type"`
	redisCli   *myredis.RedisClient `json:"-"` // NOCC:vet/vet(设计如此)
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*TendisPlusMigrateSlots)(nil)

// NewTendisPlusMigrateSlots new
func NewTendisPlusMigrateSlots() jobruntime.JobRunner {
	return &TendisPlusMigrateSlots{}
}

// Init 初始化
func (job *TendisPlusMigrateSlots) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("TendisPlusMigrateSlots Init params validate failed,err:%v,params:%+v", err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("TendisPlusMigrateSlots Init params validate failed,err:%v,params:%+v", err, job.params)
			return err
		}
	}
	if job.params.MigrateSpecifiedSlot && job.params.Slots == "" {

		err = fmt.Errorf("MigrateSpecifiedSlot=%v 和 slots:%s 指定迁移的slot不能为空",
			job.params.MigrateSpecifiedSlot, job.params.Slots)
		job.runtime.Logger.Error(err.Error())
		return err

	}

	job.runtime.Logger.Info("tendisplus migrate slots init success")

	return nil

}

// Name 原子任务名
func (job *TendisPlusMigrateSlots) Name() string {
	return "tendisplus_migrate_slots"

}

// Retry 重试次数
func (job *TendisPlusMigrateSlots) Retry() uint {
	return 2
}

// Rollback rollback
func (job *TendisPlusMigrateSlots) Rollback() error {
	return nil

}

// Run 执行逻辑
func (job *TendisPlusMigrateSlots) Run() error {
	job.checkNodeInfo()
	if job.Err != nil {
		return job.Err
	}
	if job.params.IsDeleteNode {
		var toBeDelNodesAddr []string
		toBeDelNodesAddr = append(toBeDelNodesAddr, job.dstNodeAddr())
		err := job.MigrateSlotsFromToBeDelNode(toBeDelNodesAddr)
		if err != nil {
			return err
		}
		return nil
	}

	job.dstClusterMeetSrc()
	if job.Err != nil {
		return job.Err
	}

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
		job.MigrateSpecificSlots(job.srcNodeAddr(), job.dstNodeAddr(), slots, 20*time.Minute)
		if job.Err != nil {
			return job.Err
		}
	} else {
		err := job.ReBalanceCluster()
		if err != nil {
			job.Err = err
			return job.Err
		}
	}

	return nil
}

// srcNodeAddr 源节点地址
func (job *TendisPlusMigrateSlots) srcNodeAddr() string {
	return job.params.SrcNode.IP + ":" + strconv.Itoa(job.params.SrcNode.Port)
}

// dstNodeAddr 源节点地址
func (job *TendisPlusMigrateSlots) dstNodeAddr() string {
	return job.params.DstNode.IP + ":" + strconv.Itoa(job.params.DstNode.Port)
}

// dstClusterMeetSrc 新建节点加入源集群
func (job *TendisPlusMigrateSlots) dstClusterMeetSrc() {
	var err error
	nodePasswordOnMachine, err := myredis.GetPasswordFromLocalConfFile(job.params.SrcNode.Port)
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
func (job *TendisPlusMigrateSlots) clusterState(redisCli *myredis.RedisClient) (state bool,
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
func (job *TendisPlusMigrateSlots) checkNodeInfo() {
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

	// 获取源节点连接&信息
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

	// 由于迁移slot命令和社区不一样，所以必须是tendisplus
	if job.params.SrcNode.TendisType != consts.TendisTypeTendisplusInsance || job.params.DstNode.TendisType !=
		consts.TendisTypeTendisplusInsance {
		job.Err = fmt.Errorf("node tendisType != TendisplusInstance ,please check ! srcNodeTendisType is %s"+
			" dsrNodeTendisType is %s", job.params.SrcNode.TendisType, job.params.DstNode.TendisType)
		job.runtime.Logger.Error(job.Err.Error())
	}
	job.runtime.Logger.Info("checkNodeInfo tendisType success: DstNode tendisType %s",
		job.params.DstNode.TendisType)

	return
}

// ParallelMigrateSpecificSlots 并发执行slot迁移任务
func (job *TendisPlusMigrateSlots) ParallelMigrateSpecificSlots(migrateList []MigrateSomeSlots) error {
	wg := sync.WaitGroup{}
	genChan := make(chan MigrateSomeSlots)
	retChan := make(chan MigrateSomeSlots)

	limit := len(migrateList) // no limit
	for worker := 0; worker < limit; worker++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for item01 := range genChan {
				job.MigrateSpecificSlots(item01.SrcAddr, item01.DstAddr, item01.MigrateSlots, 48*time.Hour)
				if job.Err != nil {
					item01.Err = job.Err
				}
				retChan <- item01
			}
		}()
	}
	go func() {
		defer close(genChan)

		for _, item02 := range migrateList {
			genChan <- item02
		}
	}()

	go func() {
		wg.Wait()
		close(retChan)
	}()

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

// MigrateSomeSlots ..(为并发迁移slot)
type MigrateSomeSlots struct {
	SrcAddr      string
	DstAddr      string
	MigrateSlots []int
	Err          error
}

// ReBalanceCluster 重新分配slots,
// 将slots尽量均匀的分配到新masterNode(没负责任何slot的master)上
// NOCC:golint/fnsize(设计如此)
func (job *TendisPlusMigrateSlots) ReBalanceCluster() error {
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
	for totalBalance > 0 {
		for _, node01 := range allRunningMasters {
			nodeItem := node01
			if nodeItem.Balance() < 0 && totalBalance > 0 {
				t01 := nodeItem.Balance() - 1
				nodeItem.SetBalance(t01)
				totalBalance -= 1
			}
		}
	}
	sort.Slice(runningMasterList, func(i, j int) bool {
		a := runningMasterList[i]
		b := runningMasterList[j]
		return a.Balance() < b.Balance()
	})

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

	err = job.ParallelMigrateSpecificSlots(migrateTasks)
	if err != nil {
		return err
	}

	return nil
}

// MigrateSpecificSlots 迁移slots
// NOCC:golint/fnsize(设计如此)
func (job *TendisPlusMigrateSlots) MigrateSpecificSlots(srcAddr,
	dstAddr string, slots []int, timeout time.Duration) {
	job.runtime.Logger.Info("MigrateSpecificSlots start... srcAddr:%s desrAddr:%s"+
		" slots:%+v", srcAddr, dstAddr, myredis.ConvertSlotToShellFormat(slots))

	if len(slots) == 0 {
		job.Err = fmt.Errorf("MigrateSpecificSlots target slots count == %d ", len(slots))
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
		job.Err = fmt.Errorf("MigrateSpecificSlots cluster not include the sre node,sreAddr:%s,clusterAddr:%s",
			srcAddr, job.params.SrcNode.redisCli.Addr)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}

	dstNodeInfo, ok := clusterNodes[dstAddr]
	if ok == false {
		job.Err = fmt.Errorf("MigrateSpecificSlots cluster not include the sre node,sreAddr:%s,clusterAddr:%s",
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
	// job.runtime.Logger.Info("clusterNodes:%+v", clusterNodes)
	allBelong, notBelongList, err := job.params.SrcNode.redisCli.IsSlotsBelongMaster(srcAddr, slots)
	if err != nil {
		job.Err = err
		job.runtime.Logger.Error(job.Err.Error())
		return
	}
	if allBelong == false {
		err = fmt.Errorf("MigrateSpecificSlots slots:%s not belong to srcNode:%s",
			myredis.ConvertSlotToShellFormat(notBelongList), srcAddr)
		job.runtime.Logger.Error(err.Error())
		return
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
			msg = fmt.Sprintf(`slot in deleting : MigrateSpecificSlots execute cluster setslot importing fail,
			err:%v,srcAddr:%s,dstAddr:%s,cmd: cluster setslot importing %s %s`, err, srcAddr, dstAddr, srcNodeInfo.NodeID, myredis.ConvertSlotToShellFormat(slots))
			job.runtime.Logger.Warn(msg)
			time.Sleep(1 * time.Minute)
			deleteSlotErrRetryTimes++
			continue
		} else if err != nil && strings.Contains(err.Error(), "slot not empty") == true {
			dstCli.ClusterClear()
			srcCli.ClusterClear()
			msg = fmt.Sprintf(`slot not empty : MigrateSpecificSlots execute cluster setslot importing fail,
			err:%v,srcAddr:%s,dstAddr:%s,cmd: cluster setslot importing %s %s`, err, srcAddr, dstAddr, srcNodeInfo.NodeID, myredis.ConvertSlotToShellFormat(slots))
			job.runtime.Logger.Warn(msg)
			time.Sleep(1 * time.Minute)
			deleteSlotErrRetryTimes++
			continue
		} else if err != nil {
			err = fmt.Errorf(`MigrateSpecificSlots execute cluster setslot importing fail,
			err:%v,srcAddr:%s,dstAddr:%s,cmd: cluster setslot importing %s %s`, err, srcAddr, dstAddr, srcNodeInfo.NodeID, myredis.ConvertSlotToShellFormat(slots))
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
	return
}

// confirmMigrateSlotsStatus 在dstAddr上执行 cluster setslot info 确认slots是否迁移ok
func (job *TendisPlusMigrateSlots) confirmMigrateSlotsStatus(
	srcNodeInfo, dstNodeInfo *myredis.ClusterNodeData,
	taskID string, migrateSlots []int, timeout time.Duration) (mySuccImport, myFailImport []int, err error) {

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
func (job *TendisPlusMigrateSlots) retryMigrateSpecSlots(
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
func (job *TendisPlusMigrateSlots) findNewMasterWhenFailover(
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
func (job *TendisPlusMigrateSlots) MigrateSlotsFromToBeDelNode(toBeDelNodesAddr []string) (err error) {
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
func (job *TendisPlusMigrateSlots) areTenplusMigrating(tenplusAddrs []string) (
	migratingOrNot bool, migratingAddr string, migatingSlots []int, err error,
) {
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
