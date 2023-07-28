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
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	ma "dbm-services/mysql/db-tools/mysql-crond/api"
)

// ExcutePartitionSQLComp TODO
type ExcutePartitionSQLComp struct {
	GeneralParam                 *components.GeneralParam `json:"general"`
	Params                       *ExcutePartitionSQLParam `json:"extend"`
	ExcutePartitionSQLRunTimeCtx `json:"-"`
}

// ExcutePartitionSQLParam TODO
type ExcutePartitionSQLParam struct {
	BkBizId      int    `json:"bk_biz_id"`
	ClusterId    int    `json:"cluster_id"`
	ImmuteDomain string `json:"immute_domain"`
	MasterIp     string `json:"master_ip"  validate:"required,ip"` // 当前实例的主机地址
	MasterPort   int    `json:"master_port"`                       // 被监控机器的上所有需要监控的端口
	ShardName    string `json:"shard_name"`
	Ticket       string `json:"ticket"`
	FilePath     string `json:"file_path"`
	Force        bool   `json:"force"`
}

// ExcutePartitionSQLObj TODO
type ExcutePartitionSQLObj struct {
	ConfigID      int                    `json:"config_id"`
	Dblike        string                 `json:"dblike"`
	Tblike        string                 `json:"tblike"`
	InitPartition []InitPartitionContent `json:"init_partition"`
	AddPartition  []string               `json:"add_partition"`
	DropPartition []string               `json:"drop_partition"`
}

// InitPartitionContent TODO
type InitPartitionContent struct {
	NeedSize int64  `json:"need_size"`
	Sql      string `json:"sql"`
}

// ExcutePartitionSQLRunTimeCtx TODO
type ExcutePartitionSQLRunTimeCtx struct {
	port                 int
	dbConns              *native.DbWorker
	ver                  string // 当前实例的版本
	charset              string // 当前实例的字符集
	socket               string // 当前实例的socket value
	RegularIgnoreDbNames []string
	RegularDbNames       []string
	WorkDir              string
}

// Example TODO
func (e *ExcutePartitionSQLComp) Example() interface{} {
	comp := ExcutePartitionSQLComp{
		Params: &ExcutePartitionSQLParam{
			BkBizId:      0,
			ClusterId:    0,
			ImmuteDomain: "xxx.xxx.xxx",
			MasterIp:     "1.1.1.1",
			MasterPort:   0,
			ShardName:    "xxx",
			Ticket:       "https://www.xxx.com",
			FilePath:     "/xxx/xxx/xxx.txt",
			Force:        false,
		},
	}
	return comp
}

// Init TODO
func (e *ExcutePartitionSQLComp) Init() (err error) {
	e.port = e.Params.MasterPort
	var ver, charset, socket string
	dbConn, err := native.InsObject{
		Host: e.Params.MasterIp,
		Port: e.port,
		User: e.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  e.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect %d failed:%s", e.port, err.Error())
		return err
	}
	if ver, err = dbConn.SelectVersion(); err != nil {
		logger.Error("获取实例版本失败:%s", err.Error())
		return err
	}

	if socket, err = dbConn.ShowSocket(); err != nil {
		logger.Error("获取socket value 失败:%s", err.Error())
		return err
	}
	if !cmutil.FileExists(socket) {
		socket = ""
	}
	e.dbConns = dbConn
	e.ver = ver
	e.socket = socket
	e.charset = charset
	e.WorkDir = fmt.Sprintf("%s/%s", cst.BK_PKG_INSTALL_PATH, "partition")
	_ = os.MkdirAll(e.WorkDir, 0755)
	return nil
}

