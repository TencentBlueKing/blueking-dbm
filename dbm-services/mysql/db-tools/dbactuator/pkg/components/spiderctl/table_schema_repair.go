/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package spiderctl

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	"ariga.io/atlas/sql/migrate"
	"ariga.io/atlas/sql/mysql"
	"ariga.io/atlas/sql/schema"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// TableSchemaRepairComp TODO
type TableSchemaRepairComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       TableSchemaRepairParam
	tableSchemaRepairCtx
}

// TableSchemaRepairParam TODO
type TableSchemaRepairParam struct {
	Host    string `json:"host" validate:"required,ip"`
	Port    int    `json:"port" validate:"required,lt=65536,gte=3306"`
	AutoFix bool   `json:"auto_fix"`
	// 必须指定一个待修复的库
	Db     string   `json:"db"`
	Tables []string `json:"tables"`
	DryRun bool     `json:"dry_run"`
}
type tableSchemaRepairCtx struct {
	tdbCtlConn        *native.TdbctlDbWork
	taskdir           string
	svrNameServersMap map[SVRNAME]native.Server
	primarySpts       []native.Server
	spiderSpts        []native.Server
}

// Example TODO
func (r *TableSchemaRepairComp) Example() interface{} {
	return &TableSchemaRepairParam{
		Host: "127.0.0.1",
		Port: 3306,
		Db:   "test",
		Tables: []string{
			"test",
		},
		DryRun: true,
	}
}

// Init TODO
func (r *TableSchemaRepairComp) Init() (err error) {
	// connection central control
	conn, err := native.InsObject{
		Host: r.Params.Host,
		Port: r.Params.Port,
		User: r.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  r.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("connect to tdbctl failed, err: %v", err)
		return err
	}
	r.tdbCtlConn = &native.TdbctlDbWork{DbWorker: *conn}
	servers, err := r.tdbCtlConn.SelectServers()
	if err != nil {
		logger.Error("select servers failed, err: %v", err)
		return err
	}
	_, r.svrNameServersMap = transServersToMap(servers)
	for _, server := range servers {
		if native.SvrNameIsMasterShard(server.ServerName) {
			r.primarySpts = append(r.primarySpts, server)
		}
		if native.SvrNameIsMasterSpiderShard(server.ServerName) {
			r.spiderSpts = append(r.spiderSpts, server)
		}
	}
	return nil
}

type repairTableInfo struct {
	native.SchemaCheckResult
	referDb string
}

// RunAutoFix TODO
// 根据校验的结果来自动修复 无需指定修复的库表
func (r *TableSchemaRepairComp) RunAutoFix() (err error) {
	abnormalChecksums, err := r.tdbCtlConn.GetAbnormalSchemaChecksum()
	if err != nil {
		logger.Error("get abnormal schema checksum failed, err: %v", err)
		return err
	}
	if len(abnormalChecksums) <= 0 {
		logger.Info("no abnormal table structure check record was found,bye~")
		return nil
	}
	logger.Info("found %d abnormal table structure check record(s)", len(abnormalChecksums))
	// 根据serverName分组需要修复的表信息
	fixMap := make(map[SVRNAME][]repairTableInfo)
	for _, abnormalChecksum := range abnormalChecksums {
		var abnormalDetails []native.SchemaCheckResult
		if err = json.Unmarshal(abnormalChecksum.ChecksumResult, &abnormalDetails); err != nil {
			logger.Error("unmarshal abnormal checksum result failed, err: %v", err)
			return err
		}
		for _, abnormalDetail := range abnormalDetails {
			fixMap[abnormalDetail.ServerName] = append(fixMap[abnormalDetail.ServerName], repairTableInfo{
				SchemaCheckResult: abnormalDetail,
				referDb:           abnormalChecksum.Db,
			})
		}
	}
	var referSchema *schema.Schema
	var referConn migrate.Driver
	if referConn, err = mysql.Open(r.tdbCtlConn.Db); err != nil {
		logger.Error("open refer conn failed, err: %v", err)
		return err
	}
	logger.Info("open refer conn success")
	// 根据得到的分组结果来进行修复
	for svrName, abnormalDetails := range fixMap {
		// 根据dbName 来分组需要修复的表信息
		fixMapByDb := make(map[string][]string)
		referDbMap := make(map[string]string)
		for _, repairTableInfo := range abnormalDetails {
			fixMapByDb[repairTableInfo.Db] = append(fixMapByDb[repairTableInfo.Db], repairTableInfo.Table)
			referDbMap[repairTableInfo.Db] = repairTableInfo.referDb
		}
		svr, ok := r.svrNameServersMap[svrName]
		if !ok {
			return fmt.Errorf("server %s not found", svrName)
		}
		logger.Info("will fix on %s:%s", svrName, svr.GetEndPoint())
		for db, tables := range fixMapByDb {
			if referSchema, err = referConn.InspectSchema(context.Background(), referDbMap[db], &schema.InspectOptions{
				Tables: tables,
			}); err != nil {
				logger.Error("get schema failed, err: %v", err)
				return err
			}
			if err = r.do(svr, db, referConn, referSchema); err != nil {
				return err
			}
		}
	}
	return nil
}

