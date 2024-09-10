package tendisdb

import (
	"encoding/json"
	"fmt"
	"net/http"
	"reflect"
	"regexp"
	"sync"

	"github.com/spf13/viper"
	"go.uber.org/zap"

	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/scrdbclient"
)

var (
	lightningTaskFiledToColunm map[string]string // struct filedName map to colunmName
	lightningTaskOnce          sync.Once
)

/*
create table  tb_tendisplus_lightning_task (
task_id varchar(64) NOT NULL  primary key,
ticket_id bigint(20) NOT NULL,
user varchar(64) NOT NULL,
bk_biz_id varchar(64) NOT NULL,
bk_cloud_id bigint(20) NOT NULL,
cos_key varchar(128) NOT NULL,
cos_file_size bigint(20) NOT NULL,
dts_server varchar(128) NOT NULL,
dst_cluster varchar(128) NOT NULL,
dst_cluster_id bigint(20) NOT NULL,
dst_cluster_priority int(11) NOT NULL,
dst_zonename varchar(128) NOT NULL,
task_type varchar(128) NOT NULL,
operate_type varchar(128) NOT NULL,
status int(11) NOT NULL,
message longtext NOT NULL,
create_time datetime(6) NOT NULL,
update_time datetime(6) NOT NULL,
key idx_update_time(update_time),
key idx_dst_cluster_id(dst_cluster_id),
key idx_user(user),
key idx_ticket_cluster(ticket_id,dst_cluster_id)
)ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
*/

// TbTendisplusLightningTask TODO
type TbTendisplusLightningTask struct {
	// gorm
	TaskId             string `gorm:"column:task_id;type:varchar(64);primary_key" json:"task_id"`
	TicketID           int64  `gorm:"column:ticket_id;type:bigint(20) unsigned;not null" json:"ticket_id"`
	User               string `gorm:"column:user;type:varchar(64);not null" json:"user"`
	BkBizID            string `gorm:"column:bk_biz_id;type:varchar(64);not null" json:"bk_biz_id"`
	BkCloudID          int64  `gorm:"column:bk_cloud_id;type:bigint(20) unsigned;not null" json:"bk_cloud_id"`
	CosKey             string `gorm:"column:cos_key;type:varchar(128);not null" json:"cos_key"`
	CosFileSize        int64  `gorm:"column:cos_file_size;type:bigint(20) unsigned;not null" json:"cos_file_size"`
	DtsServer          string `gorm:"column:dts_server;type:varchar(128);not null" json:"dts_server"`
	DstCluster         string `gorm:"column:dst_cluster;type:varchar(128);not null" json:"dst_cluster"`
	DstClusterID       int64  `gorm:"column:dst_cluster_id;type:bigint(20) unsigned;not null" json:"dst_cluster_id"`
	DstClusterPriority int    `gorm:"column:dst_cluster_priority;type:int(11);not null" json:"dst_cluster_priority"`
	DstZonename        string `gorm:"column:dst_zonename;type:varchar(128);not null" json:"dst_zonename"`
	TaskType           string `gorm:"column:task_type;type:varchar(128);not null" json:"task_type"`
	OperateType        string `gorm:"column:operate_type;type:varchar(128);not null" json:"operate_type"`
	Status             int    `gorm:"column:status;type:int(11);not null" json:"status"`
	Message            string `gorm:"column:message;type:longtext;not null" json:"message"`
	CreateTime         string `gorm:"column:create_time;type:datetime(6);not null" json:"create_time"`
	UpdateTime         string `gorm:"column:update_time;type:datetime(6);not null" json:"update_time"`
}

// TableName 表名
func (t *TbTendisplusLightningTask) TableName() string {
	return "tb_tendisplus_lightning_task"
}

// TaskLockKey keyname
func (t *TbTendisplusLightningTask) TaskLockKey() string {
	return fmt.Sprintf("Lightning_task_lock_%d_%s_%s",
		t.TicketID, t.DstCluster, t.TaskId,
	)
}

