/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package service

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"regexp"
	"slices"
	"strings"
	"time"

	"github.com/bsm/redislock"
	"github.com/redis/go-redis/v9"
	"github.com/samber/lo"
	"gorm.io/gorm"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	util "dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app"
	"dbm-services/mysql/db-simulation/app/config"
	"dbm-services/mysql/db-simulation/model"
)

// DelPod 控制运行模拟执行后是否删除拉起的Pod的开关
// 用于保留现场排查问题
var DelPod = true

// HeartbeatInterval 心跳时间间隔
var HeartbeatInterval = 15

// BaseParam 请求模拟执行的基础参数
type BaseParam struct {
	//nolint
	Uid string `json:"uid"`
	//nolint
	NodeId string `json:"node_id"`
	//nolint
	RootId string `json:"root_id"`
	//nolint
	VersionId string `json:"version_id"`
	//nolint
	TaskId            string               `json:"task_id"  binding:"required"`
	MySQLVersion      string               `json:"mysql_version"  binding:"required"`
	MySQLCharSet      string               `json:"mysql_charset"  binding:"required"`
	MySQLStartConfigs map[string]string    `json:"mysql_start_config"`
	Path              string               `json:"path"  binding:"required"`
	SchemaSQLFile     string               `json:"schema_sql_file"  binding:"required"`
	ExcuteObjects     []ExcuteSQLFileObjV2 `json:"execute_objects"  binding:"gt=0,dive,required"`
}

// BuildTendbPodName build tendb pod name
func (b BaseParam) BuildTendbPodName() string {
	podName := fmt.Sprintf("tendb-%s-%s", strings.ToLower(b.MySQLVersion),
		replaceUnderSource(b.TaskId))
	return podName
}

// BuildSpiderPodName build spider pod name
func (b BaseParam) BuildSpiderPodName() string {
	podName := fmt.Sprintf("spider-%s-%s", strings.ToLower(b.MySQLVersion),
		replaceUnderSource(b.TaskId))
	return podName
}

func replaceUnderSource(str string) string {
	return strings.ReplaceAll(str, "_", "-")
}

// BuildStartArgs mysql pod start args
func (b BaseParam) BuildStartArgs() []string {
	if len(b.MySQLStartConfigs) == 0 {
		return []string{}
	}
	var args []string
	for key, val := range b.MySQLStartConfigs {
		p := strings.ReplaceAll(strings.TrimSpace(key), "_", "-")
		args = append(args, fmt.Sprintf("--%s=%s", p, strings.TrimSpace(val)))
	}
	return args
}

// parseDbParamRe ConvertDbParamToRegular 解析DbNames参数成正则参数
func (e *ExcuteSQLFileObj) parseDbParamRe() (s []string) {
	return changeToMatch(e.DbNames)
}

// parseIgnoreDbParamRe  解析IgnoreDbNames参数成正则参数
//
//	@receiver e
//	@return []string
func (e *ExcuteSQLFileObj) parseIgnoreDbParamRe() (s []string) {
	return changeToMatch(e.IgnoreDbNames)
}

// changeToMatch 将输入的参数转成正则匹配的格式
//
//	@receiver input
//	@return []string
func changeToMatch(input []string) []string {
	var result []string
	for _, str := range input {
		str = strings.ReplaceAll(str, "?", ".")
		str = strings.ReplaceAll(str, "%", ".*")
		str = `^` + str + `$`
		result = append(result, str)
	}
	return result
}

// TaskRuntimCtx 模拟执行运行上下文
type TaskRuntimCtx struct {
	dbsExcludeSysDb []string
}

// SimulationTask simulated execution task definition
type SimulationTask struct {
	RequestId string
	PodName   string
	Version   string
	*BaseParam
	*DbPodSets
	TaskRuntimCtx
}

// TaskChan 模拟执行任务队列
var TaskChan chan SimulationTask

// SpiderTaskChan TendbCluster模拟执行任务队列
var SpiderTaskChan chan SimulationTask

// CtrlChan 并发控制
var ctrlChan chan struct{}

var rdb *redis.Client

