/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysql

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strconv"
	"strings"
	"sync"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// ExecutePartitionSQLComp TODO
type ExecutePartitionSQLComp struct {
	GeneralParam                  *components.GeneralParam  `json:"general"`
	Params                        *ExecutePartitionSQLParam `json:"extend"`
	ExecutePartitionSQLRunTimeCtx `json:"-"`
}

// ExecutePartitionSQLParam TODO
type ExecutePartitionSQLParam struct {
	Ip       string `json:"ip"  validate:"required,ip"` // 当前实例的主机地址
	FilePath string `json:"file_path"`
	Force    bool   `json:"force"`
}

// FilePartitionSQLObj TODO
type FilePartitionSQLObj struct {
	Ip             string                   `json:"ip"  validate:"required,ip"` // 当前实例的主机地址
	Port           int                      `json:"port"`                       // 被监控机器的上所有需要监控的端口
	ShardName      string                   `json:"shard_name"`
	ExecuteObjects []ExecutePartitionSQLObj `json:"execute_objects"`
}

// MyInstanceInfo TODO
type MyInstanceInfo struct {
	Ip     string `json:"ip"  validate:"required,ip"` // 当前实例的主机地址
	Port   int    `json:"port"`                       // 被监控机器的上所有需要监控的端口
	Socket string `json:"socket"`
	User   string
	Pwd    string
}

// ExecutePartitionSQLObj TODO
type ExecutePartitionSQLObj struct {
	ConfigID      int                    `json:"config_id"`
	Dblike        string                 `json:"dblike"`
	Tblike        string                 `json:"tblike"`
	InitPartition []InitPartitionContent `json:"init_partition"`
	AddPartition  []string               `json:"add_partition"`
	DropPartition []string               `json:"drop_partition"`
}

// InitPartitionContent TODO
type InitPartitionContent struct {
	NeedSize     int64  `json:"need_size"`
	Sql          string `json:"sql"`
	HasUniqueKey bool   `json:"has_unique_key"`
}

// ExecutePartitionSQLRunTimeCtx TODO
type ExecutePartitionSQLRunTimeCtx struct {
	WorkDir string
}

// ReturnInfo TODO
type ReturnInfo struct {
	ConfigId int    `json:"config_id"`
	Status   string `json:"status"`
	Msg      string `json:"msg"`
}

// Example TODO
func (e *ExecutePartitionSQLComp) Example() interface{} {
	comp := ExecutePartitionSQLComp{
		Params: &ExecutePartitionSQLParam{
			Ip:       "1.1.1.1",
			FilePath: "/xxx/xxx/xxx.txt",
			Force:    false,
		},
	}
	return comp
}

// Init TODO
func (e *ExecutePartitionSQLComp) Init() (err error) {
	e.WorkDir = fmt.Sprintf("%s/%s", cst.BK_PKG_INSTALL_PATH, "partition")
	_ = os.MkdirAll(e.WorkDir, 0755)
	return nil
}

// Execute TODO
func (e *ExecutePartitionSQLComp) Execute() (err error) {
	// 以单个执行目标为单位 execute_objects FilePartitionSQLObj
	filePartitionSQLObjs, err := e.getPartitionInfo(e.Params.FilePath)
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	// filePartitionSQLObj是从文件中读取，不是下发的参数
	// 一台机器上的多个实例串行执行
	var allReturnInfos []ReturnInfo
	for _, filePartitionSQLObj := range filePartitionSQLObjs {
		oneInsReturnInfo := e.excuteOneInstance(filePartitionSQLObj)
		allReturnInfos = append(allReturnInfos, oneInsReturnInfo...)
	}
	ret := struct {
		Summaries []ReturnInfo `json:"summaries"`
	}{allReturnInfos}

	retJson, _ := json.Marshal(ret)
	retInfo := components.WrapperOutputString(string(retJson))
	fmt.Println(retInfo)
	logger.Info(retInfo)
	return nil
}