// LightningDtsSvrMigratingTasks  获取dtsserver正在迁移的task,与task对应多少dataSize
// 对Tendisplus Lightning 来说,'迁移中'指处于 status=1 状态的task
func LightningDtsSvrMigratingTasks(bkCloudID int64, dtsSvr string, taskTypes []string,
	logger *zap.Logger) (tasks []*TbTendisplusLightningTask, dataSize uint64, err error) {
	var cli01 *scrdbclient.Client
	var subURL string
	var data *scrdbclient.APIServerResponse
	cli01, err = scrdbclient.NewClient(viper.GetString("serviceName"), logger)
	if err != nil {
		return
	}
	tasks = []*TbTendisplusLightningTask{}
	if cli01.GetServiceName() == constvar.BkDbm {
		subURL = constvar.DbmLightningDtsServerMigratingTasksURL
	}
	type lightningDtsSvrMigratingTasksReq struct {
		BkCloudID int64    `json:"bk_cloud_id"`
		DtsServer string   `json:"dts_server"`
		TaskTypes []string `json:"task_types"`
	}
	param := lightningDtsSvrMigratingTasksReq{
		BkCloudID: bkCloudID,
		DtsServer: dtsSvr,
		TaskTypes: taskTypes,
	}
	data, err = cli01.Do(http.MethodPost, subURL, param)
	if err != nil {
		return
	}
	err = json.Unmarshal(data.Data, &tasks)
	if err != nil {
		err = fmt.Errorf("LightningDtsSvrMigratingTasks unmarshal data fail,err:%v,resp.Data:%s,subURL:%s,param:%+v",
			err.Error(), string(data.Data), subURL, param)
		logger.Error(err.Error())
		return
	}
	dataSize = 0
	for _, tmp := range tasks {
		task := tmp
		dataSize = dataSize + uint64(task.CosFileSize)
	}
	return
}

// LightningLast30DaysToExecuteTasks 用于获取最近一个月本地等待执行的lightning tasks
func LightningLast30DaysToExecuteTasks(
	bkCloudID int64,
	dtsServer, taskType string,
	status, limit int,
	logger *zap.Logger) (tasks []*TbTendisplusLightningTask, err error) {
	var cli01 *scrdbclient.Client
	var subURL string
	var data *scrdbclient.APIServerResponse
	cli01, err = scrdbclient.NewClient(viper.GetString("serviceName"), logger)
	if err != nil {
		return
	}
	type lightningLast30DaysToExecTasksReq struct {
		BkCloudID int64  `json:"bk_cloud_id"`
		DtsServer string `json:"dts_server"`
		TaskType  string `json:"task_type"`
		Status    int    `json:"status"`
		Limit     int    `json:"limit"`
	}
	tasks = []*TbTendisplusLightningTask{}
	if cli01.GetServiceName() == constvar.BkDbm {
		subURL = constvar.DbmLightningLast30DaysToExecuteTasksURL
	}
	param := lightningLast30DaysToExecTasksReq{
		DtsServer: dtsServer,
		TaskType:  taskType,
		Status:    status,
		Limit:     limit,
	}
	data, err = cli01.Do(http.MethodPost, subURL, param)
	if err != nil {
		return
	}
	err = json.Unmarshal(data.Data, &tasks)
	if err != nil {
		err = fmt.Errorf("LightningLast30DaysToExecuteTasks unmarshal data fail,err:%v,resp.Data:%s,subURL:%s,param:%+v",
			err.Error(), string(data.Data), subURL, param)
		logger.Error(err.Error())
		return
	}
	return
}

// LightningLast30DaysToScheduleJobs 获取最近30天待调度的Jobs
// jobs必须满足: 有一个待调度的task.dataSize < maxDataSize
func LightningLast30DaysToScheduleJobs(bkCloudID int64, maxDataSize int64, zoneName string,
	logger *zap.Logger) (jobs []*TbTendisplusLightningTask, err error) {
	var cli01 *scrdbclient.Client
	var subURL string
	var data *scrdbclient.APIServerResponse
	cli01, err = scrdbclient.NewClient(viper.GetString("serviceName"), logger)
	if err != nil {
		return
	}
	type lightningLast30DaysToScheduleJobsReq struct {
		BkCloudID   int64  `json:"bk_cloud_id"`
		MaxDataSize int64  `json:"max_data_size"`
		ZoneName    string `json:"zone_name"`
	}
	jobs = []*TbTendisplusLightningTask{}
	if cli01.GetServiceName() == constvar.BkDbm {
		subURL = constvar.DbmLightningLast30DaysToScheduleJobsURL
	}
	param := lightningLast30DaysToScheduleJobsReq{
		BkCloudID:   bkCloudID,
		MaxDataSize: maxDataSize,
		ZoneName:    zoneName,
	}
	data, err = cli01.Do(http.MethodPost, subURL, param)
	if err != nil {
		return
	}
	err = json.Unmarshal(data.Data, &jobs)
	if err != nil {
		err = fmt.Errorf("LightningLast30DaysToScheduleJobs unmarshal data fail,err:%v,resp.Data:%s,subURL:%s,param:%+v",
			err.Error(), string(data.Data), subURL, param)
		logger.Error(err.Error())
		return
	}
	return
}

