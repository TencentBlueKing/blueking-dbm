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
	"fmt"
	"os"
	"regexp"
	"strings"
	"time"

	util "dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app"
	"dbm-services/mysql/db-simulation/app/config"
	"dbm-services/mysql/db-simulation/model"

	"github.com/pkg/errors"
)

// DelPod TODO
var DelPod bool = true

// BaseParam TODO
type BaseParam struct {
	Uid       string `json:"uid"`
	NodeId    string `json:"node_id"`
	RootId    string `json:"root_id"`
	VersionId string `json:"version_id"`
	// app
	TaskId        string             `json:"task_id"  binding:"required"`
	MySQLVersion  string             `json:"mysql_version"  binding:"required"`
	MySQLCharSet  string             `json:"mysql_charset"  binding:"required"`
	Path          string             `json:"path"  binding:"required"`
	ExcuteObjects []ExcuteSQLFileObj `json:"execute_objects"  binding:"gt=0,dive,required"`
	SchemaSQLFile string             `json:"schema_sql_file"  binding:"required"`
}

// SpiderSimulationExecParam TODO
// SpiderSimulationExecParam TODO
type SpiderSimulationExecParam struct {
	BaseParam
	SpiderVersion string `json:"spider_version"`
}

// SimulationTask TODO
type SimulationTask struct {
	RequestId string
	PodName   string
	*BaseParam
	*DbPodSets
	TaskRuntimCtx
}

// GetSpiderImg TODO
func (in SpiderSimulationExecParam) GetSpiderImg() string {
	return config.GAppConfig.Image.SpiderImg
}

// GetTdbctlImg TODO
func (in SpiderSimulationExecParam) GetTdbctlImg() string {
	return config.GAppConfig.Image.TdbCtlImg
}

// ExcuteSQLFileObj 单个文件的执行对象
// 一次可以多个文件操作不同的数据库
type ExcuteSQLFileObj struct {
	SQLFile       string   `json:"sql_file"  binding:"required"` // 变更文件名称
	IgnoreDbNames []string `json:"ignore_dbnames"`               // 忽略的,需要排除变更的dbName,支持模糊匹配
	DbNames       []string `json:"dbnames"  binding:"gt=0"`      // 需要变更的DBNames,支持模糊匹配
}

// parseDbParamRe TODO
// ConvertDbParamToRegular 解析DbNames参数成正则参数
//
//	@receiver e
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
		str = strings.Replace(str, "?", ".", -1)
		str = strings.Replace(str, "%", ".*", -1)
		str = `^` + str + `$`
		result = append(result, str)
	}
	return result
}

// GetImgFromMySQLVersion TODO
func GetImgFromMySQLVersion(verion string) (img string, err error) {
	switch {
	case regexp.MustCompile("5.6").MatchString(verion):
		return config.GAppConfig.Image.Tendb56Img, nil
	case regexp.MustCompile("5.7").MatchString(verion):
		return config.GAppConfig.Image.Tendb57Img, nil
	case regexp.MustCompile("8.0").MatchString(verion):
		return config.GAppConfig.Image.Tendb80Img, nil
	default:
		return "", fmt.Errorf("not match any version")
	}
}

// TaskRuntimCtx TODO
type TaskRuntimCtx struct {
	dbsExcludeSysDb []string // 过滤了系统库的全部db list
	version         string
}

// TaskChan TODO
var TaskChan chan SimulationTask

// SpiderTaskChan TODO
var SpiderTaskChan chan SimulationTask

// CtrlChan TODO
// 并发控制
var ctrlChan chan struct{}

func init() {
	TaskChan = make(chan SimulationTask, 100)
	SpiderTaskChan = make(chan SimulationTask, 100)
	ctrlChan = make(chan struct{}, 30)
}

// init TODO
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

