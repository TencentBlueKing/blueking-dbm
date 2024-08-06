// Package failednodehandle TODO
package failednodehandle

import (
	"context"
	"fmt"
	"strconv"
	"sync"
	"time"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/models/myredis"
	"dbm-services/redis/db-tools/dbmon/models/mysqlite"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
)

var (
	// 第一次发现失败
	statusFirstFindFaied = "first_find_failed"
	// 恢复成running状态
	statusRecoverRunning = "recover_running"
	// 不存在于cluster nodes中
	statusNotInClusterNodes = "not_in_cluster_nodes"
	// 成功执行cluster forget
	statusSuccessForget = "success_forget"
)

// FailedNodeHandleSchema  failed 节点处理
type FailedNodeHandleSchema struct {
	BkBizID        string    `json:"bk_biz_id" gorm:"type:varchar(64);column:bk_biz_id;not null;default:''"`
	ImmuteDomain   string    `json:"immute_domain" gorm:"type:varchar(128);column:immute_domain;not null;default:'';primaryKey"`
	MyServerIP     string    `json:"my_server_ip" gorm:"type:varchar(128);not null;default:'';primaryKey"`
	MyServerPort   int       `json:"my_server_port" gorm:"not null;default:0;primaryKey"`
	FailedNodeID   string    `json:"failed_node_id" gorm:"type:varchar(128);not null;default:'';primaryKey"`
	FailedNodeIP   string    `json:"failed_node_ip" gorm:"type:varchar(128);not null;default:''"`
	FailedNodePort int       `json:"failed_node_port" gorm:"not null;default:0"`
	FailedRawLine  string    `json:"failed_raw_line" gorm:"not null;default:''"`
	HandleStatus   string    `json:"handle_status" gorm:"type:varchar(128);not null;default:''"`
	UpdateAt       time.Time `json:"update_at" gorm:"autoUpdateTime"`
	CreateAt       time.Time `json:"create_at"`
}

// TableName TODO
func (c *FailedNodeHandleSchema) TableName() string {
	return "failed_node_handle"
}

// globFailedNodeHandleJob global var
var globFailedNodeHandleJob *Job
var handleOnce sync.Once

// Job TODO
type Job struct {
	Conf *config.Configuration `json:"conf"`
	sqdb *gorm.DB
	Err  error
}

// GetGlobFailedNodeHandleJob 初始化failed节点处理任务
func GetGlobFailedNodeHandleJob(conf *config.Configuration) *Job {
	handleOnce.Do(func() {
		globFailedNodeHandleJob = &Job{
			Conf: conf,
		}
	})
	return globFailedNodeHandleJob
}

func (job *Job) getSqDB() {
	job.sqdb, job.Err = mysqlite.GetLocalSqDB()
	if job.Err != nil {
		return
	}
	job.Err = job.sqdb.AutoMigrate(&FailedNodeHandleSchema{})
	if job.Err != nil {
		job.Err = fmt.Errorf("ClusterNodesSchema AutoMigrate failed,err:%v", job.Err)
		mylog.Logger.Info(job.Err.Error())
		return
	}
}
func (job *Job) closeDB() {
	mysqlite.CloseDB(job.sqdb)
}

// Run Command Run
func (job *Job) Run() {
	mylog.Logger.Info("failednodehandle wakeup,start running...")
	defer func() {
		if job.Err != nil {
			mylog.Logger.Info(fmt.Sprintf("failednodehandle end fail,err:%v", job.Err))
		} else {
			mylog.Logger.Info("failednodehandle end succ")
		}
	}()
	job.Err = nil
	job.getSqDB()
	if job.Err != nil {
		return
	}
	defer job.closeDB()
	defer job.delete30DaysOldFailedNodeRows()
	var task redisNodeTask
	for _, svrItem := range job.Conf.Servers {
		if !consts.IsRedisMetaRole(svrItem.MetaRole) {
			continue
		}
		for _, port := range svrItem.ServerPorts {
			task = redisNodeTask{
				BkBizID:      svrItem.BkBizID,
				ImmuteDomain: svrItem.ClusterDomain,
				IP:           svrItem.ServerIP,
				Port:         port,
				Password:     "",
				sqdb:         job.sqdb,
			}
			task.RunTask()
		}
	}
}

