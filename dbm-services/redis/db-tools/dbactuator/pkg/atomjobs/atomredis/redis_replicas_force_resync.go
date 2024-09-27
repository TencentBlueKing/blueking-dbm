package atomredis

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/go-playground/validator/v10"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// ReplicaResyncParams params
type ReplicaResyncParams struct {
	SlaveIP    string `json:"slave_ip" validate:"required"`
	SlavePorts []int  `json:"slave_ports" validate:"required"`
}

// ReplicasForceResync TODO
type ReplicasForceResync struct {
	runtime         *jobruntime.JobGenericRuntime
	params          ReplicaResyncParams
	slaveAddrMapCli map[string]*myredis.RedisClient
	slavePairsMap   map[string]ReplicaItem
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*ReplicasForceResync)(nil)

// NewReplicasForceResync new
func NewReplicasForceResync() jobruntime.JobRunner {
	return &ReplicasForceResync{}
}

// Init prepare run env
func (job *ReplicasForceResync) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("ReplicasForceResync Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("ReplicasForceResync Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	return nil
}

// Name 原子任务名
func (job *ReplicasForceResync) Name() string {
	return "redis_replicas_force_resync"
}

// getReplicaPairsFile 获取 master slave pairs 文件
func (job *ReplicasForceResync) getReplicaPairsFile() string {
	file := fmt.Sprintf("%s_%s_master_replica_pairs", job.runtime.UID, job.params.SlaveIP)
	saveDir := filepath.Join(consts.GetRedisBackupDir(), "dbbak", "replicas_force_resync")
	if !util.FileExists(saveDir) {
		util.MkDirsIfNotExists([]string{saveDir})
		util.LocalDirChownMysql(saveDir)
	}
	fullPath := filepath.Join(saveDir, file)
	return fullPath
}

// checkReplicaParisFileExistsAndNotEmpty 检查文件是否存在且不为空
// 如果文件不存在或为空,则返回 false
// 如果文件存在且不为空,则返回 true
func (job *ReplicasForceResync) checkReplicaParisFileExistsAndNotEmpty() (ok bool, err error) {
	fullPath := job.getReplicaPairsFile()
	if !util.FileExists(fullPath) {
		return false, nil
	}
	statInfo, err := os.Stat(fullPath)
	if err != nil {
		err = fmt.Errorf("os.Stat failed,err:%v,fullPath:%s", err, fullPath)
		job.runtime.Logger.Error(err.Error())
		return false, err
	}
	if statInfo.Size() == 0 {
		return false, nil
	}
	return true, nil
}

