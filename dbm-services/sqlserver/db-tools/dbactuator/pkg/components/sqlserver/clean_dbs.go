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
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// CleanDBSComp 清档数据库
type CleanDBSComp struct {
	GeneralParam *components.GeneralParam
	Params       *CleanDBSParam
	cleanDBSrunTimeCtx
}

// CleanDBSParam 参数
type CleanDBSParam struct {
	Host              string         `json:"host" validate:"required,ip" `            // 本地hostip
	Port              int            `json:"port"  validate:"required,gt=0"`          // 需要操作的实例端口
	CleanDBS          []string       `json:"clean_dbs" validate:"required" `          // 待清理库的列表
	SyncMode          int            `json:"sync_mode" validate:"required"`           // 集群的同步模式分别是：single:3/mirroring:2/alwayson:1
	CleanMode         string         `json:"clean_mode" validate:"required"`          //这次的清档类型：clean_tables/drop_tables/drop_dbs
	Slaves            []cst.Instnace `json:"slaves" `                                 // 集群的从实例
	CleanTables       []string       `json:"clean_tables" validate:"required"`        // 清理表信息
	IgnoreCleanTables []string       `json:"ignore_clean_tables" validate:"required"` // 忽略清理表信息
	IsForce           bool           `json:"is_force" `                               //隐藏参数，是否强制清理
}

// runTimeCtx 上下文
type cleanDBSrunTimeCtx struct {
	DB      *sqlserver.DbWorker
	DRS     []slaves
	RealDBS []string
}

// dirtyTable 清档后未达到预期状态的表信息
type dirtyTable struct {
	SchemaName       string `db:"SchemaName"`
	TableName        string `db:"TableName"`
	RowCnt           int64  `db:"RowCnt"`
	HasIdentity      int    `db:"HasIdentity"`
	IdentityReseedOK int    `db:"IdentityStartsFrom1_OK"`
}

// Init初始化
func (c *CleanDBSComp) Init() error {
	var LWork *sqlserver.DbWorker
	var err error
	// 初始化本地实例连接
	if LWork, err = sqlserver.NewDbWorker(
		c.GeneralParam.RuntimeAccountParam.SAUser,
		c.GeneralParam.RuntimeAccountParam.SAPwd,
		c.Params.Host,
		c.Params.Port,
	); err != nil {
		logger.Error("connenct by [%s:%d] failed,err:%s",
			c.Params.Host, c.Params.Port, err.Error())
		return err
	}
	c.DB = LWork
	// 从实例初始化连接
	for _, s := range c.Params.Slaves {
		var SWork *sqlserver.DbWorker
		if SWork, err = sqlserver.NewDbWorker(
			c.GeneralParam.RuntimeAccountParam.SAUser,
			c.GeneralParam.RuntimeAccountParam.SAPwd,
			s.Host,
			s.Port,
		); err != nil {
			logger.Error("connenct by [%s:%d] failed,err:%s",
				c.Params.Host, c.Params.Port, err.Error())
			return err
		}
		c.DRS = append(c.DRS, slaves{
			Host:   s.Host,
			Port:   s.Port,
			Connet: SWork,
		})
	}
	return nil
}

// PerCheck 预检测
func (c *CleanDBSComp) PerCheck() error {
	var isErr bool
	for _, dbName := range c.Params.CleanDBS {
		// 仅在 drop_dbs 模式下检查DB是否有相关请求
		// 其他清档模式（clean_tables/drop_tables）不做该检查
		if c.Params.CleanMode == "drop_dbs" {
			if !c.DB.CheckDBProcessExist(dbName) && !c.Params.IsForce {
				logger.Error(
					"db:[%s] still has active business connections, "+
						"please check the connection table printed above (use is_force=true to skip)",
					dbName,
				)
				isErr = true
			}
		}
		var sql string = "select count(0) as cnt from master.sys.databases where name = '%s';"
		var cnt int
		// 判断源库名是否存在，如果不存在，打印日志，但不作为报错
		checkOldDBSQL := fmt.Sprintf(sql, dbName)
		if err := c.DB.Queryxs(&cnt, checkOldDBSQL); err != nil {
			logger.Error("check-db failed:%v", err)
			isErr = true
		}
		if cnt == 0 {
			// 代表DB不存在
			logger.Warn("[%s] DB not exists,skip", dbName)
			continue
		}
		// 没有报错则加入待清理数组
		logger.Info("the db [%s] enters the clean queue", dbName)
		c.RealDBS = append(c.RealDBS, dbName)
	}
	if isErr {
		return fmt.Errorf("precheck error")
	}
	return nil
}

// DoCleanDBS 执行清档逻辑
func (c *CleanDBSComp) DoCleanDBS() error {

	if len(c.RealDBS) == 0 {
		// 没有库可操作，正常退出
		return nil
	}

	switch c.Params.CleanMode {
	case "clean_tables":
		if err := c.CleanTablesInDBS(); err != nil {
			return err
		}
	case "drop_tables":
		if err := c.DropTablesInDBS(); err != nil {
			return err
		}
	case "drop_dbs":
		if err := c.DropDBS(); err != nil {
			return err
		}
	default:
		return fmt.Errorf("this clean-mode [%s] of operation is not supported", c.Params.CleanMode)
	}
	return nil
}

