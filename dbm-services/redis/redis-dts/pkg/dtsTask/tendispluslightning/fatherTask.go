package tendispluslightning

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"path/filepath"
	"strings"

	"go.uber.org/zap"

	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/tclog"
	"dbm-services/redis/redis-dts/util"
)

// LightningFatherTask lightning father task
type LightningFatherTask struct {
	RowData            *tendisdb.TbTendisplusLightningTask `json:"rowData"`
	valueChangedFields []string                            // 值已变化的字段名
	TaskDir            string                              `json:"taskDir"`
	Logger             *zap.Logger                         `json:"-"`
	Err                error                               `json:"-"`
}

// NewLightningFatherTask new lightning father task
func NewLightningFatherTask(rowData *tendisdb.TbTendisplusLightningTask) LightningFatherTask {
	return LightningFatherTask{
		RowData:            rowData,
		valueChangedFields: []string{},
	}
}

// SetStatus 设置status的值
func (t *LightningFatherTask) SetStatus(status int) {
	t.RowData.Status = status
	t.valueChangedFields = append(t.valueChangedFields, "Status")
}

// SetCosFileSize 设置cosFileSize的值
func (task *LightningFatherTask) SetCosFileSize(cosFileSize int64) {
	task.RowData.CosFileSize = cosFileSize
	task.valueChangedFields = append(task.valueChangedFields, "CosFileSize")
}

// SetMessage 设置message的值
func (t *LightningFatherTask) SetMessage(format string, args ...interface{}) {
	if len(args) == 0 {
		t.RowData.Message = format
	} else {
		t.RowData.Message = fmt.Sprintf(format, args...)
	}
	t.valueChangedFields = append(t.valueChangedFields, "Message")
}

// SetOperateType set operateType
func (t *LightningFatherTask) SetOperateType(op string) {
	t.RowData.OperateType = op
	t.valueChangedFields = append(t.valueChangedFields, "OperateType")
}

// SetTaskType 设置task_type的值
func (t *LightningFatherTask) SetTaskType(taskType string) {
	t.RowData.TaskType = taskType
	t.valueChangedFields = append(t.valueChangedFields, "TaskType")
}

// UpdateRow update tendisdb相关字段(值变化了的字段)
func (t *LightningFatherTask) UpdateRow() {
	if len(t.valueChangedFields) == 0 {
		return
	}
	t.RowData.UpdateFieldsValues(t.valueChangedFields, t.Logger)
	t.valueChangedFields = []string{}
}

// Init 初始化
func (t *LightningFatherTask) Init() {
	defer func() {
		if t.Err != nil {
			t.SetStatus(-1)
			t.SetMessage(t.Err.Error())
		} else {
			t.SetStatus(1) // 更新为running状态
		}
		t.UpdateRow()
	}()
	t.Err = t.InitLogger()
	if t.Err != nil {
		return
	}
	if t.RowData.OperateType == constvar.RedisForceKillTaskTodo {
		t.RowData.OperateType = constvar.RedisForceKillTaskSuccess
		t.Err = fmt.Errorf(constvar.RedisForceKillTaskSuccess + "...")
		return
	}
}

// InitTaskDir 初始化本地任务目录
func (t *LightningFatherTask) InitTaskDir() error {
	currExecPath, err := util.CurrentExecutePath()
	if err != nil {
		return err
	}
	domainPort := strings.Split(t.RowData.DstCluster, ":")
	subDir := fmt.Sprintf("tasks/%d_%s_%s/%s", t.RowData.TicketID,
		domainPort[0], domainPort[1], t.RowData.TaskId)
	t.TaskDir = filepath.Join(currExecPath, subDir)
	err = util.MkDirIfNotExists(t.TaskDir)
	if err != nil {
		return err
	}
	return nil
}

// InitLogger 初始化日志文件logger
func (t *LightningFatherTask) InitLogger() error {
	err := t.InitTaskDir()
	if err != nil {
		return nil
	}
	logFile := fmt.Sprintf("task_%s.log", t.RowData.TaskId)
	fullPath := filepath.Join(t.TaskDir, logFile)
	t.Logger = tclog.NewFileLogger(fullPath)
	return nil
}

// GetLocalCosFile 获取本地cos文件保存路径
func (t *LightningFatherTask) GetLocalCosFile() string {
	return t.RowData.TaskId + ".cos_binary"
}

// GetSplitOutputDir 获取split输出目录
func (t *LightningFatherTask) GetSplitOutputDir() string {
	return "split_outout_dir"
}

// GetSlaveNodeSstDir 获取slave节点sst文件保存目录
func (t *LightningFatherTask) GetSlaveNodeSstDir(slaveIP, slavePort string) string {
	// return filepath.Join("slave_nodes_sst_dir", slaveIP+"_"+slavePort)
	return "slave_nodes_sst_dir_" + slaveIP + "_" + slavePort + "_" + t.RowData.TaskId
}

type clusterNodeItem struct {
	MasterAddr          string `json:"master_addr"`
	SlaveAddr           string `json:"slave_addr"`
	Slots               string `json:"slots"`
	RedisPasswordEncode string `json:"redis_password_encode"`
	RedisPassword       string `json:"redis_password"`
}

// GetSlaveIpPort 获取slave的ip和port
func (c *clusterNodeItem) GetSlaveIpPort() (ip, port string, err error) {
	if c.SlaveAddr == "" {
		err = fmt.Errorf("slave_addr is empty,data:%s", util.ToString(c))
		return
	}
	tempList := strings.Split(c.SlaveAddr, ":")
	if len(tempList) != 2 {
		err = fmt.Errorf("slave_addr:%s format error,data:%s", c.SlaveAddr, util.ToString(c))
		return
	}
	ip = tempList[0]
	port = tempList[1]
	return
}

// GetDstClusterNodes 获取目标集群 cluster nodes信息
func (task *LightningFatherTask) GetDstClusterNodes() (clusterNodes []*clusterNodeItem) {
	var lightningJobsRows []*tendisdb.TbTendisplusLightningJob
	var passwordDecode []byte
	lightningJobsRows, task.Err = tendisdb.GetLightningJob(task.RowData.TicketID, task.RowData.DstCluster, task.Logger)
	if task.Err != nil {
		return
	}
	if len(lightningJobsRows) == 0 {
		task.Err = fmt.Errorf("获取ticket_id:%d dst_cluster:%s cluster nodes信息为空",
			task.RowData.TicketID,
			task.RowData.DstCluster)
		task.Logger.Error(task.Err.Error())
		return
	}
	task.Err = json.Unmarshal([]byte(lightningJobsRows[0].ClusterNodes), &clusterNodes)
	if task.Err != nil {
		task.Err = fmt.Errorf("unmarshal clusterNodes:%s fail,err:%v", lightningJobsRows[0].ClusterNodes, task.Err)
		task.Logger.Error(task.Err.Error())
		return
	}
	for _, tmp := range clusterNodes {
		clusterNode := tmp
		passwordDecode, task.Err = base64.StdEncoding.DecodeString(clusterNode.RedisPasswordEncode)
		if task.Err != nil {
			task.Err = fmt.Errorf("base64 decode redis password:%s fail,err:%v", clusterNode.RedisPasswordEncode, task.Err)
			task.Logger.Error(task.Err.Error())
			return
		}
		clusterNode.RedisPassword = string(passwordDecode)
		task.Logger.Info(fmt.Sprintf("slave_addr:%s encodePassword:%s password:%s",
			clusterNode.SlaveAddr, clusterNode.RedisPasswordEncode, clusterNode.RedisPassword))
	}
	return
}
