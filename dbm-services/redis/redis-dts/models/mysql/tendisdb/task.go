package tendisdb

import (
	"encoding/json"
	"fmt"
	"net/http"
	"reflect"
	"regexp"
	"strings"
	"sync"

	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/customtime"
	"dbm-services/redis/redis-dts/pkg/scrdbclient"

	"github.com/spf13/viper"
	"go.uber.org/zap"
)

var (
	tbTaskFiledToColunm map[string]string // struct filedName map to colunmName
	once01              sync.Once
)

// TbTendisDTSTask 迁移task
type TbTendisDTSTask struct {
	ID                    int64                 `json:"id" gorm:"column:id;primary_key"`
	BillID                int64                 `json:"bill_id" gorm:"column:bill_id"`                                   // 单据号
	App                   string                `json:"app" gorm:"column:app"`                                           // 业务英文名
	BkCloudID             int64                 `json:"bk_cloud_id" gorm:"column:bk_cloud_id"`                           // 云区域id
	DtsServer             string                `json:"dts_server" gorm:"column:dts_server"`                             // 执行迁移任务的server ip
	User                  string                `json:"user" gorm:"column:user"`                                         // 申请人
	SrcCluster            string                `json:"src_cluster" gorm:"column:src_cluster"`                           // 源集群域名
	SrcClusterPriority    int                   `json:"src_cluster_priority" gorm:"column:src_cluster_priority"`         // 源集群优先级,值越大,优先级越高
	SrcIP                 string                `json:"src_ip" gorm:"column:src_ip"`                                     // 源slave ip
	SrcPort               int                   `json:"src_port" gorm:"column:src_port"`                                 // 源slave port
	SrcPassword           string                `json:"src_password" gorm:"column:src_password"`                         // 源实例密码base64值
	SrcDbType             string                `json:"src_dbtype" gorm:"column:src_dbtype"`                             // 源实例db类型,TendisSSDInstance/RedisInstance/TendisplusInstance
	SrcDbSize             int64                 `json:"src_dbsize" gorm:"column:src_dbsize"`                             // 源实例数据量大小,单位byte,ssd=>rocksdbSize,cache=>used_memory
	SrcSegStart           int                   `json:"src_seg_start" gorm:"column:src_seg_start"`                       // 源实例所属segment start
	SrcSegEnd             int                   `json:"src_seg_end" gorm:"column:src_seg_end"`                           // 源实例所属segment end
	SrcWeight             int                   `json:"src_weight" gorm:"column:src_weight"`                             // 源实例权重,单个集群中根据实例的weight从小到大执行迁移
	SrcIPConcurrencyLimit int                   `json:"src_ip_concurrency_limit" gorm:"column:src_ip_concurrency_limit"` // 源slave ip上task并发数控制
	SrcIPZonename         string                `json:"src_ip_zonename" gorm:"column:src_ip_zonename"`                   // 源实例所在城市
	SrcOldLogCount        int64                 `json:"src_old_logcount" gorm:"column:src_old_logcount"`                 // 源实例slave-keep-log-count的旧值
	SrcNewLogCount        int64                 `json:"src_new_logcount" gorm:"column:src_new_logcount"`                 // 源实例slave-keep-log-count的新值
	IsSrcLogCountRestored int                   `json:"is_src_logcount_restored" gorm:"column:is_src_logcount_restored"` // 源实例slave-keep-log-count是否恢复
	SrcHaveListKeys       int                   `json:"src_have_list_keys" gorm:"column:src_have_list_keys"`             // srcRedis是否包含list类型key,list类型key重试存在风险
	KeyWhiteRegex         string                `json:"key_white_regex" gorm:"column:key_white_regex"`                   // key正则(白名单)
	KeyBlackRegex         string                `json:"key_black_regex" gorm:"column:key_black_regex"`                   // key正则(黑名单)
	SrcKvStoreID          int                   `json:"src_kvstore_id" gorm:"column:src_kvstore_id"`                     // tendisplus kvstore id
	DstCluster            string                `json:"dst_cluster" gorm:"column:dst_cluster"`                           // 目的集群
	DstPassword           string                `json:"dst_password" gorm:"column:dst_password"`                         // 目的密码base64值
	TaskType              string                `json:"task_type" gorm:"column:task_type"`                               // task类型,包含tendis_backup, backupfile_fetch,tendisdump,cmdsImporter,make_sync
	TendisbackupFile      string                `json:"tendisbackup_file" gorm:"column:tendisbackup_file"`               // tendis slave上bakup文件位置
	FetchFile             string                `json:"fetch_file" gorm:"column:fetch_file"`                             // backup文件拉取到dtsserver本地位置
	SqlfileDir            string                `json:"sqlfile_dir" gorm:"column:sqlfile_dir"`                           // tendisdumper得到的sql文件夹
	SyncerPort            int                   `json:"syncer_port" gorm:"column:syncer_port"`                           // redis-sync端口
	SyncerPid             int                   `json:"syncer_pid" gorm:"column:syncer_pid"`                             // sync的进程id
	TendisBinlogLag       int64                 `json:"tendis_binlog_lag" gorm:"column:tendis_binlog_lag"`               // redis-sync tendis_binlog_lag信息
	RetryTimes            int                   `json:"retry_times" gorm:"column:retry_times"`                           // task重试次数
	SyncOperate           string                `json:"sync_operate" gorm:"column:sync_operate"`                         // sync操作,包括pause,resume,upgrade,stop等,对应值有PauseTodo PauseFail PauseSucc
	KillSyncer            int                   `json:"kill_syncer" gorm:"column:kill_syncer"`                           // 杀死syncer,0代表否,1代表是
	Message               string                `json:"message" gorm:"column:message"`                                   // 信息
	Status                int                   `json:"status" gorm:"column:status"`                                     // 0:未开始 1:执行中 2:完成 -1:发生错误
	IgnoreErrlist         string                `json:"ignore_errlist" gorm:"column:ignore_errlist"`                     // 迁移过程中被忽略的错误,如key同名不同类型WRONGTYPE Operation
	ResyncFromTime        customtime.CustomTime `json:"resync_from_time" gorm:"column:resync_from_time"`                 // sync从该时间点重新同步增量数据
	CreateTime            customtime.CustomTime `json:"create_time" gorm:"column:create_time"`                           // 创建时间
	UpdateTime            customtime.CustomTime `json:"update_time" gorm:"column:update_time"`                           // 更新时间
}