// CleanTablesInDBS 清空数据，保留表结构（统一使用安全的 FK 感知方案）
func (c *CleanDBSComp) CleanTablesInDBS() error {
	var isErr bool
	for _, dbName := range c.RealDBS {
		// 获取实际要清理的表清单
		realTables, err := c.DB.GetTableListOnDB(
			dbName,
			c.Params.CleanTables,
			c.Params.IgnoreCleanTables,
		)
		if err != nil {
			logger.Error("get tables list on db [%s] failed:[%v]", dbName, err)
			isErr = true
			continue
		}

		if len(realTables) == 0 {
			logger.Info(
				"table-list is empty on db [%s], skip. CleanTables:[%v];IgnoreCleanTables[%v]",
				dbName,
				c.Params.CleanTables,
				c.Params.IgnoreCleanTables,
			)
			continue
		}

		// 统一使用安全的 execTablesForPer 方法
		if err := c.execTablesForPer("truncate", dbName); err != nil {
			logger.Error("clean tables on db [%s] failed: [%v]", dbName, err)
			isErr = true
		}
	}

	if isErr {
		return fmt.Errorf("clean tables error")
	}
	return nil
}

// checkFKTrusted 校验 DELETE 清档后所有外键的 is_not_trusted 是否都为 0（即都被信任）
// 注意：用户需求中描述的"is_not_trusted 都为 1"应理解为外键都处于"已被信任"状态
// checkFKTrusted 校验 DELETE 清档后所有外键的 is_not_trusted 是否都为 0（即都被信任）
func (c *CleanDBSComp) checkFKTrusted(dbName string) error {
	var notTrustedFKs []string
	checkSQL := fmt.Sprintf(cst.CHECK_FK_NOT_TRUSTED_SQL, dbName)
	if err := c.DB.Queryx(&notTrustedFKs, checkSQL); err != nil {
		return fmt.Errorf("check fk-trusted on db [%s] failed: %v", dbName, err)
	}
	if len(notTrustedFKs) > 0 {
		return fmt.Errorf(
			"after delete-clean on db [%s], the following foreign keys are still not-trusted (is_not_trusted=1), check: %v",
			dbName,
			notTrustedFKs,
		)
	}
	logger.Info("all foreign keys on db [%s] are trusted after clean", dbName)
	return nil
}

// manualFixFKTrusted 手动修复外键信任状态（当自动重试失败时使用）
func (c *CleanDBSComp) manualFixFKTrusted(dbName string) error {
	var notTrustedFKs []string
	checkSQL := fmt.Sprintf(cst.CHECK_FK_NOT_TRUSTED_SQL, dbName)
	if err := c.DB.Queryx(&notTrustedFKs, checkSQL); err != nil {
		return fmt.Errorf("check fk-trusted for manual fix on db [%s] failed: %v", dbName, err)
	}

	if len(notTrustedFKs) == 0 {
		logger.Info("no untrusted foreign keys found on db [%s], manual fix not needed", dbName)
		return nil
	}

	logger.Warn("attempting manual fix for %d untrusted foreign keys on db [%s]: %v",
		len(notTrustedFKs), dbName, notTrustedFKs)

	// 构建手动修复 SQL
	var fixSQLs []string
	for _, fkFullName := range notTrustedFKs {
		// 解析外键完整名称：[schema].[table].[fk_name]
		// 注意：
		//  1) 不能用 strings.Trim(s, "[]")，它是按字符集去除，会把首尾所有连续的
		//     '['、']' 都剥光（若 schema/fk 名以 ] 开头或 [ 结尾会被错误剥离）；
		//  2) 不能直接用 strings.Split(s, "].[")，否则当标识符内部含 "].[" 时
		//     会被切出超过 3 段。
		// 这里通过两次 strings.Index 定位 "].[" 切成 3 段，再各自仅去掉最外层的 '['/']'，
		// 并按 QUOTENAME 规范把内部转义的 "]]" 还原为 "]"。
		schemaName, tableName, fkName, ok := parseQuotedSchemaTableFK(fkFullName)
		if !ok {
			logger.Warn("invalid foreign key format: %s, skipping", fkFullName)
			continue
		}

		// 生成手动修复 SQL
		fixSQL := fmt.Sprintf(
			"ALTER TABLE [%s].[%s] WITH CHECK CHECK CONSTRAINT [%s]",
			schemaName, tableName, fkName,
		)
		fixSQLs = append(fixSQLs, fixSQL)
	}

	if len(fixSQLs) == 0 {
		return fmt.Errorf("no valid foreign keys to fix on db [%s]", dbName)
	}

	// 执行手动修复
	for _, sql := range fixSQLs {
		logger.Info("executing manual FK trust fix: %s", sql)
		if _, err := c.DB.Exec(sql); err != nil {
			logger.Warn("manual FK trust fix failed for SQL [%s]: %v", sql, err)
			// 继续尝试修复其他外键，不立即失败
		}
	}

	// 验证修复结果
	var remainingUntrusted []string
	if err := c.DB.Queryx(&remainingUntrusted, checkSQL); err != nil {
		return fmt.Errorf("verify manual fix result on db [%s] failed: %v", dbName, err)
	}

	if len(remainingUntrusted) > 0 {
		logger.Warn("manual fix partially successful, %d foreign keys still untrusted on db [%s]: %v",
			len(remainingUntrusted), dbName, remainingUntrusted)
		// 记录警告但不阻止操作，让用户决定是否继续
	} else {
		logger.Info("manual FK trust fix on db [%s] completed successfully", dbName)
	}

	return nil
}