// LightningJobToScheduleTasks 获取job中所有待调度的task
// ticketId、dstCluster确定一个job
// dtsserver='1.1.1.1' and status=0 and task_type="" 代表 '未执行'
// 一个job可能部分task执行,部分未执行;
// 根据权重src_weight排序,权重越小,越前面执行
func LightningJobToScheduleTasks(ticketID int64, dstCluster string,
	logger *zap.Logger) (tasks []*TbTendisplusLightningTask, err error) {
	if ticketID == 0 || dstCluster == "" {
		err = fmt.Errorf("ticketID:%d or dstCluster:%s cann't be empty",
			ticketID, dstCluster)
		logger.Error(err.Error())
		return tasks, err
	}
	var cli01 *scrdbclient.Client
	var subURL string
	var data *scrdbclient.APIServerResponse
	cli01, err = scrdbclient.NewClient(viper.GetString("serviceName"), logger)
	if err != nil {
		return
	}
	type lightningJobToScheduleTasks struct {
		TicketID   int64  `json:"ticket_id"`
		DstCluster string `json:"dst_cluster"`
	}
	tasks = []*TbTendisplusLightningTask{}
	if cli01.GetServiceName() == constvar.BkDbm {
		subURL = constvar.DbmLightningJobToScheduleTasksURL
	}
	param := lightningJobToScheduleTasks{
		TicketID:   ticketID,
		DstCluster: dstCluster,
	}
	data, err = cli01.Do(http.MethodPost, subURL, param)
	if err != nil {
		return
	}
	err = json.Unmarshal(data.Data, &tasks)
	if err != nil {
		err = fmt.Errorf("LightningJobToScheduleTasks unmarshal data fail,err:%v,resp.Data:%s,subURL:%s,param:%+v",
			err.Error(), string(data.Data), subURL, param)
		logger.Error(err.Error())
		return
	}
	return
}

// LightningTaskByID 根据id获得task详细信息
func LightningTaskByID(taskID string, logger *zap.Logger) (task *TbTendisplusLightningTask, err error) {
	if logger == nil {
		err = fmt.Errorf("LightningTaskByID logger cannot be nil")
		return
	}
	var cli01 *scrdbclient.Client
	var subURL string
	var data *scrdbclient.APIServerResponse
	cli01, err = scrdbclient.NewClient(viper.GetString("serviceName"), logger)
	if err != nil {
		return
	}
	type lightningTaskRowByIDReq struct {
		TaskID string `json:"task_id"`
	}

	task = &TbTendisplusLightningTask{}
	if cli01.GetServiceName() == constvar.BkDbm {
		subURL = constvar.DbmLightningTaskRowByIDURL
	}
	param := lightningTaskRowByIDReq{
		TaskID: taskID,
	}
	data, err = cli01.Do(http.MethodPost, subURL, param)
	if err != nil {
		return
	}
	if len(data.Data) == 4 && string(data.Data) == "null" {
		return nil, nil
	}
	err = json.Unmarshal(data.Data, task)
	if err != nil {
		err = fmt.Errorf("LightningTaskByID unmarshal data fail,err:%v,resp.Data:%s,subURL:%s,param:%+v",
			err.Error(), string(data.Data), subURL, param)
		logger.Error(err.Error())
		return
	}
	return
}

// LightningTaskStructFieldsToColumns 获取 TbTendisplusLightningTask 字段名 到 列名之间的对应关系
// 如 filedNames=["BillID","App","User","SrcIP"] 对应的 columnNames=["bill_id","app","user","src_ip"]
func LightningTaskStructFieldsToColumns(fieldNames []string, logger *zap.Logger) (columnNames []string, err error) {
	lightningTaskOnce.Do(func() {
		t01 := TbTendisplusLightningTask{}
		reg01 := regexp.MustCompile(`column:(\w+)`)
		getType := reflect.TypeOf(t01)
		lightningTaskFiledToColunm = make(map[string]string, getType.NumField())
		for i := 0; i < getType.NumField(); i++ {
			field := getType.Field(i)
			gormTag := string(field.Tag.Get("gorm"))
			l01 := reg01.FindStringSubmatch(gormTag)
			if len(l01) < 2 {
				continue
			}
			lightningTaskFiledToColunm[field.Name] = l01[1]
		}
	})
	columnNames = make([]string, 0, len(fieldNames))
	for _, field01 := range fieldNames {
		colName, ok := lightningTaskFiledToColunm[field01]
		if ok == false {
			err = fmt.Errorf("struct TbTendisplusLightningTask have no field:%s", colName)
			logger.Error(err.Error())
			return
		}
		columnNames = append(columnNames, colName)
	}
	return
}