// TableName 表名
func (t *TbTendisDTSTask) TableName() string {
	return "tb_tendis_dts_task"
}

// ToString 行数据返回为json
func (t *TbTendisDTSTask) ToString() string {
	ret, _ := json.Marshal(t)
	return string(ret)
}

// TaskLockKey keyname
func (t *TbTendisDTSTask) TaskLockKey() string {
	return fmt.Sprintf("TendisDTS_task_lock_%d_%s_%s_%s_%d",
		t.BillID, t.SrcCluster, t.DstCluster,
		t.SrcIP, t.SrcPort)
}

// IsAllDtsTasksToForceKill 是否全部tasks都等待被force kill
func IsAllDtsTasksToForceKill(tasks []*TbTendisDTSTask) (allForceKill bool) {
	if len(tasks) == 0 {
		return false
	}
	for _, t01 := range tasks {
		t02 := t01
		if t02.SyncOperate != constvar.RedisForceKillTaskTodo {
			return false
		}
	}
	return true
}

func genColInWhere(colName string, valList []string) string {
	if len(valList) == 0 || colName == "" {
		return ""
	}

	var builder strings.Builder
	builder.WriteString(" and " + colName + " in (")

	if len(valList) == 1 {
		builder.WriteString("'" + valList[0] + "'")
	} else {
		builder.WriteString("'" + valList[0] + "'")
		for _, s := range valList[1:] {
			builder.WriteString(",'" + s + "'")
		}
	}
	builder.WriteString(")")
	return builder.String()
}