// checkCleanResultByList 检查指定表的清理结果
func (c *CleanDBSComp) checkCleanResultByList(dbName string, tables []sqlserver.TableSchema) error {
	if len(tables) == 0 {
		logger.Info("no tables to check on db [%s], skip clean-result check", dbName)
		return nil
	}

	// 构建表清单插入语句
	// 注意：schema/table 名属于用户可控输入，SQL Server 允许在方括号内出现单引号等特殊字符，
	// 这里直接拼接到 N'...' 字符串字面量中存在 SQL 注入/执行报错风险，
	// 需对单引号按 T-SQL 规范转义（' -> ''）。同时显式使用 N'...' 以匹配 NVARCHAR 列。
	var insertRows []string
	for _, t := range tables {
		insertRows = append(insertRows, fmt.Sprintf(
			"INSERT INTO #T(SchemaName, TableName) VALUES(N'%s', N'%s');",
			strings.ReplaceAll(t.SchemaName, "'", "''"),
			strings.ReplaceAll(t.TableName, "'", "''"),
		))
	}
	insertSQL := strings.Join(insertRows, "\n")

	var dirtyTables []dirtyTable
	checkSQL := fmt.Sprintf(cst.CHECK_CLEAN_RESULT_BY_LIST_SQL, dbName, insertSQL)
	if err := c.DB.Queryx(&dirtyTables, checkSQL); err != nil {
		return fmt.Errorf("check clean-result for specified tables on db [%s] failed: %v", dbName, err)
	}

	if len(dirtyTables) == 0 {
		logger.Info("clean-result check pass on db [%s]: all %d target tables are empty and identity reset",
			dbName, len(tables))
		return nil
	}

	// 拼装详细日志
	var notEmptyTables []string
	var identityNotResetTables []string
	for _, t := range dirtyTables {
		fullName := fmt.Sprintf("[%s].[%s]", t.SchemaName, t.TableName)
		if t.RowCnt > 0 {
			notEmptyTables = append(notEmptyTables, fmt.Sprintf("%s(rows=%d)", fullName, t.RowCnt))
		}
		if t.HasIdentity == 1 && t.IdentityReseedOK == 0 {
			identityNotResetTables = append(identityNotResetTables, fullName)
		}
	}

	return fmt.Errorf(
		"clean-result check failed on db [%s]: %d of %d tables not clean, not-empty-tables=%v, identity-not-reset-tables=%v",
		dbName,
		len(dirtyTables),
		len(tables),
		notEmptyTables,
		identityNotResetTables,
	)
}

// DropTablesInDBS 删除表（统一使用安全的 FK 感知方案）
func (c *CleanDBSComp) DropTablesInDBS() error {
	var isErr bool
	for _, dbName := range c.RealDBS {
		// 获取实际要清理的表清单
		realTables, err := c.DB.GetTableListOnDB(
			dbName,
			c.Params.CleanTables,
			c.Params.IgnoreCleanTables,
		)
		if err != nil {
			logger.Error("get tables list on db [%s] failed:[%v]", dbName, err)
			isErr = true
			continue
		}

		if len(realTables) == 0 {
			logger.Info(
				"table-list is empty on db [%s], skip. CleanTables:[%v];IgnoreCleanTables[%v]",
				dbName,
				c.Params.CleanTables,
				c.Params.IgnoreCleanTables,
			)
			continue
		}

		// 统一使用安全的 dropTablesByList 方法
		if err := c.dropTablesByList(dbName, realTables); err != nil {
			logger.Error("drop tables on db [%s] failed: [%v]", dbName, err)
			isErr = true
		}
	}

	if isErr {
		return fmt.Errorf("drop tables error")
	}
	return nil
}

// DropDBS 删除库
func (c *CleanDBSComp) DropDBS() error {
	var isErr bool
	for _, dbName := range c.RealDBS {
		switch c.Params.SyncMode {
		case cst.ALWAYSON:
			if err := c.DropdbwithAlwayson(dbName); err != nil {
				logger.Error(err.Error())
				isErr = true
			}
		case cst.MIRRORING:
			if err := c.DropdbwithMirroring(dbName); err != nil {
				logger.Error(err.Error())
				isErr = true
			}
		default:
			if err := c.DropdbwithMirroring(dbName); err != nil {
				logger.Error(err.Error())
				isErr = true
			}
		}
	}
	if isErr {
		return fmt.Errorf("drop databases error")
	}
	return nil
}