// GetFieldsValue 根据 字段名 从task中获取其字段values
// 如 filedNames=["DtsServer","CosFileSize"] 其对应值为 ret=["1.1.1.1",11111]
func (t *TbTendisplusLightningTask) GetFieldsValue(fieldNames []string, logger *zap.Logger) (ret []interface{},
	err error) {
	_, err = LightningTaskStructFieldsToColumns(fieldNames, logger)
	if err != nil {
		return
	}
	ret = make([]interface{}, 0, len(fieldNames))
	getValue := reflect.ValueOf(t)
	for _, field01 := range fieldNames {
		val01 := reflect.Indirect(getValue).FieldByName(field01)
		ret = append(ret, val01.Interface())
	}
	return
}

// GetColToValByFields 根据struct fieldName 生成 表列名=>值 之间的对应关系
func (t *TbTendisplusLightningTask) GetColToValByFields(fieldNames []string, logger *zap.Logger) (
	colToVal map[string]interface{}, err error) {
	var columnNames []string
	var values []interface{}
	columnNames, err = LightningTaskStructFieldsToColumns(fieldNames, logger)
	if err != nil {
		return
	}
	values, err = t.GetFieldsValue(fieldNames, logger)
	if err != nil {
		return
	}
	colToVal = make(map[string]interface{}, len(fieldNames))
	for idx, col := range columnNames {
		colToVal[col] = values[idx]
	}
	return
}

// UpdateFieldsValues 根据字段名 自动生成update 语句并进行更新
// 如 filedNames=["DtsServer","CosFileSize"]
// 生成的update语句: update tb_tendis_dts_task set dts_server=?,cos_file_size=?,update_time=now() where task_id=xxxx;
// 该函数主要目的只更新 值变化的字段,而不是row全部值
func (t *TbTendisplusLightningTask) UpdateFieldsValues(fieldNames []string, logger *zap.Logger) (err error) {
	var colToVal map[string]interface{}
	colToVal, err = t.GetColToValByFields(fieldNames, logger)
	if err != nil {
		return err
	}
	_, err = UpdateLightningTaskRows([]string{t.TaskId}, colToVal, logger)
	return
}

// UpdateLightningTaskRows 更新tasks多行
func UpdateLightningTaskRows(taskIDs []string, colToValue map[string]interface{},
	logger *zap.Logger) (rowsAffected int64,
	err error) {
	var cli01 *scrdbclient.Client
	var subURL string
	var data *scrdbclient.APIServerResponse
	cli01, err = scrdbclient.NewClient(viper.GetString("serviceName"), logger)
	if err != nil {
		return
	}
	type dtsTaskRowsUpdateReq struct {
		TaskIDs       []string               `json:"task_ids"`
		ColumnToValue map[string]interface{} `json:"col_to_val"`
	}

	type dtsTaskRowsUpdateRsp struct {
		RowsAffected int64 `json:"rows_affected"`
	}

	ret := &dtsTaskRowsUpdateRsp{}
	if cli01.GetServiceName() == constvar.BkDbm {
		subURL = constvar.DbmLightningUpdateTaskRowsURL
	}
	param := dtsTaskRowsUpdateReq{
		TaskIDs:       taskIDs,
		ColumnToValue: colToValue,
	}
	data, err = cli01.Do(http.MethodPost, subURL, param)
	if err != nil {
		return
	}
	err = json.Unmarshal(data.Data, ret)
	if err != nil {
		err = fmt.Errorf("UpdateLightningTaskRows unmarshal data fail,err:%v,resp.Data:%s,subURL:%s,param:%+v",
			err.Error(), string(data.Data), subURL, param)
		logger.Error(err.Error())
		return
	}
	return ret.RowsAffected, nil
}

// IsAllLightningTasksToForceKill 是否全部tasks都等待被force kill
func IsAllLightningTasksToForceKill(tasks []*TbTendisplusLightningTask) (allForceKill bool) {
	if len(tasks) == 0 {
		return false
	}
	for _, t01 := range tasks {
		t02 := t01
		if t02.OperateType != constvar.RedisForceKillTaskTodo {
			return false
		}
	}
	return true
}