func init() {
	TaskChan = make(chan SimulationTask, 100)
	SpiderTaskChan = make(chan SimulationTask, 100)
	ctrlChan = make(chan struct{}, 30)
	timer := time.NewTicker(60 * time.Second)
	go func() {
		for {
			select {
			case task := <-TaskChan:
				go run(task, app.MySQL)
			case task := <-SpiderTaskChan:
				go run(task, app.TdbCtl)
			case <-timer.C:
				logger.Info("current run %d task", len(TaskChan))
			}
		}
	}()
	logger.Info("redis addr %s", config.GAppConfig.Redis.Addr)
	rdb = redis.NewClient(&redis.Options{
		Addr:     config.GAppConfig.Redis.Addr,
		Password: config.GAppConfig.Redis.Password,
		DB:       0,
	})
	go func() {
		// 等待一个周期的原因，避免重载执行正常的任务
		// 因为http svr 是graceful shutdown, 可能旧的服务会接受请求
		for i := 0; i < 5; i++ {
			logger.Info("the %d times reload running task", i)
			time.Sleep(time.Duration(HeartbeatInterval) * time.Second)
			reloadRunningTaskFromdb(i + HeartbeatInterval)
		}
		rdb.Close()
	}()
}

// ReloadParam reload running task from db
type ReloadParam struct {
	BaseParam
	SpiderVersion *string `json:"spider_version,omitempty"`
}

// reloadRunningTaskFromdb 重载重启服务前运行的任务 加锁是避免多个服务同时启动，避免相同任务被重载
// nolint
func reloadRunningTaskFromdb(heartbeatInterval int) {
	key := "simulation:reload:lock"
	locker := redislock.New(rdb)
	ctx := context.Background()
	rlock, err := locker.Obtain(ctx, key, 60*time.Second, nil)
	if err != nil {
		logger.Error("obtain lock failed %v", err)
		return
	}
	defer func() {
		// nolint
		rlock.Release(ctx)
	}()
	var tks []model.TbSimulationTask
	if err := model.DB.Model(model.TbSimulationTask{}).Where(
		"phase not in (?) and create_time > DATE_SUB(NOW(),INTERVAL 2 HOUR) and time_to_sec(timediff(now(),heartbeat_time)) > ?",
		[]string{model.PhaseDone, model.PhaseReloading}, heartbeatInterval).Scan(&tks).Error; err != nil {
		logger.Error("get running task failed %s", err.Error())
		return
	}
	var reRunTask []model.TbSimulationTask
	// 可能已经重试成功了，但是version ID 已经变了
	for _, tk := range tks {
		var cks model.TbSimulationTask
		if err := model.DB.Model(model.TbSimulationTask{}).Where("bill_task_id = ? and phase = ? and status = ?",
			tk.BillTaskId, model.PhaseDone, model.TaskSuccess).First(&cks).Error; err != nil {
			if errors.Is(err, gorm.ErrRecordNotFound) {
				reRunTask = append(reRunTask, tk)
				continue
			}
		}
		logger.Info("task %s already run success", tk.TaskId)
	}
	if len(reRunTask) == 0 {
		logger.Info("no need reload running task")
		return
	}
	for _, tk := range reRunTask {
		var err error
		var req model.TbRequestRecord
		var p ReloadParam
		var podName string
		if err = model.DB.Model(model.TbRequestRecord{}).Where("request_id = ? ", tk.RequestID).Find(&req).
			Error; err != nil {
			logger.Error("get request content failed %s", err.Error())
			//nolint
			model.CompleteTask(tk.TaskId, tk.MySQLVersion, model.TaskFailed, "", "", "")
			continue
		}
		if err = json.Unmarshal([]byte(req.RequestBody), &p); err != nil {
			logger.Error("get request content failed %s", err.Error())
			//nolint
			model.CompleteTask(tk.TaskId, tk.MySQLVersion, model.TaskFailed, "", "", "")
			continue
		}
		if p.SpiderVersion == nil {
			podName = p.BuildTendbPodName()
		} else {
			podName = p.BuildSpiderPodName()
		}
		// delete old pod
		var gracePeriodSeconds int64
		if slices.Contains([]string{model.PhaseCreatePod, model.PhaseLoadSchema, model.PhaseRunning}, tk.Phase) {
			err = Kcs.Cli.CoreV1().Pods(Kcs.Namespace).Delete(context.TODO(), podName, metav1.DeleteOptions{
				GracePeriodSeconds: &gracePeriodSeconds,
			})
			if err != nil {
				logger.Error("delete pod failed %s", err.Error())
				//nolint
				model.CompleteTask(tk.TaskId, tk.MySQLVersion, model.TaskFailed, "", "", "")
				continue
			}
		}
		// wait pod delete
		time.Sleep(3 * time.Second)
		logger.Info("loading task %s", tk.TaskId)
		model.UpdatePhase(tk.TaskId, tk.MySQLVersion, model.PhaseReloading)
		if p.SpiderVersion != nil {
			SpiderTaskChan <- p.BuildTsk(tk.RequestID)
		} else {
			TaskChan <- p.BuildTsk(tk.RequestID)
		}
	}
}

