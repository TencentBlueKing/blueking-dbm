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
	"crypto/sha256"
	"errors"
	"fmt"
	"os"
	"regexp"
	"strings"
	"time"

	util "dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app"
	"dbm-services/mysql/db-simulation/model"
)

// DelPod 控制运行模拟执行后是否删除拉起的Pod的开关
// 用于保留现场排查问题
var DelPod = true

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

func init() {
	TaskChan = make(chan SimulationTask, 100)
	SpiderTaskChan = make(chan SimulationTask, 100)
	ctrlChan = make(chan struct{}, 30)
}

func init() {
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
		return task.CreateMySQLPod()
	case app.TdbCtl:
		return task.DbPodSets.CreateClusterPod()
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
	doneChan := make(chan struct{})
	ticker := time.NewTicker(30 * time.Second)
	go func() {
		for {
			select {
			case <-ticker.C:
				model.UpdateHeartbeat(t.TaskId, sstderr, sstdout)
			case <-doneChan:
				logger.Info("simulation run done")
				return
			}
		}
	}()
	// 关闭协程
	defer func() { ticker.Stop(); doneChan <- struct{}{} }()
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
