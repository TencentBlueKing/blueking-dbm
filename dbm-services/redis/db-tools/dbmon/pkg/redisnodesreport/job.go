package redisnodesreport

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/glebarez/sqlite"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/models/myredis"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/report"
	"dbm-services/redis/db-tools/dbmon/util"
)

// globRedisNodesReportJob global var
var globRedisNodesReportJob *Job
var reportOnce sync.Once

// Job 节点变化上报任务
type Job struct {
	Conf     *config.Configuration `json:"conf"`
	sqdb     *gorm.DB
	Reporter report.Reporter `json:"-"`
	Err      error           `json:"-"`
}

// GetGlobRedisNodesReportJob 初始化节点变化上报任务
func GetGlobRedisNodesReportJob(conf *config.Configuration) *Job {
	reportOnce.Do(func() {
		globRedisNodesReportJob = &Job{
			Conf: conf,
		}
	})
	return globRedisNodesReportJob
}

func (job *Job) getSqDB() {
	var homeDir string
	homeDir, job.Err = os.Executable()
	if job.Err != nil {
		job.Err = fmt.Errorf("os.Executable failed,err:%v", job.Err)
		mylog.Logger.Info(job.Err.Error())
		return
	}
	homeDir = filepath.Dir(homeDir)
	dbname := filepath.Join(homeDir, "db", "redis_nodes.db")
	job.Err = util.MkDirsIfNotExists([]string{filepath.Join(homeDir, "db")})
	if job.Err != nil {
		mylog.Logger.Error(job.Err.Error())
		return
	}
	util.LocalDirChownMysql(filepath.Join(homeDir, "db"))
	job.sqdb, job.Err = gorm.Open(sqlite.Open(dbname), &gorm.Config{})
	if job.Err != nil {
		job.Err = fmt.Errorf("gorm.Open failed,err:%v,dbname:%s", job.Err, dbname)
		mylog.Logger.Info(job.Err.Error())
		return
	}
	job.Err = job.sqdb.AutoMigrate(&ClusterNodesSchema{})
	if job.Err != nil {
		job.Err = fmt.Errorf("AutoMigrate failed,err:%v", job.Err)
		mylog.Logger.Info(job.Err.Error())
		return
	}
}

// getReporter 上报者
func (job *Job) getReporter() {
	reportDir := filepath.Join(job.Conf.ReportSaveDir, "redis")
	util.MkDirsIfNotExists([]string{reportDir})
	util.LocalDirChownMysql(reportDir)
	reportFile := fmt.Sprintf(consts.RedisClusterNodesRepoter, time.Now().Local().Format(consts.FilenameDayLayout))
	job.Reporter, job.Err = report.NewFileReport(filepath.Join(reportDir, reportFile))
}

// ClusterNodesSchema TODO
type ClusterNodesSchema struct {
	BkBizID      string    `json:"bk_biz_id" gorm:"column:bk_biz_id;not null;default:''"`
	ImmuteDomain string    `json:"immute_domain" gorm:"primaryKey;column:immute_domain;not null;default:''"`
	ServerIP     string    `json:"server_ip" gorm:"primaryKey;not null;default:''"`
	ServerPort   int       `json:"server_port" gorm:"primaryKey;not null;default:0"`
	NodesData    string    `json:"nodes_data" gorm:"not null;default:'';type:text"`
	UpdatedAt    time.Time `json:"update_at" gorm:"autoUpdateTime"`
	CreatedAt    time.Time `json:"create_at" gorm:"autoUpdateTime"`
}

// TableName TODO
func (c *ClusterNodesSchema) TableName() string {
	return "cluster_nodes_update"
}