func (job *Job) delete30DaysOldFailedNodeRows() {
	// delete from failed_node_handle
	// where create_at < datetime('now', '-30 days')
	job.Err = job.sqdb.Where("create_at < datetime('now', '-30 days')").Delete(&FailedNodeHandleSchema{}).Error
	if job.Err != nil {
		mylog.Logger.Error(fmt.Sprintf("delete30DaysOldFailedNodeRows failed,err:%v", job.Err))
		return
	}
}

type redisNodeTask struct {
	BkBizID      string
	ImmuteDomain string
	IP           string
	Port         int
	Password     string               `json:"password"`
	redisCli     *myredis.RedisClient `json:"-"`
	sqdb         *gorm.DB
	Err          error
}

// Addr TODO
func (rn *redisNodeTask) Addr() string {
	return rn.IP + ":" + strconv.Itoa(rn.Port)
}

// RunTask TODO
func (rn *redisNodeTask) RunTask() {
	var clusterEnabled bool
	var ok bool
	var nowIDMapToNodes map[string]*myredis.ClusterNodeData
	rn.getRedisCli()
	if rn.Err != nil {
		return
	}
	defer rn.closeRedisCli()
	clusterEnabled, rn.Err = rn.redisCli.IsClusterEnabled()
	if rn.Err != nil {
		return
	}
	if !clusterEnabled {
		mylog.Logger.Debug(fmt.Sprintf("redis cluster not enabled,addr:%s", rn.Addr()))
		// 非集群模式,跳过
		return
	}
	nowIDMapToNodes, rn.Err = rn.redisCli.GetNodeIDMapToNodes()
	if rn.Err != nil {
		return
	}
	oldFailedIDToRows := rn.getOldFailedNodeRows()
	if rn.Err != nil {
		return
	}
	// 遍历 oldFailedIDToRows,处理历史failed节点信息,根据 nowIDMapToNodes 中内容做处理
	var tempNodeData *myredis.ClusterNodeData
	for id, oldRow := range oldFailedIDToRows {
		tempNodeData, ok = nowIDMapToNodes[id]
		if !ok {
			// 该节点已经不在集群中,则修改 oldRow 的状态为 not_in_cluster_nodes
			oldRow.HandleStatus = statusNotInClusterNodes
			rn.replaceFailedNodeRow(oldRow)
			continue
		}
		// 该节点在集群中,且重新恢复运行了则修改 oldRow 的状态为 running
		if myredis.IsRunningNode(tempNodeData) {
			oldRow.HandleStatus = statusRecoverRunning
			oldRow.FailedRawLine = tempNodeData.RawLine
			rn.replaceFailedNodeRow(oldRow)
			continue
		}
		// 该节点在集群中,依然是failed状态,判断create_at时间是否超过了半小时,如果超过了,则所有running的节点对其执行cluster forget
		if time.Now().Local().Sub(oldRow.CreateAt) > 30*time.Minute {
			rn.forgetClusterNode(nowIDMapToNodes, oldRow.FailedNodeID)
			oldRow.HandleStatus = statusSuccessForget
			rn.replaceFailedNodeRow(oldRow)
			continue
		}
	}
	// 遍历 nowIDMapToNodes 非running的节点
	// 如果同时也不在 oldFailedIDToRows中,则新增一行
	for id, nowNodeData := range nowIDMapToNodes {
		if myredis.IsRunningNode(nowNodeData) {
			// running状态的node,忽略
			continue
		}
		// 非running的node,同时不在 oldFailedIDToRows中,则新增一行
		oldRow, ok := oldFailedIDToRows[id]
		if !ok {
			oldRow = &FailedNodeHandleSchema{
				BkBizID:        rn.BkBizID,
				ImmuteDomain:   rn.ImmuteDomain,
				MyServerIP:     rn.IP,
				MyServerPort:   rn.Port,
				FailedNodeID:   nowNodeData.NodeID,
				FailedNodeIP:   nowNodeData.IP,
				FailedNodePort: nowNodeData.Port,
				FailedRawLine:  nowNodeData.RawLine,
				HandleStatus:   statusFirstFindFaied,
				CreateAt:       time.Now().Local(),
				UpdateAt:       time.Now().Local(),
			}
			rn.replaceFailedNodeRow(oldRow)
			continue
		}
	}
}