func (e *ExecutePartitionSQLComp) excuteOneInstance(filePartitionSQLObj FilePartitionSQLObj,
) (oneInsReturnInfo []ReturnInfo) {
	// filePartitionSQLObj由文件中读取
	var myInsInfo MyInstanceInfo
	myInsInfo.Ip = filePartitionSQLObj.Ip
	myInsInfo.Port = filePartitionSQLObj.Port
	myInsInfo.User = e.GeneralParam.RuntimeAccountParam.PartitionYwUser
	myInsInfo.Pwd = e.GeneralParam.RuntimeAccountParam.PartitionYwPwd
	// 获取socket文件，获取不到则任务实例故障，不执行后面操作
	var err error
	myInsInfo.Socket, err = myInsInfo.getSocket()
	if err != nil {
		// 以实例为单位进行返回
		return getOneInsReturnInfo(filePartitionSQLObj, err.Error())
	}
	dbw, err := initDB(myInsInfo.Ip, myInsInfo.Port, myInsInfo.User, myInsInfo.Pwd)
	defer func() {
		if dbw != nil {
			dbw.Close()
		}
	}()
	c := make(chan struct{}, 4)
	wg := &sync.WaitGroup{}
	// errs := []string{}
	lock := &sync.Mutex{}

	// 需要处理返回，每个循环都是一个规则，需要对应一个返回
	for _, eb := range filePartitionSQLObj.ExecuteObjects {
		c <- struct{}{}
		wg.Add(1)
		// 并发执行ExecutePartitionSQLObj
		go func(eb ExecutePartitionSQLObj) {
			defer wg.Done()
			// 每条分区config为一个单位，根据ConfigID生成一个对应的错误文件
			// errfile := fmt.Sprintf("partition_%d_%s.err", eb.ConfigID, time.Now().Format("20060102150405"))
			errsall := []string{}
			// 依次执行初始化、添加、删除
			// 每个任务中会并发执行单条sql
			if len(eb.InitPartition) > 0 {
				logger.Info(fmt.Sprintf("初始化分区，config_id=%d\n", eb.ConfigID))
				if strings.Contains(filePartitionSQLObj.ShardName, "TDBCTL") {
					// TDBCTL不使用pt工具
					initPartition := e.getInitPartitionSQL(eb.InitPartition)
					err = e.excuteOne(dbw, initPartition, 10, myInsInfo)
				} else {
					// 初始化分区使用pt工具，因此通过命令行的形式进行执行
					// 没有唯一键的不能用pt工具
					hasUnikeyInit, hasNotUnikeyInit := e.initSQLClassify(eb.InitPartition)
					if len(hasUnikeyInit) > 0 {
						// 有唯一键的可以使用pt工具执行
						err = e.excuteInitSql(hasUnikeyInit, 10, myInsInfo)
					}

					if len(hasNotUnikeyInit) > 0 {
						err = e.excuteOne(dbw, hasNotUnikeyInit, 10, myInsInfo)
					}

				}
				if err != nil {
					errsall = append(errsall, err.Error())
				} else {
					logger.Info("初始化分区成功！")
				}
			}
			if len(eb.AddPartition) > 0 {
				logger.Info(fmt.Sprintf("添加分区，config_id=%d\n", eb.ConfigID))
				if strings.Contains(filePartitionSQLObj.ShardName, "TDBCTL") {
					addPartition := e.getNewPartitionSQL(eb.AddPartition)
					err = e.excuteOne(dbw, addPartition, 20, myInsInfo)
				} else {
					err = e.excuteOne(dbw, eb.AddPartition, 20, myInsInfo)
				}
				if err != nil {
					errsall = append(errsall, err.Error())
				} else {
					logger.Info("添加分区成功！")
				}
			}
			if len(eb.DropPartition) > 0 {
				logger.Info(fmt.Sprintf("删除分区，config_id=%d\n", eb.ConfigID))
				if strings.Contains(filePartitionSQLObj.ShardName, "TDBCTL") {
					dropPartition := e.getNewPartitionSQL(eb.DropPartition)
					err = e.excuteOne(dbw, dropPartition, 20, myInsInfo)
				} else {
					err = e.excuteOne(dbw, eb.DropPartition, 20, myInsInfo)
				}
				if err != nil {
					errsall = append(errsall, err.Error())
				} else {
					logger.Info("删除分区成功！")
				}
			}
			if len(errsall) > 0 {
				lock.Lock()
				// errs = append(errs, strings.Join(errsall, ";\n"))
				msg := fmt.Sprintf("instance is %s#%d. %s",
					myInsInfo.Ip, myInsInfo.Port, strings.Join(errsall, ";\n"))
				oneInsReturnInfo = append(oneInsReturnInfo,
					getOneReturnInfo(eb.ConfigID, "failed", msg))
				lock.Unlock()
			} else {
				lock.Lock()
				msg := fmt.Sprintf("instance is %s#%d", myInsInfo.Ip, myInsInfo.Port)
				oneInsReturnInfo = append(oneInsReturnInfo,
					getOneReturnInfo(eb.ConfigID, "succeeded", msg))
				lock.Unlock()
			}
			<-c
		}(eb)
	}
	wg.Wait()
	return
}