// GetDtsSvrMigratingTasks TODO
/*GetDtsSvrMigratingTasks 获取dtsserver正在迁移的task,与task对应多少dataSize
对tendiSSD来说,'迁移中' 指处于 'tendisBackup'、'backupfileFetch'、'tendisdump'、'cmdsImporter'中的task,
不包含处于 status=-1 或 处于 makeSync 状态的task
对tendisCache来说,'迁移中'指处于 'makeCacheSync'中的task,不包含处于 status=-1 或 处于 watchCacheSync 状态的task
@params:
 dbType: TendisSSDInstance/RedisInstance/TendisplusInstance
*/
func GetDtsSvrMigratingTasks(bkCloudID int64, dtsSvr, dbType string, taskTypes []string,
	logger *zap.Logger) (tasks []*TbTendisDTSTask, dataSize uint64, err error) {
	var cli01 *scrdbclient.Client
	var subURL string
	var data *scrdbclient.APIServerResponse
	cli01, err = scrdbclient.NewClient(viper.GetString("serviceName"), logger)
	if err != nil {
		return
	}
	tasks = []*TbTendisDTSTask{}
	if cli01.GetServiceName() == constvar.DtsRemoteTendisxk8s {
		subURL = constvar.K8sDtsServerMigratingTasksURL
	} else if cli01.GetServiceName() == constvar.BkDbm {
		subURL = constvar.DbmDtsServerMigratingTasksURL
	}
	type dtsSvrMigratingTasksReq struct {
		BkCloudID int64    `json:"bk_cloud_id"`
		DtsServer string   `json:"dts_server"`
		DbType    string   `json:"db_type"`
		TaskTypes []string `json:"task_types"`
	}
	param := dtsSvrMigratingTasksReq{
		BkCloudID: bkCloudID,
		DtsServer: dtsSvr,
		DbType:    dbType,
		TaskTypes: taskTypes,
	}
	data, err = cli01.Do(http.MethodPost, subURL, param)
	if err != nil {
		return
	}
	err = json.Unmarshal(data.Data, &tasks)
	if err != nil {
		err = fmt.Errorf("GetDtsSvrMigratingTasks unmarshal data fail,err:%v,resp.Data:%s,subURL:%s,param:%+v",
			err.Error(), string(data.Data), subURL, param)
		logger.Error(err.Error())
		return
	}
	dataSize = 0
	for _, tmp := range tasks {
		task := tmp
		dataSize = dataSize + uint64(task.SrcDbSize)
	}
	return
}

// GetDtsSvrMaxSyncPort 获取DtsServer上syncPort最大的task
func GetDtsSvrMaxSyncPort(bkCloudID int64, dtsSvr, dbType string, taskTypes []string, logger *zap.Logger) (
	ret *TbTendisDTSTask, err error) {
	var cli01 *scrdbclient.Client
	var subURL string
	var data *scrdbclient.APIServerResponse
	cli01, err = scrdbclient.NewClient(viper.GetString("serviceName"), logger)
	if err != nil {
		return
	}
	type dtsSvrMaxSyncPortReq struct {
		BkCloudID int64    `json:"bk_cloud_id"`
		DtsServer string   `json:"dts_server"`
		DbType    string   `json:"db_type"`
		TaskTypes []string `json:"task_types"`
	}

	ret = &TbTendisDTSTask{}
	if cli01.GetServiceName() == constvar.DtsRemoteTendisxk8s {
		subURL = constvar.K8sDtsServerMaxSyncPortURL
	} else if cli01.GetServiceName() == constvar.BkDbm {
		subURL = constvar.DbmDtsServerMaxSyncPortURL
	}
	param := dtsSvrMaxSyncPortReq{
		BkCloudID: bkCloudID,
		DtsServer: dtsSvr,
		DbType:    dbType,
		TaskTypes: taskTypes,
	}
	data, err = cli01.Do(http.MethodPost, subURL, param)
	if err != nil {
		return
	}
	if len(data.Data) == 4 && string(data.Data) == "null" {
		return nil, nil
	}
	err = json.Unmarshal(data.Data, ret)
	if err != nil {
		err = fmt.Errorf("GetDtsSvrMaxSyncPortV2 unmarshal data fail,err:%v,resp.Data:%s,subURL:%s,param:%+v",
			err.Error(), string(data.Data), subURL, param)
		logger.Error(err.Error())
		return
	}
	return
}