func (rn *redisNodeTask) getRedisCli() {
	rn.Password, rn.Err = myredis.GetRedisPasswdFromConfFile(rn.Port)
	if rn.Err != nil {
		return
	}
	rn.redisCli, rn.Err = myredis.NewRedisClientWithTimeout(rn.Addr(), rn.Password, 0,
		consts.TendisTypeRedisInstance, 10*time.Second)
}

func (rn *redisNodeTask) closeRedisCli() {
	if rn.redisCli != nil {
		rn.redisCli.Close()
	}
}

func (rn *redisNodeTask) getOldFailedNodeRows() (failedNodeIDToRow map[string]*FailedNodeHandleSchema) {
	// select * from failed_node_handle
	// where  handle_status= 'first_find_failed' and
	// my_server_ip='' and my_server_port =0 and immute_domain='xxx'
	var failedNodeRows []*FailedNodeHandleSchema
	sql := rn.sqdb.ToSQL(func(tx *gorm.DB) *gorm.DB {
		return tx.Model(&FailedNodeHandleSchema{}).
			Where("immute_domain=? and my_server_ip=? and my_server_port=? and handle_status=?",
				rn.ImmuteDomain, rn.IP, rn.Port, statusFirstFindFaied).
			Find(&[]FailedNodeHandleSchema{})
	})
	mylog.Logger.Debug(fmt.Sprintf("getOldFailedNodeRows sql:%s", sql))
	rn.Err = rn.sqdb.Where("immute_domain=? and my_server_ip=? and my_server_port=? and handle_status=?",
		rn.ImmuteDomain, rn.IP, rn.Port, statusFirstFindFaied).Find(&failedNodeRows).Error
	if rn.Err != nil && gorm.ErrRecordNotFound == rn.Err {
		rn.Err = nil
		return
	} else if rn.Err != nil {
		mylog.Logger.Error(fmt.Sprintf("getOldFailedNodeRows failed,err:%v,sql:%s",
			rn.Err, sql))
		return
	}
	if len(failedNodeRows) == 0 {
		mylog.Logger.Debug(fmt.Sprintf("getOldFailedNodeRows not found,sql:%s", sql))
		return
	}
	failedNodeIDToRow = make(map[string]*FailedNodeHandleSchema)
	for _, item := range failedNodeRows {
		dbRow := item
		failedNodeIDToRow[dbRow.FailedNodeID] = dbRow
	}
	return
}

func (rn *redisNodeTask) replaceFailedNodeRow(row *FailedNodeHandleSchema) {
	if row == nil {
		return
	}
	row.UpdateAt = time.Now().Local()
	rn.Err = rn.sqdb.Clauses(clause.OnConflict{
		UpdateAll: true,
	}).Create(row).Error
	if rn.Err != nil {
		mylog.Logger.Error(fmt.Sprintf("replaceFailedNodeRow failed,err:%v", rn.Err))
		return
	}
}

// forgetClusterNode 集群中running node并发执行cluster forget
func (rn *redisNodeTask) forgetClusterNode(nowIDMapToNodes map[string]*myredis.ClusterNodeData, toForgetID string) {
	var wg sync.WaitGroup
	for _, nowNodeData := range nowIDMapToNodes {
		if !myredis.IsRunningNode(nowNodeData) {
			continue
		}
		wg.Add(1)
		go func(tempNodeData *myredis.ClusterNodeData) {
			defer wg.Done()
			redisCli, err := myredis.NewRedisClientWithTimeout(tempNodeData.Addr, rn.Password, 0,
				consts.TendisTypeRedisInstance, 10*time.Second)
			if err != nil {
				return
			}
			defer redisCli.Close()
			mylog.Logger.Info(fmt.Sprintf("redis %s cluster forget %s", tempNodeData.Addr, toForgetID))
			err = redisCli.InstanceClient.ClusterForget(context.TODO(), toForgetID).Err()
			if err != nil {
				mylog.Logger.Error(fmt.Sprintf("redis %s cluster forget %s fail,err:%v", tempNodeData.Addr, toForgetID, err))
			}
		}(nowNodeData)
	}
	wg.Wait()
}