// run TODO
func run(task SimulationTask, tkType string) {
	var err error
	var so, se string
	ctrlChan <- struct{}{}
	defer func() {
		<-ctrlChan
		var status string
		var errMsg string
		status = model.Task_Success
		if err != nil {
			status = model.Task_Failed
			errMsg = err.Error()
		}
		if err := model.CompleteTask(task.TaskId, status, se, so, errMsg); err != nil {
			logger.Error("update task status faield %s", err.Error())
			return
		}
	}()
	xlogger := task.getXlogger()
	// create Pod
	model.UpdatePhase(task.TaskId, model.Phase_CreatePod)
	defer func() {
		if DelPod {
			if err := task.DbPodSets.DeletePod(); err != nil {
				logger.Warn("delete Pod failed %s", err.Error())
			}
			logger.Info("delete pod successfuly~")
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
	logger.Info("get all database is %v", alldbs)
	if err = t.DbWork.Queryxs(&t.version, "select version();"); err != nil {
		logger.Error("query version failed %s", err.Error())
		return err
	}
	logger.Info("version is %s", t.version)
	t.dbsExcludeSysDb = util.FilterOutStringSlice(alldbs, util.GetGcsSystemDatabasesIgnoreTest(t.version))
	return nil
}

// SimulationRun TODO
func (t *SimulationTask) SimulationRun(containerName string, xlogger *logger.Logger) (sstdout, sstderr string,
	err error) {
	logger.Info("will execute in %s", containerName)
	doneChan := make(chan struct{})
	go func() {
		ticker := time.NewTicker(5 * time.Second)
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
	defer func() { doneChan <- struct{}{} }()
	// xlogger := t.getXlogger()
	// execute load schema
	model.UpdatePhase(t.TaskId, model.Phase_LoadSchema)
	stdout, stderr, err := t.DbPodSets.executeInPod(t.getLoadSchemaSQLCmd(t.Path, t.SchemaSQLFile),
		containerName,
		t.getExtmap())
	sstdout += stdout.String() + "\n"
	sstderr += stderr.String() + "\n"
	if err != nil {
		logger.Error("load database schema sql failed %s", err.Error())
		return sstdout, sstderr, errors.Wrap(err, "[导入表结构失败]")
	}
	xlogger.Info(stdout.String(), stderr.String())
	// load real databases
	if err = t.getDbsExcludeSysDb(); err != nil {
		logger.Error("getDbsExcludeSysDb faiked")
		err = errors.Wrap(err, "[getDbsExcludeSysDb failed]")
		return sstdout, sstderr, err
	}
	model.UpdatePhase(t.TaskId, model.Phase_Running)
	for _, e := range t.ExcuteObjects {
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
		if len(realexcutedbs) <= 0 {
			return "", "", fmt.Errorf("the changed db does not exist!!!")
		}
		for idx, cmd := range t.getLoadSQLCmd(t.Path, e.SQLFile, realexcutedbs) {
			sstdout += util.RemovePassword(cmd) + "\n"
			stdout, stderr, err := t.DbPodSets.executeInPod(cmd, containerName, t.getExtmap())
			sstdout += stdout.String() + "\n"
			sstderr += stderr.String() + "\n"
			if err != nil {
				if idx == 0 {
					xlogger.Error("download file failed:%s", err.Error())
					return sstdout, sstderr, fmt.Errorf("download file %s failed:%s", e.SQLFile, err.Error())
				}
				xlogger.Error("%s[%s]:ExecuteInPod failed %s", e.SQLFile, realexcutedbs[idx-1], err.Error())
				return sstdout, sstderr, fmt.Errorf("exec %s in %s failed:%s", e.SQLFile, realexcutedbs[idx-1],
					err.Error())
			}
			xlogger.Info("%s \n %s", stdout.String(), stderr.String())
		}
		xlogger.Info("[end]-%s", e.SQLFile)
	}
	return sstdout, sstderr, err
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

func (t *SimulationTask) getExtmap() map[string]string {
	return map[string]string{
		"uid":        t.Uid,
		"node_id":    t.NodeId,
		"root_id":    t.RootId,
		"version_id": t.VersionId,
	}
}

// getXlogger TODO
func (t *SimulationTask) getXlogger() *logger.Logger {
	return logger.New(os.Stdout, true, logger.InfoLevel, t.getExtmap())
}