func (c *CleanDBSComp) DropdbwithMirroring(dbName string) error {
	var cnt int
	var checkSQL string
	var dbSnapshots []string
	var execDBSQLs []string

	// mirroring  判断同步方法
	checkSQL = fmt.Sprintf(
		`select count(0) as cnt from master.sys.database_mirroring where 
			database_id= DB_ID('%s') and mirroring_guid is not null`,
		dbName,
	)

	if err := c.DB.Queryxs(&cnt, checkSQL); err != nil {
		return fmt.Errorf("check-db failed %v", err)
	}
	// 表示有建立镜像关系，所以drop之前需要解除
	if cnt != 0 {
		execDBSQLs = append(execDBSQLs, fmt.Sprintf("ALTER DATABASE [%s] SET PARTNER OFF;", dbName))
	}
	// 查询数据库是否有关联的快照库
	getSnapshots := fmt.Sprintf(
		"select name from master.sys.databases where source_database_id = DB_ID('%s')",
		dbName,
	)
	if err := c.DB.Queryx(&dbSnapshots, getSnapshots); err != nil {
		return fmt.Errorf("get-db-snapshots failed %v", err)
	}

	// 如果有存在快照，则先删除快照库
	if len(dbSnapshots) != 0 {
		for _, snapshot := range dbSnapshots {
			execDBSQLs = append(execDBSQLs, fmt.Sprintf("DROP DATABASE [%s];", snapshot))
		}
	}
	// 拼接执行删除源库
	execDBSQLs = append(execDBSQLs, fmt.Sprintf("DROP DATABASE [%s]", dbName))

	// 执行drop 批命令
	if _, err := c.DB.ExecMore(execDBSQLs); err != nil {
		return fmt.Errorf(
			"exec drop database [%s] in DB [%s:%d] failed: [%v]",
			dbName,
			c.Params.Host,
			c.Params.Port,
			err,
		)
	}
	return nil
}

// DropdbwithAlwayson 在Alwayson场景删除库
func (c *CleanDBSComp) DropdbwithAlwayson(dbName string) error {
	var cnt int
	var checkSQL string
	var dbSnapshots []string
	var execDBSQLs []string
	checkSQL = fmt.Sprintf(
		`select count(0) as cnt from master.sys.databases where 
		name= '%s' and replica_id is not null`,
		dbName,
	)
	if err := c.DB.Queryxs(&cnt, checkSQL); err != nil {
		return fmt.Errorf("check-db failed %v", err)
	}
	// 表示有建立同步关系，所以drop之前需要解除
	if cnt != 0 {
		var groupName string
		var role int
		var err error
		if groupName, err = c.DB.GetGroupName(); err != nil {
			return fmt.Errorf("get groupname failed:%v", err)
		}
		// 获取实例角色, 不同的角色用不一样的sql解决同步关系
		if role, err = c.DB.GetRoleInAlwaysOn(); err != nil {
			return fmt.Errorf("get role failed:%v", err)
		}
		switch role {
		case 0:
			return fmt.Errorf("the state for the instance[%s:%d] is Resolving, check ", c.Params.Host, c.Params.Port)
		case 1:
			execDBSQLs = append(
				execDBSQLs,
				fmt.Sprintf("ALTER AVAILABILITY GROUP [%s] REMOVE DATABASE %s;", groupName, dbName),
			)
		case 2:
			execDBSQLs = append(
				execDBSQLs,
				fmt.Sprintf("ALTER DATABASE [%s] SET HADR OFF;", dbName),
			)
		default:
			return fmt.Errorf("not support the role[%d], check ", role)
		}

	}
	// 查询数据库是否有关联的快照库
	getSnapshots := fmt.Sprintf(
		"select name from master.sys.databases where source_database_id = DB_ID('%s')",
		dbName,
	)
	if err := c.DB.Queryx(&dbSnapshots, getSnapshots); err != nil {
		return fmt.Errorf("get-db-snapshots failed %v", err)
	}

	// 如果有存在快照，则先删除快照库
	if len(dbSnapshots) != 0 {
		for _, snapshot := range dbSnapshots {
			execDBSQLs = append(execDBSQLs, fmt.Sprintf("DROP DATABASE [%s];", snapshot))
		}
	}
	// 拼接执行删除源库
	execDBSQLs = append(execDBSQLs, fmt.Sprintf("DROP DATABASE [%s]", dbName))

	// 执行drop 批命令
	if _, err := c.DB.ExecMore(execDBSQLs); err != nil {
		return fmt.Errorf(
			"exec drop database [%s] in DB [%s:%d] failed: [%v]",
			dbName,
			c.Params.Host,
			c.Params.Port,
			err,
		)
	}

	return nil
}

// execTablesForPer 非全匹配规则，按指定表清单执行清理（truncate / drop）
//
// truncate 模式下采用"FK 感知"策略：
//  1. 拉取数据库内全部 FK 关系
//  2. 对每条 FK 检查 parent / referenced 是否都在本次清理列表中：
//     - 越界（外部表引用了将被清空的表）-> 直接报错，整批不执行
//     - 否则把"涉及 FK"的表归为 fkTables，其余归为 noFKTables
//  3. noFKTables 走 TRUNCATE TABLE，速度快
//  4. fkTables  走 DELETE 方案 + WITH CHECK CHECK + checkFKTrusted 校验
func (c *CleanDBSComp) execTablesForPer(execMode string, dbName string) error {
	realTables, err := c.DB.GetTableListOnDB(
		dbName,
		c.Params.CleanTables,
		c.Params.IgnoreCleanTables,
	)
	if err != nil {
		return fmt.Errorf("get tables list on db [%s] failed:[%v]", dbName, err)
	}
	if len(realTables) == 0 {
		// 获取的表列表为空，正常跳过
		logger.Info(
			"table-list is empty on db [%s], skip. CleanTables:[%v];IgnoreCleanTables[%v]",
			dbName,
			c.Params.CleanTables,
			c.Params.IgnoreCleanTables,
		)
		return nil
	}

	switch execMode {
	case "truncate":
		return c.cleanTablesByList(dbName, realTables)
	case "drop":
		return c.dropTablesByList(dbName, realTables)
	default:
		return fmt.Errorf("execMode [%s] not suppurt", execMode)
	}
}