// excuteOne 以执行目标为单位
func (e *ExecutePartitionSQLComp) excuteOne(
	dbw *sql.DB, partitionSQLSet []string,
	connum int, myInsInfo MyInstanceInfo,
) (err error) {
	wg := sync.WaitGroup{}
	var errs []string
	lock := &sync.Mutex{}
	// lockappend用于保证
	lockappend := &sync.Mutex{}
	// 初始化分区的并发度可以低点
	// 增加和删除分区相对消耗小点，可以增加并发度
	c := make(chan struct{}, connum)
	for _, partitionSQL := range partitionSQLSet {
		c <- struct{}{}
		wg.Add(1)
		// partitionSQL = e.replace(partitionSQL)
		go func(partitionSQL string) {
			defer wg.Done()
			err := mysqlutil.ExecuteSqlAtLocal{
				WorkDir:          e.WorkDir,
				IsForce:          e.Params.Force,
				Charset:          "utf8",
				NeedShowWarnings: false,
				Host:             myInsInfo.Ip,
				Port:             myInsInfo.Port,
				Socket:           myInsInfo.Socket,
				User:             e.GeneralParam.RuntimeAccountParam.PartitionYwUser,
				Password:         e.GeneralParam.RuntimeAccountParam.PartitionYwPwd,
			}.ExecutePartitionByMySQLClient(dbw, partitionSQL, lock)
			if err != nil {
				lockappend.Lock()
				errs = append(errs, fmt.Sprintf("%s执行失败，报错：%s", partitionSQL, err.Error()))
				lockappend.Unlock()
			}
			<-c
		}(partitionSQL)
	}
	wg.Wait()
	if len(errs) > 0 {
		return fmt.Errorf(fmt.Sprintf("%s", strings.Join(errs, "\n")))
	}
	return nil
}

// initDB TODO
func initDB(host string, port int, user string, pwd string) (dbw *sql.DB, err error) {
	tcpdsn := fmt.Sprintf("%s:%d", host, port)
	dsn := fmt.Sprintf(
		"%s:%s@tcp(%s)/?charset=utf8&parseTime=True&loc=Local&timeout=30s&readTimeout=30s&lock_wait_timeout=5", user,
		pwd,
		tcpdsn,
	)
	SqlDB, err := sql.Open("mysql", dsn)
	if err != nil {
		logger.Error("connect to mysql failed %s", err.Error())
		return nil, err
	}
	return SqlDB, nil
}

func (e *ExecutePartitionSQLComp) excuteInitSql(
	partitionSQLSets []InitPartitionContent,
	connum int, myInsInfo MyInstanceInfo,
) (err error) {
	// 在执行初始化分区前，需要预先检查磁盘剩余空间是否满足初始化分区的条件
	// 使用pt工具执行初始化分区，暂时不做并发操作
	errs := []string{}
	for _, partitionSQL := range partitionSQLSets {
		// 检查磁盘这个行为执行是正确的 但实际对应分区逻辑是执行失败的 所以要把错误报出来
		// precheck中进行错误的信息处理
		flag, err := e.precheck(partitionSQL.NeedSize, myInsInfo)
		pt_tool := "percona-toolkit-3.5.0/bin/pt-online-schema-change"
		user := e.GeneralParam.RuntimeAccountParam.PartitionYwUser
		pwd := e.GeneralParam.RuntimeAccountParam.PartitionYwPwd
		command := fmt.Sprintf("%s/%s -u%s -p%s --socket %s %s", cst.DBAToolkitPath,
			pt_tool, user, pwd, myInsInfo.Socket, partitionSQL.Sql)
		if err != nil {
			return err
		}
		if flag {
			err := mysqlutil.ExecuteSqlAtLocal{
				WorkDir:          e.WorkDir,
				IsForce:          e.Params.Force,
				Charset:          "utf8",
				NeedShowWarnings: false,
				Host:             myInsInfo.Ip,
				Port:             myInsInfo.Port,
				Socket:           myInsInfo.Socket,
				User:             e.GeneralParam.RuntimeAccountParam.PartitionYwPwd,
				Password:         e.GeneralParam.RuntimeAccountParam.PartitionYwPwd,
			}.ExecuteInitPartition(command)
			if err != nil {
				errs = append(errs, fmt.Sprintf("%s执行失败，报错：%s", command, err.Error()))
			}
		}
	}
	if len(errs) > 0 {
		return fmt.Errorf(fmt.Sprintf("%s", strings.Join(errs, "\n")))
	}
	return nil
}