// Excute TODO
func (e *ExcutePartitionSQLComp) Excute() (err error) {
	// 以单个执行目标为单位 execute_objects
	executeObjects, err := e.getPartitionInfo(e.Params.FilePath)

	if err != nil {
		logger.Error(err.Error())
		return err
	}
	ip := e.Params.MasterIp
	port := e.Params.MasterPort
	user := e.GeneralParam.RuntimeAccountParam.AdminUser
	pwd := e.GeneralParam.RuntimeAccountParam.AdminPwd
	param := ""
	if strings.Contains(e.Params.ShardName, "TDBCTL") {
		param = "&tc_admin=0"
	}

	dbw, err := initDB(ip, port, user, pwd, param)
	defer func() {
		if dbw != nil {
			dbw.Close()
		}
	}()
	c := make(chan struct{}, 4)
	wg := &sync.WaitGroup{}
	errs := []string{}
	lock := &sync.Mutex{}
	for _, eb := range executeObjects {
		c <- struct{}{}
		wg.Add(1)
		// 并发执行ExcutePartitionSQLObj
		go func(eb ExcutePartitionSQLObj) {
			defer wg.Done()
			// 每条分区config为一个单位，根据ConfigID生成一个对应的错误文件
			errfile := fmt.Sprintf("partition_%d_%s.err", eb.ConfigID, time.Now().Format("20060102150405"))
			errsall := []string{}

			// 依次执行初始化、添加、删除
			// 每个任务中会并发执行单条sql
			if len(eb.InitPartition) > 0 {
				logger.Info(fmt.Sprintf("初始化分区，config_id=%d\n", eb.ConfigID))
				if strings.Contains(e.Params.ShardName, "TDBCTL") {
					// TDBCTL不使用pt工具
					initPartition := e.getInitPartitionSQL(eb.InitPartition)
					err = e.excuteOne(dbw, initPartition, errfile, 10)
				} else {
					// 初始化分区使用pt工具，因此通过命令行的形式进行执行
					err = e.excuteInitSql(eb.InitPartition, errfile, 10)
				}
				if err != nil {
					lock.Lock()
					errsall = append(errsall, err.Error())
					lock.Unlock()
				} else {
					logger.Info("初始化分区成功！")
				}
			}
			if len(eb.AddPartition) > 0 {
				logger.Info(fmt.Sprintf("添加分区，config_id=%d\n", eb.ConfigID))
				err := e.excuteOne(dbw, eb.AddPartition, errfile, 20)
				if err != nil {
					lock.Lock()
					errsall = append(errsall, err.Error())
					lock.Unlock()
				} else {
					logger.Info("添加分区成功！")
				}
			}
			if len(eb.DropPartition) > 0 {
				logger.Info(fmt.Sprintf("删除分区，config_id=%d\n", eb.ConfigID))
				err := e.excuteOne(dbw, eb.DropPartition, errfile, 20)
				if err != nil {
					lock.Lock()
					errsall = append(errsall, err.Error())
					lock.Unlock()
				} else {
					logger.Info("删除分区成功！")
				}
			}
			if len(errsall) > 0 {
				body := struct {
					Name      string
					Content   string
					Dimension map[string]interface{}
				}{}
				body.Name = "partition"
				body.Content = fmt.Sprintf("%s。单据号：%s", "分区任务执行失败", e.Params.Ticket)
				body.Dimension = make(map[string]interface{})
				body.Dimension["config_id"] = eb.ConfigID
				body.Dimension["dblike"] = eb.Dblike
				body.Dimension["tblike"] = eb.Tblike
				body.Dimension["ticket"] = e.Params.Ticket
				body.Dimension["immute_domain"] = e.Params.ImmuteDomain
				body.Dimension["shard_name"] = e.Params.ShardName
				manager := ma.NewManager("http://127.0.0.1:9999")
				sendErr := manager.SendEvent(body.Name, body.Content, body.Dimension)
				errs = append(errs, strings.Join(errsall, ";\n"))
				if sendErr != nil {
					logger.Error(fmt.Sprintf("上报失败:%s\n", sendErr.Error()))
				}
			}
			<-c
		}(eb)
	}
	wg.Wait()
	if len(errs) > 0 {
		return errors.New(strings.Join(errs, ";\n"))
	}
	return nil
}

// excuteOne 以执行目标为单位
func (e *ExcutePartitionSQLComp) excuteOne(
	dbw *sql.DB, partitionSQLSet []string, errfile string,
	connum int,
) (err error) {
	wg := sync.WaitGroup{}
	var errs []string
	lock := &sync.Mutex{}
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
				Host:             e.Params.MasterIp,
				Port:             e.Params.MasterPort,
				Socket:           e.socket,
				User:             e.GeneralParam.RuntimeAccountParam.AdminUser,
				Password:         e.GeneralParam.RuntimeAccountParam.AdminPwd,
				ErrFile:          errfile,
			}.ExcutePartitionByMySQLClient(dbw, partitionSQL, lock)
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
func initDB(host string, port int, user string, pwd string, param string) (dbw *sql.DB, err error) {
	tcpdsn := fmt.Sprintf("%s:%d", host, port)
	dsn := fmt.Sprintf(
		"%s:%s@tcp(%s)/?charset=utf8&parseTime=True&loc=Local&timeout=30s&readTimeout=30s&lock_wait_timeout=5%s", user,
		pwd,
		tcpdsn, param,
	)
	SqlDB, err := sql.Open("mysql", dsn)
	if err != nil {
		logger.Error("connect to mysql failed %s", err.Error())
		return nil, err
	}
	return SqlDB, nil
}

func (e *ExcutePartitionSQLComp) excuteInitSql(
	partitionSQLSets []InitPartitionContent, errfile string,
	connum int,
) (err error) {
	// 在执行初始化分区前，需要预先检查磁盘剩余空间是否满足初始化分区的条件
	errs := []string{}
	for _, partitionSQL := range partitionSQLSets {
		flag, err := e.precheck(partitionSQL.NeedSize)
		command := fmt.Sprintf("%s/%s %s", cst.DBAToolkitPath, "percona-toolkit-3.5.0", partitionSQL.Sql)
		if err != nil {
			return err
		}
		if flag {
			err := mysqlutil.ExecuteSqlAtLocal{
				WorkDir:          e.WorkDir,
				IsForce:          e.Params.Force,
				Charset:          "utf8",
				NeedShowWarnings: false,
				Host:             e.Params.MasterIp,
				Port:             e.Params.MasterPort,
				Socket:           e.socket,
				User:             e.GeneralParam.RuntimeAccountParam.AdminUser,
				Password:         e.GeneralParam.RuntimeAccountParam.AdminPwd,
				ErrFile:          errfile,
			}.ExcuteInitPartition(command)
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

func (e *ExcutePartitionSQLComp) precheck(needSize int64) (flag bool, err error) {
	// (已用磁盘空间+3*表大小)/总容量<90%
	// (可用磁盘空间+NeedSize)/总容量>10%
	datadir, err := e.dbConns.GetSingleGlobalVar("datadir")
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
	if rate > 0.1 {
		flag = true
	} else {
		flag = false
	}
	return flag, nil
}

func (e *ExcutePartitionSQLComp) getPartitionInfo(filePath string) (epsos []ExcutePartitionSQLObj, err error) {
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
func (e *ExcutePartitionSQLComp) replace(partitionSQL string) string {
	return strings.Replace(partitionSQL, "`", "\\`", -1)
}

func (e *ExcutePartitionSQLComp) getInitPartitionSQL(initPartitions []InitPartitionContent) []string {
	var initPartitionSQL []string
	for _, initPartition := range initPartitions {
		initPartitionSQL = append(initPartitionSQL, initPartition.Sql)
	}
	return initPartitionSQL
}