// writeSlavePairsToFile 将主从关系写入文件
func (job *ReplicasForceResync) writeSlavePairsToFile() (err error) {
	pairFile := job.getReplicaPairsFile()
	pairData, err := json.Marshal(job.slavePairsMap)
	if err != nil {
		err = fmt.Errorf("json.Marshal failed,err:%v,pairData:%+v", err, job.slavePairsMap)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	err = os.WriteFile(pairFile, pairData, 0644)
	if err != nil {
		err = fmt.Errorf("os.WriteFile failed,err:%v,pairFile:%s,pairData:%s", err, pairFile, pairData)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	util.LocalDirChownMysql(pairFile)
	job.runtime.Logger.Info(fmt.Sprintf("writeSlavePairsToFile to %s ok", pairFile))
	return nil
}

// getSlavePairsFromFile 从slave pairs文件中读取数据,并填充到job.slavePairsMap中,得到主从关系
func (job *ReplicasForceResync) getSlavePairsFromFile() (err error) {
	pairFile := job.getReplicaPairsFile()
	if !util.FileExists(pairFile) {
		err = fmt.Errorf("file:%s not exists", pairFile)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	pairData, err := os.ReadFile(pairFile)
	if err != nil {
		err = fmt.Errorf("os.ReadFile failed,err:%v,pairFile:%s", err, pairFile)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	pairDecoded := make(map[string]ReplicaItem)
	err = json.Unmarshal(pairData, &pairDecoded)
	if err != nil {
		err = fmt.Errorf("json.Unmarshal failed,err:%v,pairData:%s", err, pairData)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	for k, v := range pairDecoded {
		if _, ok := job.slavePairsMap[k]; !ok {
			job.slavePairsMap[k] = v
		}
	}
	job.runtime.Logger.Info(fmt.Sprintf("completeSlavePairs from %s ok", pairFile))
	return nil
}

// Run Command Run
func (job *ReplicasForceResync) Run() (err error) {
	util.StopBkDbmon()
	defer util.StartBkDbmon()

	job.slavePairsMap = make(map[string]ReplicaItem)
	err = job.slaveInstsAbleToConnect()
	if err != nil {
		return err
	}
	defer job.allInstDisconnect()

	// slaveof no one
	err = job.slaveofNoOneAndUtilToMaster()
	if err != nil {
		return err
	}
	// slave flushall
	err = job.slaveFlushall()
	if err != nil {
		return err
	}
	err = job.clusterMeetAndUtilFinish()
	if err != nil {
		return err
	}
	// slaveof master_ip master_port
	err = job.ReplicaResync()
	if err != nil {
		return err
	}
	return nil
}

// slaveInstsAbleToConnect 检查所有slave可连接
func (job *ReplicasForceResync) slaveInstsAbleToConnect() (err error) {
	instsAddrs := make([]string, 0, len(job.params.SlavePorts))
	job.slaveAddrMapCli = make(map[string]*myredis.RedisClient, len(job.params.SlavePorts))
	var addr, password, role, masterHost, masterPortStr string
	pairFileOK, err := job.checkReplicaParisFileExistsAndNotEmpty()
	if err != nil {
		return err
	}
	allInstancesSlave := true
	for _, port := range job.params.SlavePorts {
		addr = fmt.Sprintf("%s:%d", job.params.SlaveIP, port)
		instsAddrs = append(instsAddrs, addr)
		password, err = myredis.GetRedisPasswdFromConfFile(port)
		if err != nil {
			return err
		}
		cli, err := myredis.NewRedisClientWithTimeout(addr, password, 0,
			consts.TendisTypeRedisInstance, 5*time.Second)
		if err != nil {
			return err
		}
		role, err = cli.GetRole()
		if err != nil {
			return err
		}
		if role != consts.RedisSlaveRole {
			if !pairFileOK {
				// 如果存在非slave角色,同时 不存在slave pairs 文件
				// 代表是第一次运行,这种情况报错
				// 第一次运行,slave关系必须是ok的
				err = fmt.Errorf("redis instance(%s) role:%s,not slave role", addr, role)
				job.runtime.Logger.Error(err.Error())
				return err
			}
			allInstancesSlave = false
		} else {
			// 获取 master_host and master_port
			masterHost, masterPortStr, _, _, err = cli.GetMasterData()
			if err != nil {
				return err
			}
			masterPort, _ := strconv.Atoi(masterPortStr)
			job.slavePairsMap[addr] = ReplicaItem{
				MasterIP:      masterHost,
				MasterPort:    masterPort,
				MasterAuth:    password,
				SlaveIP:       job.params.SlaveIP,
				SlavePort:     port,
				SlavePassword: password,
			}
		}
		job.slaveAddrMapCli[addr] = cli
	}
	if !allInstancesSlave {
		if !pairFileOK {
			err = fmt.Errorf("slave instances not all slave role,and %s not exist", job.getReplicaPairsFile())
			job.runtime.Logger.Error(err.Error())
			return err
		}
		err = job.getSlavePairsFromFile()
		if err != nil {
			return err
		}
	}
	err = job.writeSlavePairsToFile()
	if err != nil {
		return err
	}
	job.runtime.Logger.Info("all slave instances able to connect,(%+v)", instsAddrs)
	return nil
}

// allInstDisconnect 所有实例断开连接
func (job *ReplicasForceResync) allInstDisconnect() {
	for _, cli := range job.slaveAddrMapCli {
		cli.Close()
	}
}

// slaveofNoOneAndUtilToMaster slaveof on one and util to master
func (job *ReplicasForceResync) slaveofNoOneAndUtilToMaster() (err error) {
	var role, msg string
	var isClusterEnabled bool
	for _, cli := range job.slaveAddrMapCli {
		isClusterEnabled, err = cli.IsClusterEnabled()
		if err != nil {
			return err
		}
		if isClusterEnabled {
			msg = "cluster reset"
			job.runtime.Logger.Info(fmt.Sprintf("slave(%s) run cluster reset", cli.Addr))
			err = cli.ClusterReset()
		} else {
			msg = "slaveof no one"
			job.runtime.Logger.Info(fmt.Sprintf("slave(%s) run 'slaveof no one'", cli.Addr))
			_, err = cli.SlaveOf("no", "one")
		}
		if err != nil {
			return err
		}
		// wait util slave to master
		for {
			time.Sleep(3 * time.Second)
			role, err = cli.GetRole()
			if err != nil {
				return err
			}
			if role == consts.RedisMasterRole {
				job.runtime.Logger.Info("after %s, slave(%s) role:%s", msg, cli.Addr, role)
				break
			}
			job.runtime.Logger.Info("slave(%s) role:%s,retry...", cli.Addr, role)
		}
	}
	return nil
}

// slaveFlushall slaveof flushall
func (job *ReplicasForceResync) slaveFlushall() (err error) {
	cmd := []string{consts.CacheFlushAllRename}
	for _, cli := range job.slaveAddrMapCli {
		job.runtime.Logger.Info("slave(%s) flushall...", cli.Addr)
		_, err = cli.DoCommand(cmd, 0)
		if err != nil {
			return err
		}
	}
	return nil
}

func (job *ReplicasForceResync) clusterMeetAndUtilFinish() (err error) {
	var isClusterEnabled bool
	for _, cli := range job.slaveAddrMapCli {
		isClusterEnabled, err = cli.IsClusterEnabled()
		if err != nil {
			return err
		}
		if !isClusterEnabled {
			job.runtime.Logger.Info("slave(%s) cluster disbaled,skip cluster meet...", cli.Addr)
			continue
		}
		masterIP := job.slavePairsMap[cli.Addr].MasterIP
		masterPort := job.slavePairsMap[cli.Addr].MasterPort
		err = cli.ClusterMeetAndUtilFinish(masterIP, strconv.Itoa(masterPort))
		if err != nil {
			return err
		}
	}
	return nil
}

// ReplicaResync slaveof $master_ip $master_port and wait util master_link_status ok
func (job *ReplicasForceResync) ReplicaResync() (err error) {
	resyncTasks := make([]*ReplicaTask, 0, len(job.slavePairsMap))
	for _, item := range job.slavePairsMap {
		resyncTasks = append(resyncTasks, &ReplicaTask{
			ReplicaItem: item,
			runtime:     job.runtime,
		})
	}
	job.runtime.Logger.Info("slave start resync...resyncTasks:%s", util.ToString(resyncTasks))
	err = GroupRunReplicaTasksAndWait(resyncTasks, job.runtime)
	if err != nil {
		return err
	}
	return nil
}

// Retry times
func (job *ReplicasForceResync) Retry() uint {
	return 2
}

// Rollback rollback
func (job *ReplicasForceResync) Rollback() error {
	return nil
}