func (e *ExecutePartitionSQLComp) precheck(needSize int64, myInsInfo MyInstanceInfo) (flag bool, err error) {
	// (已用磁盘空间+3*表大小)/总容量<95%
	// (可用磁盘空间+NeedSize)/总容量>5%
	// 连接db
	dbConn, err := native.InsObject{
		Host: myInsInfo.Ip,
		Port: myInsInfo.Port,
		User: myInsInfo.User,
		Pwd:  myInsInfo.Pwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect %d failed:%s", myInsInfo.Port, err.Error())
		return false, err
	}
	datadir, err := dbConn.GetSingleGlobalVar("datadir")
	if err != nil {
		return false, err
	}

	diskInfo, err := osutil.GetLinuxDirDiskInfo(datadir)
	if err != nil {
		return false, err
	}
	size, err := strconv.ParseInt(diskInfo.Blocks_1K, 10, 64)
	if err != nil {
		return false, err
	}
	rate := (float64(diskInfo.Available) + float64(needSize/1024)) / float64(size)

	if rate > 0.05 {
		flag = true
	} else {
		flag = false
		err = fmt.Errorf("当前磁盘空间使用率为：%f，建议先进行数据清理，请联系dba处理。", 1-rate)
	}
	return flag, nil
}

func (e *ExecutePartitionSQLComp) getPartitionInfo(filePath string) (epsos []FilePartitionSQLObj, err error) {
	f, err := os.ReadFile(filePath)
	if err != nil {
		return nil, errors.New(fmt.Sprintf("读取文件失败！--->%s", err.Error()))
	}
	err = json.Unmarshal(f, &epsos)
	if err != nil {
		return nil, errors.New(fmt.Sprintf("反序列化失败！--->%s", err.Error()))
	}
	return epsos, nil
}

// replace 反引号进行转义 可在命令行中执行
func (e *ExecutePartitionSQLComp) replace(partitionSQL string) string {
	return strings.Replace(partitionSQL, "`", "\\`", -1)
}

func (e *ExecutePartitionSQLComp) getInitPartitionSQL(initPartitions []InitPartitionContent) []string {
	var initPartitionSQL []string
	for _, initPartition := range initPartitions {
		initsql := fmt.Sprintf("%s;;;%s;", "set tc_admin=0", initPartition.Sql)
		initPartitionSQL = append(initPartitionSQL, initsql)
	}
	return initPartitionSQL
}

func (e *ExecutePartitionSQLComp) getNewPartitionSQL(partitionSQLs []string) []string {
	var newPartitionSQLs []string
	for _, parsql := range partitionSQLs {
		mysql := fmt.Sprintf("%s;;;%s;", "set tc_admin=0", parsql)
		newPartitionSQLs = append(newPartitionSQLs, mysql)
	}
	return newPartitionSQLs
}

func (e *ExecutePartitionSQLComp) initSQLClassify(initPartitions []InitPartitionContent) (
	[]InitPartitionContent, []string) {
	var hasUnikeyInit []InitPartitionContent
	var hasNotUnikeyInit []string

	for _, initPartition := range initPartitions {
		if initPartition.HasUniqueKey {
			hasUnikeyInit = append(hasUnikeyInit, initPartition)
		} else {
			hasNotUnikeyInit = append(hasNotUnikeyInit, initPartition.Sql)
		}
	}
	return hasUnikeyInit, hasNotUnikeyInit
}

// getSocket 用于获取mysql sock文件位置
func (my *MyInstanceInfo) getSocket() (socket string, err error) {
	// 连接db
	dbConn, err := native.InsObject{
		Host: my.Ip,
		Port: my.Port,
		User: my.User,
		Pwd:  my.Pwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect %d failed:%s", my.Port, err.Error())
		return "", err
	}
	if socket, err = dbConn.ShowSocket(); err != nil {
		logger.Error("获取socket value 失败:%s", err.Error())
		return "", err
	}
	if !cmutil.FileExists(socket) {
		socket = ""
	}
	return socket, nil
}

func getAllReturnInfo(filePartitionSQLObjs []FilePartitionSQLObj, msg string) (all []ReturnInfo) {
	for _, fpobj := range filePartitionSQLObjs {
		for _, epobj := range fpobj.ExecuteObjects {
			var returnInfo ReturnInfo
			returnInfo.ConfigId = epobj.ConfigID
			returnInfo.Status = "failed"
			returnInfo.Msg = msg
			all = append(all, returnInfo)
		}
	}
	return
}

func getOneInsReturnInfo(fpobj FilePartitionSQLObj, msg string) (all []ReturnInfo) {
	ip := fpobj.Ip
	port := fpobj.Port
	for _, epobj := range fpobj.ExecuteObjects {
		var returnInfo ReturnInfo
		returnInfo.ConfigId = epobj.ConfigID
		returnInfo.Status = "failed"
		returnInfo.Msg = fmt.Sprintf("instance is %s#%d. %s", ip, port, msg)
		all = append(all, returnInfo)
	}
	return
}

func getOneReturnInfo(configId int, status string, msg string) (oneRetInfo ReturnInfo) {
	oneRetInfo.ConfigId = configId
	oneRetInfo.Status = status
	oneRetInfo.Msg = msg
	return
}