// BuildTsk build read load task
func (r ReloadParam) BuildTsk(requestId string) (tsk SimulationTask) {
	tsk = SimulationTask{
		RequestId: requestId,
		DbPodSets: NewDbPodSets(),
		BaseParam: &r.BaseParam,
		Version:   r.MySQLVersion,
	}
	version := r.MySQLVersion
	img, err := GetImgFromMySQLVersion(version)
	if err != nil {
		logger.Error("GetImgFromMySQLVersion %s failed:%s", version, err.Error())
		return
	}
	tsk.DbImage = img
	if r.SpiderVersion != nil {
		tsk.SpiderImage, tsk.TdbCtlImage = GetSpiderAndTdbctlImg(*r.SpiderVersion, LatestVersion)
	}
	tsk.BaseInfo = &MySQLPodBaseInfo{
		PodName: fmt.Sprintf("tendb-%s-%s", strings.ToLower(version),
			replaceUnderSource(r.TaskId)),
		Lables: map[string]string{"task_id": replaceUnderSource(r.TaskId),
			"request_id": requestId},
		RootPwd: r.TaskId[0:4],
		Args:    r.BuildStartArgs(),
		Charset: r.MySQLCharSet,
	}
	return tsk
}

func run(task SimulationTask, tkType string) {
	var err error
	var so, se string
	ctrlChan <- struct{}{}
	defer func() {
		<-ctrlChan
		var status string
		var errMsg string
		status = model.TaskSuccess
		if err != nil {
			status = model.TaskFailed
			errMsg = err.Error()
		}
		if err = model.CompleteTask(task.TaskId, task.Version, status, se, so, errMsg); err != nil {
			logger.Error("update task status faield %s", err.Error())
			return
		}
	}()
	doneChan := make(chan struct{})
	ticker := time.NewTicker(time.Duration(HeartbeatInterval) * time.Second)
	go func() {
		for {
			select {
			case <-ticker.C:
				model.UpdateHeartbeat(task.TaskId)
			case <-doneChan:
				logger.Info("simulation run done")
				return
			}
		}
	}()
	// 关闭协程
	defer func() { ticker.Stop(); doneChan <- struct{}{} }()
	xlogger := task.getXlogger()
	// create Pod
	model.UpdatePhase(task.TaskId, task.MySQLVersion, model.PhaseCreatePod)
	defer func() {
		if DelPod {
			if errx := task.DbPodSets.DeletePod(); errx != nil {
				logger.Warn("delete Pod failed %s", errx.Error())
			}
			logger.Info("delete pod successfully~")
		}
	}()
	if err = createPod(task, tkType); err != nil {
		xlogger.Error("create pod failed %s", err.Error())
		return
	}
	so, se, err = task.SimulationRun(tkType, xlogger)
	if err != nil {
		xlogger.Error("simulation execution failed%s", err.Error())
		return
	}
	xlogger.Info("the simulation was executed successfully")
}

func createPod(task SimulationTask, tkType string) (err error) {
	switch tkType {
	case app.MySQL:
		return task.CreateMySQLPod(task.BaseParam.MySQLVersion)
	case app.TdbCtl:
		return task.DbPodSets.CreateClusterPod(task.BaseParam.MySQLVersion)
	}
	return
}

func (t *SimulationTask) getDbsExcludeSysDb() (err error) {
	alldbs, err := t.DbWork.ShowDatabases()
	if err != nil {
		logger.Error("failed to get instance db list:%s", err.Error())
		return err
	}
	t.dbsExcludeSysDb = util.FilterOutStringSlice(alldbs, util.GetGcsSystemDatabasesIgnoreTest(t.MySQLVersion))
	return nil
}