// tableKey 用于把 schema/table 拼成 map key
func tableKey(schema, name string) string { return schema + "." + name }

// fullTableName 用于打印日志的可读形式
func fullTableName(schema, name string) string { return fmt.Sprintf("[%s].[%s]", schema, name) }

// fkAnalysis FK 越界分析结果
//   - involved: 与本次清理列表存在 FK 关联的目标表集合（key = schema.table）
//   - innerFKs: 闭环在清理列表内的 FK 关系（parent/referenced 都在列表内）
//   - crossFKs: 越界 FK 的可读描述（外部表引用了清理列表内的表）
//   - fks:      原始 FK 关系列表（便于复用）
type fkAnalysis struct {
	involved map[string]struct{}
	innerFKs []sqlserver.FKRelation
	crossFKs []string
	fks      []sqlserver.FKRelation
}

// analyzeFKCrossList 对"待清理/待 drop 的表清单"做 FK 关系分析（truncate/drop 共用）
//
// 判定规则：
//   - parent ∈ target 且 ref ∈ target  -> 闭环 FK，参与 involved/innerFKs
//   - parent ∈ target 且 ref ∉ target  -> 引用方在清理列表，被引用方不动，安全（仅标 involved）
//   - parent ∉ target 且 ref ∈ target  -> 越界冲突，记入 crossFKs（必须报错）
//   - 两端都不在 target                 -> 与本次清理无关，忽略
func (c *CleanDBSComp) analyzeFKCrossList(
	dbName string, tables []sqlserver.TableSchema,
) (*fkAnalysis, error) {
	target := make(map[string]struct{}, len(tables))
	for _, t := range tables {
		target[tableKey(t.SchemaName, t.TableName)] = struct{}{}
	}
	fks, err := c.DB.GetFKRelationsOnDB(dbName)
	if err != nil {
		return nil, err
	}
	res := &fkAnalysis{
		involved: make(map[string]struct{}),
		fks:      fks,
	}
	for _, fk := range fks {
		pk := tableKey(fk.ParentSchema, fk.ParentTable)
		rk := tableKey(fk.RefSchema, fk.RefTable)
		_, pIn := target[pk]
		_, rIn := target[rk]
		switch {
		case pIn && rIn:
			res.involved[pk] = struct{}{}
			res.involved[rk] = struct{}{}
			res.innerFKs = append(res.innerFKs, fk)
		case pIn && !rIn:
			res.involved[pk] = struct{}{}
		case !pIn && rIn:
			res.crossFKs = append(res.crossFKs, fmt.Sprintf(
				"%s -(FK %s)-> %s  (parent 不在清理列表)",
				fullTableName(fk.ParentSchema, fk.ParentTable),
				fk.FKName,
				fullTableName(fk.RefSchema, fk.RefTable),
			))
		}
	}
	return res, nil
}