// GetLast30DaysToExecuteTasks 用于获取最近一个月本地等待执行的tasks
// 可用于获取 tendis_backup,backupfile_fetch等待执行的task
func GetLast30DaysToExecuteTasks(
	bkCloudID int64,
	dtsServer, taskType, dbType string,
	status, limit int,
	logger *zap.Logger) (tasks []*TbTendisDTSTask, err error) {
	var cli01 *scrdbclient.Client
	var subURL string
	var data *scrdbclient.APIServerResponse
	cli01, err = scrdbclient.NewClient(viper.GetString("serviceName"), logger)
	if err != nil {
		return
	}
	type dtsLast30DaysToExecuteTasksReq struct {
		BkCloudID int64  `json:"bk_cloud_id"`
		DtsServer string `json:"dts_server"`
		DbType    string `json:"db_type"`
		TaskType  string `json:"task_type"`
		Status    int    `json:"status"`
		Limit     int    `json:"limit"`
	}
	tasks = []*TbTendisDTSTask{}
	if cli01.GetServiceName() == constvar.DtsRemoteTendisxk8s {
		subURL = constvar.K8sDtsLast30DaysToExecuteTasksURL
	} else if cli01.GetServiceName() == constvar.BkDbm {
		subURL = constvar.DbmDtsLast30DaysToExecuteTasksURL
	}
	param := dtsLast30DaysToExecuteTasksReq{
		DtsServer: dtsServer,
		DbType:    dbType,
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
		err = fmt.Errorf("GetLast30DaysTobeExecutedTasks unmarshal data fail,err:%v,resp.Data:%s,subURL:%s,param:%+v",
			err.Error(), string(data.Data), subURL, param)
		logger.Error(err.Error())
		return
	}
	return
}

// GetToBeScheduledJobs 获取最近一个月待调度的Jobs
// 遍历jobs
// GetJobToBeScheduledTasks 获取job中所有待调度的task
// 如果task 同时满足两个条件,即可执行调度:
// a. 数据量满足 <= maxDataSize
// b. task所在的srcIP, 其当前迁移中的tasksCnt + 1 <= srcIP可支持的最大并发数(task.src_ip_concurrency_limit决定)

// GetLast30DaysToScheduleJobs 获取最近30天待调度的Jobs
// jobs必须满足: 有一个待调度的task.dataSize < maxDataSize
func GetLast30DaysToScheduleJobs(bkCloudID int64, maxDataSize int64, zoneName, dbType string,
	logger *zap.Logger) (jobs []*TbTendisDTSTask, err error) {
	var cli01 *scrdbclient.Client
	var subURL string
	var data *scrdbclient.APIServerResponse
	cli01, err = scrdbclient.NewClient(viper.GetString("serviceName"), logger)
	if err != nil {
		return
	}
	type dtsLast30DaysToScheduleJobsReq struct {
		BkCloudID   int64  `json:"bk_cloud_id"`
		MaxDataSize int64  `json:"max_data_size"`
		ZoneName    string `json:"zone_name"`
		DbType      string `json:"db_type"`
	}
	jobs = []*TbTendisDTSTask{}
	if cli01.GetServiceName() == constvar.DtsRemoteTendisxk8s {
		subURL = constvar.K8sDtsLast30DaysToScheduleJobsURL
	} else if cli01.GetServiceName() == constvar.BkDbm {
		subURL = constvar.DbmDtsLast30DaysToScheduleJobsURL
	}
	param := dtsLast30DaysToScheduleJobsReq{
		BkCloudID:   bkCloudID,
		MaxDataSize: maxDataSize,
		ZoneName:    zoneName,
		DbType:      dbType,
	}
	data, err = cli01.Do(http.MethodPost, subURL, param)
	if err != nil {
		return
	}
	err = json.Unmarshal(data.Data, &jobs)
	if err != nil {
		err = fmt.Errorf("GetLast30DaysToBeScheduledJobsV2 unmarshal data fail,err:%v,resp.Data:%s,subURL:%s,param:%+v",
			err.Error(), string(data.Data), subURL, param)
		logger.Error(err.Error())
		return
	}
	return
}