// Run new nodesreport tasks
func (job *Job) Run() {
	mylog.Logger.Info("redisnodesreport wakeup,start running...")
	defer func() {
		if job.Err != nil {
			mylog.Logger.Info(fmt.Sprintf("redisnodesreport end fail,err:%v", job.Err))
		} else {
			mylog.Logger.Info("redisnodesreport end succ")
		}
	}()
	job.Err = nil
	job.getSqDB()
	if job.Err != nil {
		return
	}
	job.getReporter()
	if job.Err != nil {
		return
	}
	var task *redisNodeTask
	for _, svrItem := range job.Conf.Servers {
		if !consts.IsRedisMetaRole(svrItem.MetaRole) {
			continue
		}
		for _, port := range svrItem.ServerPorts {
			task = &redisNodeTask{
				BkBizID:      svrItem.BkBizID,
				ImmuteDomain: svrItem.ClusterDomain,
				IP:           svrItem.ServerIP,
				Port:         port,
				sqdb:         job.sqdb,
				Reporter:     job.Reporter,
			}
			task.RunTask()
			if task.Err != nil {
				job.Err = task.Err
				break
			}
			if task.NodesHaveUpdate {
				break
			}
		}
	}
}

type redisNodeTask struct {
	BkBizID         string               `json:"bk_biz_id"`
	ImmuteDomain    string               `json:"immute_domain"`
	IP              string               `json:"ip"`
	Port            int                  `json:"port"`
	Password        string               `json:"password"`
	redisCli        *myredis.RedisClient `json:"-"`
	sqdb            *gorm.DB             `json:"-"`
	Reporter        report.Reporter      `json:"-"`
	lastRow         *ClusterNodesSchema  `json:"-"`
	Err             error                `json:"-"`
	NodesHaveUpdate bool
}

// RunTask TODO
func (rn *redisNodeTask) RunTask() {
	var clusterEnabled bool
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

	if !rn.isMyselfHaveSlots() {
		mylog.Logger.Debug(fmt.Sprintf("redis cluster not master or not have slots,addr:%s", rn.Addr()))
		// 非master,或者master没有负责slots,跳过
		return
	}
	if !rn.isClusterNodesUpdated() {
		return
	}
	rn.dbReplaceClusterNodes()
	if rn.Err != nil {
		return
	}
	rn.NodesHaveUpdate = true
	rn.reportClusterNodes()
}

// Addr TODO
func (rn *redisNodeTask) Addr() string {
	return rn.IP + ":" + strconv.Itoa(rn.Port)
}

func (rn *redisNodeTask) getRedisCli() {
	rn.Password, rn.Err = myredis.GetRedisPasswdFromConfFile(rn.Port)
	if rn.Err != nil {
		return
	}
	rn.redisCli, rn.Err = myredis.NewRedisClientWithTimeout(rn.Addr(), rn.Password, 0,
		consts.TendisTypeRedisInstance, 3*time.Second)
}

func (rn *redisNodeTask) closeRedisCli() {
	if rn.redisCli != nil {
		rn.redisCli.Close()
	}
}

func (rn *redisNodeTask) getNodesJoinStr(nodes []*myredis.ClusterNodeData) string {
	var builder strings.Builder
	for _, node := range nodes {
		nodeItem := node
		builder.WriteString(fmt.Sprintf("%s,%s,%d,%s,%s\n", nodeItem.NodeID, nodeItem.IP, nodeItem.Port, nodeItem.Role,
			nodeItem.LinkState))
	}
	return builder.String()
}

func (rn *redisNodeTask) getOldNodesJoinStr() string {
	var dbRows []*ClusterNodesSchema
	rn.Err = rn.sqdb.Where("immute_domain=? and server_ip=? and server_port=?", rn.ImmuteDomain,
		rn.IP, rn.Port).Find(&dbRows).Error
	if rn.Err != nil && gorm.ErrRecordNotFound == rn.Err {
		rn.Err = nil
		return ""
	} else if rn.Err != nil {
		mylog.Logger.Error(fmt.Sprintf("getOldNodesJoinStr failed,err:%v,immute_domain:%s,ip:%s,port:%d",
			rn.Err, rn.ImmuteDomain, rn.IP, rn.Port))
		return ""
	}
	if len(dbRows) == 0 {
		return ""
	}
	oldNodes, err := myredis.DecodeClusterNodes(dbRows[0].NodesData)
	if err != nil {
		rn.Err = err
		return ""
	}
	// 根据 NodeID 排序
	sort.SliceStable(oldNodes, func(i, j int) bool {
		return oldNodes[i].NodeID < oldNodes[j].NodeID
	})
	return rn.getNodesJoinStr(oldNodes)
}