// cleanTablesByList "FK 感知"按表清空
// 入参 tables 是经过 GetTableListOnDB 过滤后真正需要清理的表清单
func (c *CleanDBSComp) cleanTablesByList(dbName string, tables []sqlserver.TableSchema) error {
	// FK 越界分析
	ana, err := c.analyzeFKCrossList(dbName, tables)
	if err != nil {
		return err
	}

	if len(ana.crossFKs) > 0 {
		// 把待清理表也打印出来，方便用户对照排查
		var targetList []string
		for _, t := range tables {
			targetList = append(targetList, fullTableName(t.SchemaName, t.TableName))
		}
		logger.Error(
			"clean-tables on db [%s] aborted due to cross-list FK references.\n"+
				"  clean-tables:    %v\n"+
				"  cross-fk-issues: %v\n"+
				"  please add the parent tables into clean_tables, "+
				"or remove the referenced tables from clean_tables.",
			dbName, targetList, ana.crossFKs,
		)
		return fmt.Errorf(
			"clean-tables on db [%s] aborted: %d cross-list FK reference(s) detected: %v",
			dbName, len(ana.crossFKs), ana.crossFKs,
		)
	}

	// 拆分两组：noFKTables 直接 TRUNCATE，fkTables 走 DELETE 方案
	var noFKTables, fkTables []sqlserver.TableSchema
	for _, t := range tables {
		if _, ok := ana.involved[tableKey(t.SchemaName, t.TableName)]; ok {
			fkTables = append(fkTables, t)
		} else {
			noFKTables = append(noFKTables, t)
		}
	}
	logger.Info(
		"clean-plan on db [%s]: total=%d, noFK(TRUNCATE)=%d, withFK(DELETE)=%d",
		dbName, len(tables), len(noFKTables), len(fkTables),
	)

	// 1) 无 FK 牵涉 -> TRUNCATE
	if len(noFKTables) > 0 {
		var noFKNames []string
		var execSQLs []string
		for _, t := range noFKTables {
			noFKNames = append(noFKNames, fullTableName(t.SchemaName, t.TableName))
			execSQLs = append(execSQLs, fmt.Sprintf(
				cst.TRUNCATE_TABLES_SQL_FOR_PER,
				dbName,
				t.SchemaName, t.TableName,
				t.SchemaName, t.TableName,
				t.SchemaName, t.TableName,
				t.SchemaName, t.TableName,
				t.SchemaName, t.TableName,
			))
		}
		logger.Info("truncate no-fk tables on db [%s]: %v", dbName, noFKNames)
		if _, err := c.DB.ExecMore(execSQLs); err != nil {
			return fmt.Errorf(
				"truncate no-fk tables on db [%s] failed: [%v]; tables: %v",
				dbName, err, noFKNames,
			)
		}
		logger.Info("truncate no-fk tables on db [%s] succeed, count=%d", dbName, len(noFKNames))
	}

	// 2) 涉及 FK -> DELETE 方案 + FK 信任校验（带重试机制）
	if len(fkTables) > 0 {
		var fkNames []string
		for _, t := range fkTables {
			fkNames = append(fkNames, fullTableName(t.SchemaName, t.TableName))
		}
		logger.Info("delete fk-involved tables on db [%s]: %v", dbName, fkNames)

		maxRetries := 3
		retryDelayMs := 500 // 重试间隔 500ms

		for attempt := 1; attempt <= maxRetries; attempt++ {
			insertRows := buildInsertRowsForCleanList(fkTables)
			execSQL := fmt.Sprintf(cst.DELETE_TABLES_FOR_FK_BY_LIST, dbName, insertRows)
			if _, err := c.DB.Exec(execSQL); err != nil {
				return fmt.Errorf(
					"delete fk-involved tables on db [%s] failed: [%v]; tables: %v",
					dbName, err, fkNames,
				)
			}

			// DELETE 方案执行后必须校验所有 FK 都已重新被信任（is_not_trusted = 0）
			if err := c.checkFKTrusted(dbName); err == nil {
				logger.Info("delete fk-involved tables on db [%s] succeed, count=%d", dbName, len(fkNames))
				break
			}

			if attempt == maxRetries {
				// 最后一次重试仍然失败
				logger.Warn("FK trust check failed after %d attempts, attempting manual fix", maxRetries)
				if err := c.manualFixFKTrusted(dbName); err != nil {
					return fmt.Errorf(
						"delete fk-involved tables on db [%s] failed after manual fix: [%v]; tables: %v",
						dbName, err, fkNames,
					)
				}
				logger.Info("manual FK trust fix on db [%s] succeed", dbName)
			} else {
				logger.Warn("FK trust check failed on attempt %d/%d, retrying after %dms",
					attempt, maxRetries, retryDelayMs)
				// 简单延时重试
				time.Sleep(time.Duration(retryDelayMs) * time.Millisecond)
				retryDelayMs *= 2 // 指数退避
			}
		}
	}

	// 最终验证：检查清理结果是否完全成功（只检查实际清理的表）
	if err := c.checkCleanResultByList(dbName, tables); err != nil {
		return fmt.Errorf("clean-result validation failed on db [%s]: %v", dbName, err)
	}

	logger.Info("clean-tables on db [%s] all done", dbName)
	return nil
}