// SimulationRun 运行模拟执行
func (t *SimulationTask) SimulationRun(containerName string, xlogger *logger.Logger) (sstdout, sstderr string,
	err error) {
	logger.Info("will execute in %s", containerName)

	model.UpdatePhase(t.TaskId, t.MySQLVersion, model.PhaseLoadSchema)
	// Load schema SQL
	sstdout, sstderr, err = t.loadSchemaSQL(containerName)
	if err != nil {
		xlogger.Error("Failed to load schema SQL: %v", err)
		return sstdout, sstderr, fmt.Errorf("failed to load schema SQL: %w", err)
	}
	xlogger.Info("Schema SQL loaded successfully")
	xlogger.Info(sstdout, sstderr)
	// load real databases
	if err = t.getDbsExcludeSysDb(); err != nil {
		logger.Error("getDbsExcludeSysDb faiked %v", err)
		return sstdout, sstderr, fmt.Errorf("[getDbsExcludeSysDb failed]:%w", err)
	}
	model.UpdatePhase(t.TaskId, t.MySQLVersion, model.PhaseRunning)
	errs := []error{}
	sstderrs := []string{}
	for _, e := range t.ExcuteObjects {
		sstdout, sstderr, err = t.executeMultFilesObject(e, containerName, xlogger)
		if err != nil {
			//nolint
			errs = append(errs, err)
			sstderrs = append(sstderrs, sstderr)
		}
	}
	if len(errs) > 0 {
		return sstdout, strings.Join(sstderrs, "\n"), errors.Join(errs...)
	}
	return sstdout, sstderr, nil
}

func (t *SimulationTask) loadSchemaSQL(containerName string) (sstdout, sstderr string,
	err error) {
	defer func() {
		if err != nil {
			errx := model.DB.Create(&model.TbSqlFileSimulationInfo{
				TaskId:       t.TaskId,
				BillTaskId:   t.Uid,
				LineId:       0,
				FileNameHash: fmt.Sprintf("%x", sha256.Sum256([]byte(t.SchemaSQLFile))),
				FileName:     t.SchemaSQLFile,
				MySQLVersion: t.MySQLVersion,
				Status:       model.TaskFailed,
				ErrMsg:       "导入表结构失败," + err.Error(),
				CreateTime:   time.Now(),
				UpdateTime:   time.Now(),
			}).Error
			if errx != nil {
				logger.Warn("create exeute schema sqlfile simulation record failed %v", errx)
			}
		}
	}()
	stdout, stderr, err := t.DbPodSets.executeInPod(t.getLoadSchemaSQLCmd(t.Path, t.SchemaSQLFile),
		containerName,
		t.getExtmap(t.SchemaSQLFile), true)
	sstdout += stdout.String() + "\n"
	sstderr += stderr.String() + "\n"
	return sstdout, sstderr, err
}

func (t *SimulationTask) executeOneObject(e ExcuteSQLFileObj, containerName string, xlogger *logger.Logger) (sstdout,
	sstderr string, err error) {
	defer func() {
		status := model.TaskSuccess
		errMsg := ""
		if err != nil {
			status = model.TaskFailed
			errMsg = err.Error()
		}
		errx := model.DB.Create(&model.TbSqlFileSimulationInfo{
			TaskId:       t.TaskId,
			BillTaskId:   t.Uid,
			LineId:       e.LineID,
			FileNameHash: fmt.Sprintf("%x", sha256.Sum256([]byte(e.SQLFile))),
			FileName:     e.SQLFile,
			MySQLVersion: t.MySQLVersion,
			Status:       status,
			ErrMsg:       errMsg,
			CreateTime:   time.Now(),
			UpdateTime:   time.Now(),
		}).Error
		if errx != nil {
			logger.Warn("create sqlfile simulation record failed %v", errx)
		}
	}()
	xlogger.Info("[start]-%s", e.SQLFile)
	var realexcutedbs []string
	intentionDbs, err := t.match(e.parseDbParamRe())
	if err != nil {
		return "", "", err
	}
	ignoreDbs, err := t.match(e.parseIgnoreDbParamRe())
	if err != nil {
		return "", "", err
	}
	realexcutedbs = util.FilterOutStringSlice(intentionDbs, ignoreDbs)
	if len(realexcutedbs) == 0 {
		return "", "", fmt.Errorf("需要执行的db:%v,需要忽略的db:%v,查询线上存在的db,计算后没有找到任何变更的目标db,请检查你的输入是否正确", e.DbNames, e.IgnoreDbNames)
	}
	for idx, cmd := range t.getLoadSQLCmd(t.Path, e.SQLFile, realexcutedbs) {
		sstdout += util.RemovePassword(cmd) + "\n"
		stdout, stderr, err := t.DbPodSets.executeInPod(cmd, containerName, t.getExtmap(e.SQLFile), false)
		sstdout += stdout.String() + "\n"
		sstderr += stderr.String() + "\n"
		if err != nil {
			if idx == 0 {
				xlogger.Error("download file failed:%s", err.Error())
				return sstdout, sstderr, fmt.Errorf("download file %s failed:%s", e.SQLFile, err.Error())
			}
			xlogger.Error("when execute %s at %s, failed  %s\n", e.SQLFile, realexcutedbs[idx-1], err.Error())
			xlogger.Error("stderr:\n	%s", stderr.String())
			xlogger.Error("stdout:\n	%s", stdout.String())
			return sstdout, sstderr, fmt.Errorf("\nexec %s in %s failed:%s\n %s", e.SQLFile, realexcutedbs[idx-1],
				err.Error(), stderr.String())
		}
		xlogger.Info("%s \n %s", stdout.String(), stderr.String())
	}
	xlogger.Info("[end]-%s", e.SQLFile)
	return sstdout, sstderr, nil
}