// isMyselfHaveSlots '我'是否是master,且负责 slots
func (rn *redisNodeTask) isMyselfHaveSlots() bool {
	var selfNode *myredis.ClusterNodeData
	selfNode, rn.Err = rn.redisCli.GetMyself()
	if rn.Err != nil {
		return false
	}
	if selfNode.Role != consts.RedisMasterRole {
		return false
	}
	return len(selfNode.Slots) > 0
}

func (rn *redisNodeTask) isClusterNodesUpdated() bool {
	// 1. 通过 cluster nodes 获取集群节点信息
	// 2. 根据 NodeID 排序
	// 3. 拼接字符串: NodeID,IP,Port,Role,LinkState
	// 4. 从数据库中获取旧的 cluster nodes, 同样根据NodeID排序, 拼接字符串
	// 5. 对比两个字符串是否相同
	// 6. 如果不同, 返回 true
	var currNodes []*myredis.ClusterNodeData
	currNodes, rn.Err = rn.redisCli.GetClusterNodes()
	if rn.Err != nil {
		return false
	}
	// 2. 根据 NodeID 排序
	sort.SliceStable(currNodes, func(i, j int) bool {
		return currNodes[i].NodeID < currNodes[j].NodeID
	})
	// 3. 拼接字符串: NodeID,IP,Port,Role,LinkState
	currNodesStr := rn.getNodesJoinStr(currNodes)
	if rn.Err != nil {
		return false
	}
	mylog.Logger.Debug(fmt.Sprintf("isClusterNodesUpdated currNodesStr:%s", currNodesStr))
	// 4. 从数据库中获取旧的 cluster nodes, 同样根据NodeID排序, 拼接字符串
	oldNodesStr := rn.getOldNodesJoinStr()
	if rn.Err != nil {
		return false
	}
	mylog.Logger.Debug(fmt.Sprintf("isClusterNodesUpdated oldNodesStr:%s", oldNodesStr))
	// 5. 对比两个字符串是否相同
	if currNodesStr == oldNodesStr {
		return false
	}
	return true
}

func (rn *redisNodeTask) dbReplaceClusterNodes() {
	var rawNodes string
	rawNodes, rn.Err = rn.redisCli.InstanceClient.ClusterNodes(context.Background()).Result()
	if rn.Err != nil {
		return
	}
	mylog.Logger.Debug("start dbReplaceClusterNodes...")
	rn.lastRow = &ClusterNodesSchema{
		BkBizID:      rn.BkBizID,
		ImmuteDomain: rn.ImmuteDomain,
		ServerIP:     rn.IP,
		ServerPort:   rn.Port,
		NodesData:    rawNodes,
	}
	rn.lastRow.UpdatedAt = time.Now().Local()
	rn.lastRow.CreatedAt = time.Now().Local()
	rn.Err = rn.sqdb.Clauses(clause.OnConflict{
		UpdateAll: true,
	}).Create(rn.lastRow).Error
	if rn.Err != nil {
		mylog.Logger.Error(fmt.Sprintf("dbReplaceClusterNodes failed,err:%v", rn.Err))
		return
	}
}

type clusterNodesReport struct {
	ClusterNodesSchema
	UpdateAt string `json:"update_at"`
	CreateAt string `json:"create_at"`
}

func (rn *redisNodeTask) reportClusterNodes() {
	if rn.Reporter == nil {
		return
	}
	reportRow := &clusterNodesReport{
		ClusterNodesSchema: *rn.lastRow,
	}
	reportRow.UpdateAt = rn.lastRow.UpdatedAt.Local().Format(consts.UnixtimeLayout)
	reportRow.CreateAt = rn.lastRow.CreatedAt.Local().Format(consts.UnixtimeLayout)
	tmpBytes, _ := json.Marshal(reportRow)
	mylog.Logger.Debug(fmt.Sprintf("start reportClusterNodes:%s", string(tmpBytes)))
	rn.Reporter.AddRecord(string(tmpBytes)+"\n", true)
}