// dropTablesByList "FK 感知"按表清单 DROP TABLE
//
// 流程：
//  1. FK 越界检查：外部表引用了清理列表内的表 -> 直接报错
//  2. schema-bound 预检：带 SCHEMABINDING 的视图/UDF 引用了清理列表内的表 -> 直接报错
//  3. 拓扑排序：被引用方排在最后 DROP，避免 SQL Server 3726 错误
//  4. 循环依赖处理：先显式 ALTER TABLE ... DROP CONSTRAINT，把环切断
//  5. 事务包裹批量执行：任一条失败整体回滚，避免半截状态
func (c *CleanDBSComp) dropTablesByList(dbName string, tables []sqlserver.TableSchema) error {
	// ---------- 1) FK 越界检查（与 truncate 路径共用同一套规则） ----------
	ana, err := c.analyzeFKCrossList(dbName, tables)
	if err != nil {
		return err
	}
	if len(ana.crossFKs) > 0 {
		var targetList []string
		for _, t := range tables {
			targetList = append(targetList, fullTableName(t.SchemaName, t.TableName))
		}
		logger.Error(
			"drop-tables on db [%s] aborted due to cross-list FK references.\n"+
				"  drop-tables:     %v\n"+
				"  cross-fk-issues: %v\n"+
				"  please add the parent tables into clean_tables, "+
				"or remove the referenced tables from clean_tables.",
			dbName, targetList, ana.crossFKs,
		)
		return fmt.Errorf(
			"drop-tables on db [%s] aborted: %d cross-list FK reference(s) detected: %v",
			dbName, len(ana.crossFKs), ana.crossFKs,
		)
	}

	// ---------- 2) schema-bound 引用预检 ----------
	sbRefs, err := c.DB.GetSchemaBoundRefsOnDB(dbName)
	if err != nil {
		return err
	}
	targetSet := make(map[string]struct{}, len(tables))
	for _, t := range tables {
		targetSet[tableKey(t.SchemaName, t.TableName)] = struct{}{}
	}
	var blockedBySB []string
	for _, ref := range sbRefs {
		// referenced 形如 [schema].[table]，提取后比对
		schema, name := parseQuotedSchemaTable(ref.Referenced)
		if _, hit := targetSet[tableKey(schema, name)]; hit {
			blockedBySB = append(blockedBySB, fmt.Sprintf(
				"%s -(SCHEMABINDING)-> %s", ref.Referencing, ref.Referenced,
			))
		}
	}
	if len(blockedBySB) > 0 {
		logger.Error(
			"drop-tables on db [%s] aborted due to schema-bound references.\n"+
				"  blocked-by: %v\n"+
				"  please drop these schema-bound objects (or remove SCHEMABINDING) first.",
			dbName, blockedBySB,
		)
		return fmt.Errorf(
			"drop-tables on db [%s] aborted: %d schema-bound reference(s) block DROP: %v",
			dbName, len(blockedBySB), blockedBySB,
		)
	}

	// ---------- 3) 拓扑排序：被引用方在最后 ----------
	orderedTables, cycleFKs := topoSortDropOrder(tables, ana.innerFKs)
	logger.Info(
		"drop-plan on db [%s]: total=%d, inner-FK=%d, cycle-FK=%d",
		dbName, len(tables), len(ana.innerFKs), len(cycleFKs),
	)

	// ---------- 4) 拼接 SQL：先 DROP 循环依赖中的 FK 约束，再按拓扑序 DROP 表 ----------
	var stmts []string
	if len(cycleFKs) > 0 {
		var cycleDesc []string
		for _, fk := range cycleFKs {
			cycleDesc = append(cycleDesc, fmt.Sprintf(
				"%s -(FK %s)-> %s",
				fullTableName(fk.ParentSchema, fk.ParentTable),
				fk.FKName,
				fullTableName(fk.RefSchema, fk.RefTable),
			))
			stmts = append(stmts, fmt.Sprintf(
				"ALTER TABLE [%s].[%s] DROP CONSTRAINT [%s];",
				fk.ParentSchema, fk.ParentTable, fk.FKName,
			))
		}
		logger.Info("cycle-FKs to drop first on db [%s]: %v", dbName, cycleDesc)
	}

	var dropNames []string
	for _, t := range orderedTables {
		dropNames = append(dropNames, fullTableName(t.SchemaName, t.TableName))
		stmts = append(stmts, fmt.Sprintf(
			"DROP TABLE [%s].[%s];", t.SchemaName, t.TableName,
		))
	}
	logger.Info("drop tables on db [%s] in order: %v", dbName, dropNames)

	// ---------- 5) 事务包裹批量执行 ----------
	execSQL := fmt.Sprintf(cst.DROP_TABLES_BY_LIST_SQL, dbName, strings.Join(stmts, "\n    "))
	if _, err := c.DB.Exec(execSQL); err != nil {
		return fmt.Errorf(
			"drop tables on db [%s] failed: [%v]; tables: %v",
			dbName, err, dropNames,
		)
	}
	logger.Info("drop tables on db [%s] succeed, count=%d", dbName, len(dropNames))
	return nil
}

// topoSortDropOrder 对待 drop 表做拓扑排序，使"被引用方"排在最后
//
// 规则：以 referenced -> parent 为依赖方向（被引用方必须比引用方更晚 drop）
// 算法：Kahn BFS。indegree[v] = 指向 v 的 FK 数；
//   - indegree=0 的节点是"没有被列表内任何表引用"的，可以先 drop
//   - 每次出队一个 v，对所有 v 引用的表 u，把 indegree[u]-- ；
//     当 indegree[u] 归零时入队
//
// 若 BFS 结束后仍有节点未出队，说明存在循环依赖，返回 cycleFKs
// 由调用方先 ALTER TABLE ... DROP CONSTRAINT 把环切断，再 DROP 剩余表
func topoSortDropOrder(
	tables []sqlserver.TableSchema, innerFKs []sqlserver.FKRelation,
) (ordered []sqlserver.TableSchema, cycleFKs []sqlserver.FKRelation) {
	// node key -> TableSchema
	nodeMap := make(map[string]sqlserver.TableSchema, len(tables))
	for _, t := range tables {
		nodeMap[tableKey(t.SchemaName, t.TableName)] = t
	}

	// 邻接表 + 入度。 indegree[v] 表示有多少个清理列表内的表引用 v
	indegree := make(map[string]int, len(tables))
	// adj[v] = v 引用的所有目标（v 的 parent FK 指向 referenced 集合）
	adj := make(map[string][]string, len(tables))
	for k := range nodeMap {
		indegree[k] = 0
		adj[k] = nil
	}
	for _, fk := range innerFKs {
		pk := tableKey(fk.ParentSchema, fk.ParentTable)
		rk := tableKey(fk.RefSchema, fk.RefTable)
		if pk == rk {
			// 自引用：DROP TABLE 自身能处理（删除前 SQL Server 不再校验自引用）
			continue
		}
		adj[pk] = append(adj[pk], rk)
		indegree[rk]++
	}

	// Kahn BFS：先 drop 没被任何人引用的（indegree=0）
	queue := make([]string, 0, len(tables))
	for k, d := range indegree {
		if d == 0 {
			queue = append(queue, k)
		}
	}
	visited := make(map[string]struct{}, len(tables))
	for len(queue) > 0 {
		v := queue[0]
		queue = queue[1:]
		if _, ok := visited[v]; ok {
			continue
		}
		visited[v] = struct{}{}
		ordered = append(ordered, nodeMap[v])
		for _, u := range adj[v] {
			indegree[u]--
			if indegree[u] == 0 {
				queue = append(queue, u)
			}
		}
	}

	// 仍未访问到的节点存在循环依赖
	if len(visited) < len(nodeMap) {
		// 收集环内的 FK（两端都还没被 visited 的）
		for _, fk := range innerFKs {
			pk := tableKey(fk.ParentSchema, fk.ParentTable)
			rk := tableKey(fk.RefSchema, fk.RefTable)
			if pk == rk {
				continue
			}
			_, pV := visited[pk]
			_, rV := visited[rk]
			if !pV && !rV {
				cycleFKs = append(cycleFKs, fk)
			}
		}
		// 把剩下的节点也追加到 ordered 末尾，由调用方先切断 cycleFKs 再统一 DROP
		for k, t := range nodeMap {
			if _, ok := visited[k]; !ok {
				ordered = append(ordered, t)
			}
		}
	}
	return ordered, cycleFKs
}

