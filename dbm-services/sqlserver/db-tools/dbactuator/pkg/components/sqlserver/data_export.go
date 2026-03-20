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
	"path"
	"path/filepath"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// DataExportComp TODO
type DataExportComp struct {
	GeneralParam         *components.GeneralParam `json:"general"`
	Params               *DataExportParam         `json:"extend"`
	DataExportRunTimeCtx `json:"-"`
}

// DataExportParam TODO
type DataExportParam struct {
	Host          string                   `json:"host"  validate:"required,ip"`                                // 当前实例的主机地址
	Ports         []int                    `json:"ports" validate:"required,gt=0,dive"`                         // 被监控机器的上所有需要监控的端口
	ClusterDomain string                   `json:"cluster_domain" validate:"required"`                          // 实例所在集群域名
	InstanceRole  string                   `json:"instance_role" validate:"required,oneof=master slave orphan"` // 实例的角色
	FilePath      string                   `json:"file_path" validate:"required"`                               // 文件路径
	ZipFileName   string                   `json:"zip_file_name" validate:"required"`                           // 压缩文件名称
	ExcuteObjects []DataExportObj          `json:"execute_objects" validate:"required"`                         // 变更需求列表
	UploadDetail  osutil.UploadBkRepoParam `json:"upload_detail"`
}

// ExcuteSQLFileObj 单个文件的执行对象
// 一次可以多个文件操作不同的数据库
type DataExportObj struct {
	SQLFiles      []string `json:"sql_files"  validate:"required"`      // 变更文件名称
	IgnoreDbNames []string `json:"ignore_dbnames"  validate:"required"` // 忽略的,需要排除变更的dbName,支持模糊匹配
	DbNames       []string `json:"dbnames"  validate:"required" `       // 需要变更的DBNames,支持模糊匹配
}

// ExcuteSQLFileRunTimeCtx 运行时上下文
type DataExportRunTimeCtx struct {
	DbConns     map[int]*sqlserver.DbWorker
	SQLVersions map[int]string
	TaskDir     string
	CsvFiles    []string
}

// Example TODO
func (d *DataExportComp) Example() interface{} {
	return DataExportComp{
		GeneralParam: &components.GeneralParam{},
		Params: &DataExportParam{
			Host:     "127.0.0.1",
			Ports:    []int{48322, 48332},
			FilePath: "d:\\workspace",
			ExcuteObjects: []DataExportObj{
				{
					SQLFiles:      []string{"111.sql"},
					IgnoreDbNames: []string{"a%"},
					DbNames:       []string{"db1", "db2"},
				},
			},
		},
	}
}

// Percheck TODO
// 执行前预检测，检查变更实例是否异常
func (d *DataExportComp) PreCheck() (err error) {
	d.DbConns = make(map[int]*sqlserver.DbWorker)
	d.SQLVersions = make(map[int]string)
	for _, port := range d.Params.Ports {
		// 遍历每个port
		var dbWork *sqlserver.DbWorker
		if dbWork, err = sqlserver.NewDbWorker(
			d.GeneralParam.RuntimeAccountParam.DRSDataReadUser,
			d.GeneralParam.RuntimeAccountParam.DRSDataReadPwd,
			d.Params.Host,
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
		d.DbConns[port] = dbWork
		d.SQLVersions[port] = version

		// 拼接工作目录
		d.TaskDir = strings.TrimSpace(d.Params.FilePath)
		if d.TaskDir == "" {
			d.TaskDir = filepath.Join(cst.BASE_DATA_PATH, cst.BK_PKG_INSTALL_NAME)
		}

	}
	return nil
}

// DataExportForPort TODO
// 根据不同的端口导出数据
func (d *DataExportComp) DataExportForPort(port int) (err error) {
	logger.Info("execute sql files in the port [%d]", port)
	var getdbs []string
	var realexcutedbs []string
	switch d.Params.InstanceRole {
	case "master":
		// 主库
		getdbs, err = d.DbConns[port].ShowDatabases()
	case "slave":
		// 从库
		getdbs, err = d.DbConns[port].ShowDatabasesIncludeSnapshots()
	case "orphan":
		// 孤立库
		getdbs, err = d.DbConns[port].ShowDatabases()
	default:
		return fmt.Errorf("不支持的实例角色:%s", d.Params.InstanceRole)
	}
	if err != nil {
		logger.Error("获取实例db list失败:%s", err.Error())
		return err
	}
	// 先判断SQL文件所执行DB是否实例DB列表上
	for _, object := range d.Params.ExcuteObjects {

		// 如果存入master作为变更库，则直接返回master库作为变更, 否则进入判断业务库逻辑
		if len(object.DbNames) == 1 && object.DbNames[0] == "master" && len(object.IgnoreDbNames) == 0 {
			realexcutedbs = []string{"master"}
		} else {
			// 获取业务目标库
			intentionDbs, err := util.DbMatch(getdbs, util.ChangeToMatch(object.DbNames))
			if err != nil {
				return err
			}
			// 获取业务忽略库
			ignoreDbs, err := util.DbMatch(getdbs, util.ChangeToMatch(object.IgnoreDbNames))
			if err != nil {
				return err
			}
			// 获取最终需要执行的库
			realexcutedbs = util.FilterOutStringSlice(intentionDbs, ignoreDbs)
			if len(realexcutedbs) <= 0 {
				return fmt.Errorf("没有适配到任何db")
			}
		}

		// 遍历每个sql文件
		for _, sqlfile := range object.SQLFiles {
			files := []string{filepath.Join(d.TaskDir, sqlfile)}
			logger.Info("will real execute sqlfile %s on %v", files[0], realexcutedbs)

			// 调用本地执行SQL
			// 并发起文件上传
			for _, dbNames := range realexcutedbs {
				var outFiles []string
				if outFiles, err = sqlserver.ExecLocalSQLFileForDataExport(
					d.Params.ClusterDomain,
					d.SQLVersions[port],
					dbNames,
					files,
					port,
					d.GeneralParam.RuntimeAccountParam.DRSDataReadUser,
					d.GeneralParam.RuntimeAccountParam.DRSDataReadPwd,
				); err != nil {
					return err
				}
				// 将文件添加到csv文件列表中
				d.CsvFiles = append(d.CsvFiles, outFiles...)
			}

		}

	}
	// 将csv文件打包成zip文件
	if err = osutil.ZipFiles(d.CsvFiles, path.Join(d.TaskDir, d.Params.ZipFileName)); err != nil {
		logger.Error("zip files failed: %s", err.Error())
		return err
	}
	return nil
}

// DataExport
// 执行数据导出
func (d *DataExportComp) DataExport() error {
	for _, port := range d.Params.Ports {
		if err := d.DataExportForPort(port); err != nil {
			logger.Error("data export at %d failed: %s", port, err.Error())
			return err
		}
	}
	return nil
}

// UploadResult TODO
// 上传结果在制品库
func (d *DataExportComp) UploadResult() (err error) {
	logger.Info("start uploading...")
	up := d.Params.UploadDetail
	up.BackupFileName = d.Params.ZipFileName
	up.BackupDir = d.TaskDir
	return up.Upload()
}
