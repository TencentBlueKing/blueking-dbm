/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package sqlserver

import (
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// SQLFileExecuteComp TODO
type SQLFileExecuteComp struct {
	GeneralParam         *components.GeneralParam `json:"general"`
	Params               *SQLFileExecuteParam     `json:"extend"`
	ExecuteSQLRunTimeCtx `json:"-"`
}

// SQLFileExecuteParam TODO
type SQLFileExecuteParam struct {
	Host          string              `json:"host"  validate:"required,ip"`        // 当前实例的主机地址
	Ports         []int               `json:"ports" validate:"required,gt=0,dive"` // 被监控机器的上所有需要监控的端口
	CharSetNO     int                 `json:"charset_no" validate:"required"`      // 连接DB客户端的文件格式代码页
	FilePath      string              `json:"file_path"`                           // 文件路径
	ExcuteObjects []SQLFileExecuteObj `json:"execute_objects" validate:"required"` // 变更需求列表
	Force         bool                `json:"force"`                               // 是否强制执行 执行出错后，是否继续往下执行
}

// ExcuteSQLFileObj 单个文件的执行对象
// 一次可以多个文件操作不同的数据库
type SQLFileExecuteObj struct {
	SQLFile       string   `json:"sql_file"  validate:"required"`       // 变更文件名称
	IgnoreDbNames []string `json:"ignore_dbnames"  validate:"required"` // 忽略的,需要排除变更的dbName,支持模糊匹配
	DbNames       []string `json:"dbnames"  validate:"required" `       // 需要变更的DBNames,支持模糊匹配
}

// ExcuteSQLFileRunTimeCtx 运行时上下文
type ExecuteSQLRunTimeCtx struct {
	DbConns     map[int]*sqlserver.DbWorker
	SQLVersions map[int]string
	TaskDir     string
}

// Example TODO
func (s *SQLFileExecuteComp) Example() interface{} {
	return SQLFileExecuteComp{
		GeneralParam: &components.GeneralParam{},
		Params: &SQLFileExecuteParam{
			Host:      "127.0.0.1",
			Ports:     []int{48322, 48332},
			CharSetNO: 936, //BGK
			FilePath:  "d:\\workspace",
			ExcuteObjects: []SQLFileExecuteObj{
				{
					SQLFile:       "111.sql",
					IgnoreDbNames: []string{"a%"},
					DbNames:       []string{"db1", "db2"},
				},
			},
			Force: false,
		},
	}
}

// Percheck TODO
// 执行前预检测，检查变更实例是否异常
func (s *SQLFileExecuteComp) PreCheck() (err error) {
	s.DbConns = make(map[int]*sqlserver.DbWorker)
	s.SQLVersions = make(map[int]string)
	for _, port := range s.Params.Ports {
		// 遍历每个port
		var dbWork *sqlserver.DbWorker
		if dbWork, err = sqlserver.NewDbWorker(
			s.GeneralParam.RuntimeAccountParam.SAUser,
			s.GeneralParam.RuntimeAccountParam.SAPwd,
			s.Params.Host,
			port,
		); err != nil {
			// 如果其中一个端口连接失败，则退出异常
			logger.Error("connenct by %d failed,err:%s", port, err.Error())
			return err
		}

		// 获取版本信息
		version, err := dbWork.GetVersion()

		if err != nil {
			// 如果其中一个失败，则退出异常
			logger.Error("get version info  by %d failed,err:%s", port, err.Error())
			return err
		}
		s.DbConns[port] = dbWork
		s.SQLVersions[port] = version

		// 拼接工作目录
		s.TaskDir = strings.TrimSpace(s.Params.FilePath)
		if s.TaskDir == "" {
			s.TaskDir = fmt.Sprintf("%s\\%s", cst.BASE_DATA_PATH, cst.BK_PKG_INSTALL_NAME)
		}

	}
	return nil
}

// ExecuteSQLFiles TODO
// 执行导入SQL文件
func (s *SQLFileExecuteComp) ExecuteSQLFiles() (err error) {
	for _, port := range s.Params.Ports {
		if err = s.executeForport(port); err != nil {
			logger.Error("execute at %d failed: %s", port, err.Error())
			return err
		}
	}
	return nil
}

// executeForport TODO
// 根据端口执行执行导入SQL文件
// todo 需要考虑过滤系统DB吗？
func (s *SQLFileExecuteComp) executeForport(port int) (err error) {
	logger.Info("execute sql files in the port [%d]", port)
	var realexcutedbs []string
	alldbs, err := s.DbConns[port].ShowDatabases()
	if err != nil {
		logger.Error("获取实例db list失败:%s", err.Error())
		return err
	}
	// 先判断SQL文件所执行DB是否实例DB列表上
	for _, object := range s.Params.ExcuteObjects {

		// 如果存入master作为变更库，则直接返回master库作为变更, 否则进入判断业务库逻辑
		if len(object.DbNames) == 1 && object.DbNames[0] == "master" && len(object.IgnoreDbNames) == 0 {
			realexcutedbs = []string{"master"}
		} else {
			// 获取业务目标库
			intentionDbs, err := util.DbMatch(alldbs, util.ChangeToMatch(object.DbNames))
			if err != nil {
				return err
			}
			// 获取业务忽略库
			ignoreDbs, err := util.DbMatch(alldbs, util.ChangeToMatch(object.IgnoreDbNames))
			if err != nil {
				return err
			}
			// 获取最终需要执行的库
			realexcutedbs = util.FilterOutStringSlice(intentionDbs, ignoreDbs)
			if len(realexcutedbs) <= 0 {
				return fmt.Errorf("没有适配到任何db")
			}
		}

		files := []string{fmt.Sprintf("%s\\%s", s.TaskDir, object.SQLFile)}
		logger.Info("will real execute sqlfile %s on %v", files[0], realexcutedbs)

		// 调用本地执行SQL
		for _, dbNames := range realexcutedbs {
			if err := sqlserver.ExecLocalSQLFile(
				s.SQLVersions[port], dbNames, s.Params.CharSetNO, files, port); err != nil {
				return err
			}
		}

	}

	return nil
}