// parseQuotedSchemaTable 从 "[schema].[table]" 中解析出 schema/table
// 容错：未匹配方括号时，按 '.' 简单切分并去掉两端引号/方括号
func parseQuotedSchemaTable(s string) (schema, name string) {
	trim := func(x string) string {
		x = strings.TrimSpace(x)
		x = strings.TrimPrefix(x, "[")
		x = strings.TrimSuffix(x, "]")
		return x
	}
	// 优先按 "].[" 分割（标准 QUOTENAME 输出）
	if i := strings.Index(s, "].["); i >= 0 {
		return trim(s[:i+1]), trim(s[i+2:])
	}
	if i := strings.Index(s, "."); i >= 0 {
		return trim(s[:i]), trim(s[i+1:])
	}
	return "", trim(s)
}

// parseQuotedSchemaTableFK 从形如 "[schema].[table].[fk_name]" 的字符串中
// 解析出 schema/table/fk 三段。
//
// 输入由 SQL Server 端 QUOTENAME(s.name)+'.'+QUOTENAME(t.name)+'.'+QUOTENAME(fk.name)
// 拼出，保证：
//   - 每段都被一对最外层的 '[' ']' 包裹；
//   - 段内若包含 ']'，会被 QUOTENAME 转义成 ']]';
//   - 段间分隔符固定为 "].["（前一段的收尾 ']' + '.' + 后一段的开头 '['）。
//
// 因此用两次 strings.Index 定位 "].[" 即可稳定切成 3 段，
// 不能用 strings.Trim(s, "[]")（按字符集去除）或 strings.Split(s, "].[")
// （内部含 "].[" 时会切多）。
//
// 解析成功返回 schema/table/fk 与 true，否则返回空字符串与 false。
func parseQuotedSchemaTableFK(s string) (schema, table, fk string, ok bool) {
	s = strings.TrimSpace(s)
	i := strings.Index(s, "].[")
	if i < 0 {
		return "", "", "", false
	}
	j := strings.Index(s[i+2:], "].[")
	if j < 0 {
		return "", "", "", false
	}
	j += i + 2

	rawSchema := s[:i+1]     // 包含闭合的 ']'
	rawTable := s[i+2 : j+1] // 包含闭合的 ']'
	rawFK := s[j+2:]         // 末段

	unquote := func(x string) (string, bool) {
		if len(x) < 2 || x[0] != '[' || x[len(x)-1] != ']' {
			return "", false
		}
		// 去掉最外层的一对 '[' ']'，再把 QUOTENAME 转义的 "]]" 还原为 "]"
		return strings.ReplaceAll(x[1:len(x)-1], "]]", "]"), true
	}

	var ok1, ok2, ok3 bool
	if schema, ok1 = unquote(rawSchema); !ok1 {
		return "", "", "", false
	}
	if table, ok2 = unquote(rawTable); !ok2 {
		return "", "", "", false
	}
	if fk, ok3 = unquote(rawFK); !ok3 {
		return "", "", "", false
	}
	if schema == "" || table == "" || fk == "" {
		return "", "", "", false
	}
	return schema, table, fk, true
}

// buildInsertRowsForCleanList 把待清理表清单拼成多条 INSERT INTO #T(...) SELECT ... 语句
// 用于 DELETE_TABLES_FOR_FK_BY_LIST 模板的第二个 %s 占位符
//
// 安全说明：schema/table 名属于用户可控输入，SQL Server 允许标识符中出现单引号等特殊字符，
// 直接拼接到 N'...' 字符串字面量会导致 SQL 执行报错甚至注入，需按 T-SQL 规范转义（' -> ”）。
func buildInsertRowsForCleanList(tables []sqlserver.TableSchema) string {
	var sb strings.Builder
	for _, t := range tables {
		schemaName := strings.ReplaceAll(t.SchemaName, "'", "''")
		tableName := strings.ReplaceAll(t.TableName, "'", "''")
		sb.WriteString(fmt.Sprintf(
			"INSERT INTO #T(object_id, FullName, HasIdentity) "+
				"SELECT t.object_id, "+
				"QUOTENAME(s.name) + '.' + QUOTENAME(t.name), "+
				"CASE WHEN EXISTS ("+
				"SELECT 1 FROM sys.identity_columns ic WHERE ic.object_id = t.object_id"+
				") THEN 1 ELSE 0 END "+
				"FROM sys.tables t JOIN sys.schemas s ON s.schema_id = t.schema_id "+
				"WHERE s.name = N'%s' AND t.name = N'%s';\n",
			schemaName, tableName,
		))
	}
	return sb.String()
}