// GetJobToScheduleTasks 获取job中所有待调度的task
// billId、srcCluster、dstCluster确定一个job
// dtsserver='1.1.1.1' and status=0 and task_type="" 代表 '未执行'
// 一个job可能部分task执行,部分未执行;
// 根据权重src_weight排序,权重越小,越前面执行
func GetJobToScheduleTasks(billID int64, srcCluster, dstCluster string,
	logger *zap.Logger) (tasks []*TbTendisDTSTask, err error) {
	if billID == 0 || srcCluster == "" || dstCluster == "" {
		err = fmt.Errorf("billId:%d or srcCluster:%s  or dstCluster:%s cann't be empty",
			billID, srcCluster, dstCluster)
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
	type dtsJobToScheduleTasks struct {
		BillID     int64  `json:"bill_id"`
		SrcCluster string `json:"src_cluster"`
		DstCluster string `json:"dst_cluster"`
	}
	tasks = []*TbTendisDTSTask{}
	if cli01.GetServiceName() == constvar.DtsRemoteTendisxk8s {
		subURL = constvar.K8sDtsJobToScheduleTasksURL
	} else if cli01.GetServiceName() == constvar.BkDbm {
		subURL = constvar.DbmDtsJobToScheduleTasksURL
	}
	param := dtsJobToScheduleTasks{
		BillID:     billID,
		SrcCluster: srcCluster,
		DstCluster: dstCluster,
	}
	data, err = cli01.Do(http.MethodPost, subURL, param)
	if err != nil {
		return
	}
	err = json.Unmarshal(data.Data, &tasks)
	if err != nil {
		err = fmt.Errorf("GetJobToBeScheduledTasks unmarshal data fail,err:%v,resp.Data:%s,subURL:%s,param:%+v",
			err.Error(), string(data.Data), subURL, param)
		logger.Error(err.Error())
		return
	}
	return
}

// GetJobSrcIPRunningTasks 获取job中某个srcIP上正在迁移的tasks信息
// billId、srcCluster、dstCluster确定一个job
// 对于每个srcIP上可同时执行的迁移的task个数，我们必须控制，否则将影响srcIP,影响现网;
// 每个srcIP上可同时执行的最大tasks,由task.src_ip_concurrency_limit决定
func GetJobSrcIPRunningTasks(billID int64, srcCluster, dstCluster, srcIP string, taskTypes []string,
	logger *zap.Logger) (tasks []*TbTendisDTSTask, err error) {
	if billID == 0 || srcCluster == "" || dstCluster == "" {
		err = fmt.Errorf("billId:%d or srcCluster:%s  or dstCluster:%s cann't be empty",
			billID, srcCluster, dstCluster)
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
	type dtsJobSrcIPRuningTasksReq struct {
		BillID     int64    `json:"bill_id"`
		SrcCluster string   `json:"src_cluster"`
		DstCluster string   `json:"dst_cluster"`
		SrcIP      string   `json:"src_ip"`
		TaskTypes  []string `json:"task_types"`
	}

	tasks = []*TbTendisDTSTask{}
	if cli01.GetServiceName() == constvar.DtsRemoteTendisxk8s {
		subURL = constvar.K8sDtsJobSrcIPRunningTasksURL
	} else if cli01.GetServiceName() == constvar.BkDbm {
		subURL = constvar.DbmDtsJobSrcIPRunningTasksURL
	}
	param := dtsJobSrcIPRuningTasksReq{
		BillID:     billID,
		SrcCluster: srcCluster,
		DstCluster: dstCluster,
		SrcIP:      srcIP,
		TaskTypes:  taskTypes,
	}
	data, err = cli01.Do(http.MethodPost, subURL, param)
	if err != nil {
		return
	}
	err = json.Unmarshal(data.Data, &tasks)
	if err != nil {
		err = fmt.Errorf("GetJobSrcIPRunningTasks unmarshal data fail,err:%v,resp.Data:%s,subURL:%s,param:%+v",
			err.Error(), string(data.Data), subURL, param)
		logger.Error(err.Error())
		return
	}
	return
}

// DtsTaskStructFieldsToColumns 获取 TbTendisDTSTask 字段名 到 列名之间的对应关系
// 如 filedNames=["BillID","App","User","SrcIP"] 对应的 columnNames=["bill_id","app","user","src_ip"]
func DtsTaskStructFieldsToColumns(fieldNames []string, logger *zap.Logger) (columnNames []string, err error) {
	once01.Do(func() {
		t01 := TbTendisDTSTask{}
		reg01 := regexp.MustCompile(`column:(\w+)`)
		getType := reflect.TypeOf(t01)
		tbTaskFiledToColunm = make(map[string]string, getType.NumField())
		for i := 0; i < getType.NumField(); i++ {
			field := getType.Field(i)
			gormTag := string(field.Tag.Get("gorm"))
			l01 := reg01.FindStringSubmatch(gormTag)
			if len(l01) < 2 {
				continue
			}
			tbTaskFiledToColunm[field.Name] = l01[1]
		}
	})
	columnNames = make([]string, 0, len(fieldNames))
	for _, field01 := range fieldNames {
		colName, ok := tbTaskFiledToColunm[field01]
		if ok == false {
			err = fmt.Errorf("struct TbTendisDTSTask have no field:%s", colName)
			logger.Error(err.Error())
			return
		}
		columnNames = append(columnNames, colName)
	}
	return
}

// GetFieldsValue 根据 字段名 从task中获取其字段values
// 如 filedNames=["BillID","App","User","SrcIP"] 其对应值为 ret=[1111,"test_app","zhangsan","1.1.1.1"]
func (t *TbTendisDTSTask) GetFieldsValue(fieldNames []string, logger *zap.Logger) (ret []interface{}, err error) {
	_, err = DtsTaskStructFieldsToColumns(fieldNames, logger)
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
func (t *TbTendisDTSTask) GetColToValByFields(fieldNames []string, logger *zap.Logger) (
	colToVal map[string]interface{}, err error) {
	var columnNames []string
	var values []interface{}
	columnNames, err = DtsTaskStructFieldsToColumns(fieldNames, logger)
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
// 如 filedNames=["BillID","App","User","SrcIP"]
// 生成的update语句: update tb_tendis_dts_task set bill_id=?,app=?,user=?,src_ip=?,update_time=now() where id=xxxx;
// 该函数主要目的只更新 值变化的字段,而不是row全部值
func (t *TbTendisDTSTask) UpdateFieldsValues(fieldNames []string, logger *zap.Logger) (err error) {
	var colToVal map[string]interface{}
	colToVal, err = t.GetColToValByFields(fieldNames, logger)
	if err != nil {
		return err
	}
	_, err = UpdateDtsTaskRows([]int64{t.ID}, colToVal, logger)
	return
}

// UpdateDtsTaskRows 更新tasks多行
func UpdateDtsTaskRows(ids []int64, colToValue map[string]interface{}, logger *zap.Logger) (rowsAffected int64,
	err error) {
	var cli01 *scrdbclient.Client
	var subURL string
	var data *scrdbclient.APIServerResponse
	cli01, err = scrdbclient.NewClient(viper.GetString("serviceName"), logger)
	if err != nil {
		return
	}
	type dtsTaskRowsUpdateReq struct {
		TaskIDs       []int64                `json:"task_ids"`
		ColumnToValue map[string]interface{} `json:"col_to_val"`
	}

	type dtsTaskRowsUpdateRsp struct {
		RowsAffected int64 `json:"rows_affected"`
	}

	ret := &dtsTaskRowsUpdateRsp{}
	if cli01.GetServiceName() == constvar.DtsRemoteTendisxk8s {
		subURL = constvar.K8sDtsUpdateTaskRowsURL
	} else if cli01.GetServiceName() == constvar.BkDbm {
		subURL = constvar.DbmDtsUpdateTaskRowsURL
	}
	param := dtsTaskRowsUpdateReq{
		TaskIDs:       ids,
		ColumnToValue: colToValue,
	}
	data, err = cli01.Do(http.MethodPost, subURL, param)
	if err != nil {
		return
	}
	err = json.Unmarshal(data.Data, ret)
	if err != nil {
		err = fmt.Errorf("UpdateDtsTaskRows unmarshal data fail,err:%v,resp.Data:%s,subURL:%s,param:%+v",
			err.Error(), string(data.Data), subURL, param)
		logger.Error(err.Error())
		return
	}
	return ret.RowsAffected, nil
}

// GetTaskByID 根据id获得task详细信息
func GetTaskByID(id int64, logger *zap.Logger) (task *TbTendisDTSTask, err error) {
	if logger == nil {
		err = fmt.Errorf("GetTaskById logger cannot be nil")
		return
	}
	var cli01 *scrdbclient.Client
	var subURL string
	var data *scrdbclient.APIServerResponse
	cli01, err = scrdbclient.NewClient(viper.GetString("serviceName"), logger)
	if err != nil {
		return
	}
	type dtsTaskRowByIDReq struct {
		TaskID int64 `json:"task_id"`
	}

	task = &TbTendisDTSTask{}
	if cli01.GetServiceName() == constvar.DtsRemoteTendisxk8s {
		subURL = constvar.K8sDtsTaskRowByIDURL
	} else if cli01.GetServiceName() == constvar.BkDbm {
		subURL = constvar.DbmDtsTaskRowByIDURL
	}
	param := dtsTaskRowByIDReq{
		TaskID: id,
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
		err = fmt.Errorf("GetTaskByIDV2 unmarshal data fail,err:%v,resp.Data:%s,subURL:%s,param:%+v",
			err.Error(), string(data.Data), subURL, param)
		logger.Error(err.Error())
		return
	}
	return
}