// Run TODO
func (r *TableSchemaRepairComp) Run() (err error) {
	var referSchema *schema.Schema
	var referConn migrate.Driver
	if referConn, err = mysql.Open(r.tdbCtlConn.Db); err != nil {
		return err
	}
	if referSchema, err = referConn.InspectSchema(context.Background(), r.Params.Db, &schema.InspectOptions{
		Tables: r.Params.Tables,
	}); err != nil {
		return err
	}
	for _, spiderSvr := range r.spiderSpts {
		logger.Info("start repair table schema on %s", spiderSvr.ServerName)
		err = r.do(spiderSvr, r.Params.Db, referConn, referSchema)
		if err != nil {
			logger.Error("repair table schema on %s failed, err: %v", spiderSvr.ServerName, err)
			return err
		}
	}
	for _, primarySvr := range r.primarySpts {
		logger.Info("start repair table schema on %s --%s:%d", primarySvr.ServerName, primarySvr.Host, primarySvr.Port)
		shardNum := native.GetShardNumberFromMasterServerName(primarySvr.ServerName)
		dbName := fmt.Sprintf("%s_%s", r.Params.Db, shardNum)
		if err = r.do(primarySvr, dbName, referConn, referSchema); err != nil {
			logger.Error("repair table schema on %s failed, err: %v", primarySvr.ServerName, err)
			return err
		}
	}
	return nil
}

func (r *TableSchemaRepairComp) do(node native.Server, dbName string, referConn migrate.Driver,
	referSchema *schema.Schema) (err error) {
	logger.Info("start repair table schema on %s -- %s:%d", node.ServerName, node.Host, node.Port)
	conn, err := node.Opendb(dbName)
	if err != nil {
		logger.Error("open db failed, err: %v", err)
		return err
	}
	defer conn.Close()
	fromConn, err := mysql.Open(conn)
	if err != nil {
		logger.Error("open migrate driver failed, err: %v", err)
		return err
	}
	sqlfile := fmt.Sprintf("%s_%s_%d.fix.sql", node.ServerName, node.Host, node.Port)
	if cmutil.FileExists(sqlfile) {
		if err = os.Remove(sqlfile); err != nil {
			logger.Error("remove sql file failed, err: %v", err)
			return err
		}
	}
	fd, err := os.Create(sqlfile)
	if err != nil {
		logger.Error("create sql file failed, err: %v", err)
		return err
	}
	defer fd.Close()
	if err = do(dbName, fromConn, referConn, referSchema, r.Params.DryRun, fd); err != nil {
		return err
	}
	return nil
}

func do(dbName string, fromConn, referConn migrate.Driver, referSchema *schema.Schema, dryrun bool,
	fd *os.File) (err error) {
	mSchema, err := fromConn.InspectSchema(context.Background(), dbName, &schema.InspectOptions{})
	if err != nil {
		logger.Error("inspect schema failed, err: %v", err)
		return err
	}
	mSchema.Name, referSchema.Name = "", ""
	changes, err := referConn.SchemaDiff(mSchema, referSchema, schema.DiffSkipChanges(&schema.DropTable{},
		&schema.DropSchema{}))
	if err != nil {
		logger.Error("schema diff failed, err: %v", err)
		return err
	}
	plan, err := referConn.PlanChanges(context.TODO(), dbName, changes)
	if err != nil {
		logger.Error("plan changes failed, err: %v", err)
		return err
	}
	files, err := migrate.DefaultFormatter.Format(plan)
	if err != nil {
		logger.Error("format plan failed, err: %v", err)
		return err
	}
	for _, f := range files {
		logger.Info(string(f.Bytes()))
		if _, err = fd.Write(f.Bytes()); err != nil {
			logger.Warn("write file failed, err: %v", err)
		}
	}
	// if dry run , return
	if dryrun {
		logger.Info("dry run, no changes will be applied")
		return nil
	}
	if err = fromConn.ApplyChanges(context.TODO(), changes); err != nil {
		logger.Error("apply changes failed, err: %v", err)
		return err
	}
	return nil
}