func (t *SimulationTask) match(regularDbNames []string) (matched []string, err error) {
	for _, regexpStr := range regularDbNames {
		re, err := regexp.Compile(regexpStr)
		if err != nil {
			logger.Error(" regexp.Compile(%s) failed:%s", regexpStr, err.Error())
			return nil, err
		}
		for _, db := range t.dbsExcludeSysDb {
			if re.MatchString(db) {
				matched = append(matched, db)
			}
		}
	}
	return
}

func (t *SimulationTask) getExtmap(sqlFileName string) map[string]string {
	return map[string]string{
		"uid":        t.Uid,
		"node_id":    t.NodeId,
		"root_id":    t.RootId,
		"version_id": t.VersionId,
		"sqlfile":    sqlFileName,
	}
}

func (t *SimulationTask) getXlogger() *logger.Logger {
	return logger.New(os.Stdout, true, logger.InfoLevel, t.getExtmap(""))
}

func (t *SimulationTask) executeMultFilesObject(e ExcuteSQLFileObjV2, containerName string,
	xlogger *logger.Logger) (sstdout,
	sstderr string, err error) {
	for _, file := range e.SQLFiles {
		sstdout, sstderr, err = t.executeOneObject(ExcuteSQLFileObj{
			LineID:        e.LineID,
			SQLFile:       file,
			IgnoreDbNames: e.IgnoreDbNames,
			DbNames:       e.DbNames}, containerName, xlogger)
		if err != nil {
			logger.Error("simulation %s failed %v", file, err)
			return sstdout, sstderr, err
		}
	}
	return
}

// GetImgFromMySQLVersion 根据版本获取模拟执行运行的镜像配置
func GetImgFromMySQLVersion(version string) (img string, err error) {
	img, errx := model.GetImageName("mysql", version)
	if errx == nil {
		logger.Info("get image from db img config: %s", img)
		return img, nil
	}
	switch {
	case regexp.MustCompile("5.5").MatchString(version):
		return config.GAppConfig.Image.Tendb55Img, nil
	case regexp.MustCompile("5.6").MatchString(version):
		return config.GAppConfig.Image.Tendb56Img, nil
	case regexp.MustCompile("5.7").MatchString(version):
		return config.GAppConfig.Image.Tendb57Img, nil
	case regexp.MustCompile("8.0").MatchString(version):
		return config.GAppConfig.Image.Tendb80Img, nil
	default:
		return "", fmt.Errorf("not match any version")
	}
}

// GetSpiderAndTdbctlImg TODO
func GetSpiderAndTdbctlImg(spiderVersion, tdbctlVersion string) (spiderImg, tdbctlImg string) {
	return getSpiderImg(spiderVersion), getTdbctlImg(tdbctlVersion)
}

const (
	// LatestVersion latest version
	LatestVersion = "latest"
)

func getSpiderImg(version string) (img string) {
	if lo.IsEmpty(version) {
		version = LatestVersion
	}
	img, errx := model.GetImageName("spider", version)
	if errx == nil {
		return img
	}
	return config.GAppConfig.Image.SpiderImg
}

func getTdbctlImg(version string) (img string) {
	if lo.IsEmpty(version) {
		version = LatestVersion
	}
	img, errx := model.GetImageName("tdbctl", version)
	if errx == nil {
		return img
	}
	return config.GAppConfig.Image.TdbCtlImg
}
