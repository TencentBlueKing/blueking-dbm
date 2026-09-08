/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// 通过工具pt-table-sync 工具对主从数据做数据修复
// 修复前会做一系列的前置检查行为，尽量保证数据能修复正常
// 原子任务需要兼容两个触发场景：手动检验而发起修复场景、例行检验而发起修复场景。两种场景因为处理逻辑稍微不同，需要部分区别对待

package mysql

import (
	"bytes"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"math/big"
	"regexp"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// dsnPassRe 匹配 pt-table-sync DSN 中的密码段.
// pt-table-sync DSN 形如: h=1.1.1.1,P=3306,u=user,p=secret --execute
// 密码前必然是 DSN 内分隔符 ',' 或 DSN 段起始处的空白, 密码值以下一个 ',' 或空白结束.
// 通过锚定边界字符, 精确定位 DSN 中的密码字段, 避免:
//  1. 密码明文作为子串意外出现在其它位置(如库表名)被误替换;
//  2. 密码含 DSN 分隔符时无法完整匹配到真实边界.
var dsnPassRe = regexp.MustCompile(`([,\s]p=)[^,\s]+`)

const checkSumDB = native.INFODBA_SCHEMA
const checkSumTable = "checksum"
const checkSumHistoryTable = "checksum_history"
const slaveBehindMasterLimit = 1800 // slave不能落后master 半小时以上
const chunkSize = "10000"           // pt-table-sync每次修复的chunk单位,检验时候会用到
const maxInconsistentChunk = 50     // 单表不一致 chunk 数阈值,超过则不进行修复,建议走重建 slave 流程

// Charset TODO
const Charset = "binary" // 目前统一使用binary字符集

// 修复结果状态枚举
const (
	repairStatusSuccess = "success" // 修复成功
	repairStatusFailed  = "failed"  // 修复失败
	repairStatusSkipped = "skipped" // 跳过修复(表不满足修复条件)
	repairStatusNoDiff  = "no_diff" // 未发现不一致
)

// PtTableSyncComp TODO
type PtTableSyncComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *PtTableSyncParam        `json:"extend"`
	PtTableSyncCtx
	tools *tools.ToolSet
}

// PtTableSyncParam TODO
// 增加例行校验发起修复所需要的参数：start_time、end_time、is_routine_trigger
type PtTableSyncParam struct {
	Host                string `json:"host" validate:"required,ip"`
	Port                int    `json:"port" validate:"required,lt=65536,gte=3306"`
	MasterHost          string `json:"master_host" validate:"required,ip"`
	MasterPort          int    `json:"master_port" validate:"required,lt=65536,gte=3306"`
	IsSyncNonInnodbTbls bool   `json:"is_sync_non_innodb"`
	SyncUser            string `json:"sync_user" validate:"required"`
	SyncPass            string `json:"sync_pass" validate:"required"`
	CheckSumTable       string `json:"check_sum_table" validate:"required"`
	// StartTime/EndTime 会被拼接进 checksum 表 SQL 的 ts BETWEEN '...' AND '...' 条件,
	// 通过严格白名单格式校验(允许为空; 非空必须匹配 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS),
	// 可彻底规避潜在的 SQL 拼接注入风险
	StartTime        string `json:"start_time" validate:"omitempty,datetime=2006-01-02|datetime=2006-01-02 15:04:05"`
	EndTime          string `json:"end_time" validate:"omitempty,datetime=2006-01-02|datetime=2006-01-02 15:04:05"`
	IsRoutineTrigger bool   `json:"is_routine_trigger"`
	// Synctables        []string `json:"sync_tables"`
	// SyncDbs           []string `json:"SyncDbs"`
}

// PtTableSyncCtx 定义任务执行时需要的上下文
type PtTableSyncCtx struct {
	tableSyncMap          []TableSyncInfo
	dbConn                *native.DbWorker
	masterDbConn          *native.DbWorker
	tempCheckSumTableName string
	repairResults         []TableRepairResult // 每张表的修复结果,循环结束后统一输出 JSON 报告
}

// TableSyncInfo 定义待修复表的信息结构体
type TableSyncInfo struct {
	DbName    string `db:"DbName"`
	TableName string `db:"TableName"`
}

// TableRepairResult 定义单张表的修复结果, 用于最终 JSON 报告输出
type TableRepairResult struct {
	DbName             string `json:"db_name"`
	TableName          string `json:"table_name"`
	Status             string `json:"status"`              // success/failed/skipped/no_diff
	Reason             string `json:"reason"`              // 中文原因说明
	InconsistentChunks int    `json:"inconsistent_chunks"` // checksum 表中该表不一致 chunk 数
	ExitCode           int    `json:"exit_code"`           // pt-table-sync 退出码,仅实际执行时填充
}

// TableInfo TODO
type TableInfo struct {
	DbName    string `db:"TABLE_SCHEMA"`
	TableName string `db:"TABLE_NAME"`
	Engine    string `db:"ENGINE"`
	Collation string `db:"TABLE_COLLATION"`
}

// Example TODO
func (c *PtTableSyncComp) Example() interface{} {
	comp := PtTableSyncComp{
		Params: &PtTableSyncParam{
			Host:                "1.1.1.1",
			Port:                10000,
			MasterHost:          "1.1.1.2",
			MasterPort:          10000,
			IsSyncNonInnodbTbls: false,
			CheckSumTable:       "checksum",
			SyncUser:            "xxx",
			SyncPass:            "xxx",
		},
	}
	return comp
}

// Init 定义act的初始化内容
func (c *PtTableSyncComp) Init() (err error) {

	// 参数硬校验: 把可能进入 SQL 的时间字符串锁死为严格白名单,
	// 从入参源头一次性覆盖所有下游拼接点 (getTableSyncMap / countInconsistentChunks / CopyTableCheckSumReport)
	if err = c.validateTimeParams(); err != nil {
		return err
	}

	// 连接本地实例的db（其实是从实例）
	c.dbConn, err = native.InsObject{
		Host: c.Params.Host,
		Port: c.Params.Port,
		User: c.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  c.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("连接本地实例 %s:%d 失败: %s", c.Params.Host, c.Params.Port, err.Error())
		return err
	}
	// 远程连接传入过来的master实例，用临时账号
	c.masterDbConn, err = native.InsObject{
		Host: c.Params.MasterHost,
		Port: c.Params.MasterPort,
		User: c.Params.SyncUser,
		Pwd:  c.Params.SyncPass,
	}.Conn()
	if err != nil {
		logger.Error("连接主库实例 %s:%d 失败: %s", c.Params.MasterHost, c.Params.MasterPort, err.Error())
		return err
	}

	// 获取checksum 表中数据校验异常的表信息
	err = c.getTableSyncMap()
	if err != nil {
		return err
	}
	// 拼接临时表的名称
	randomNum, _ := rand.Int(rand.Reader, big.NewInt(100000))
	c.PtTableSyncCtx.tempCheckSumTableName = fmt.Sprintf("checksum_%s_%d", c.Params.SyncUser, randomNum)

	return nil
}

// validateTimeParams 校验 StartTime / EndTime 的合法性
//
// 业务约定:
//  1. 手动触发场景 (is_routine_trigger=false): 允许 start_time / end_time 为空;
//  2. 例行触发场景 (is_routine_trigger=true):  两个字段均必填;
//  3. 非空时必须严格匹配 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS 两种格式之一.
//
// 安全用途: 这两个字段会被拼接进 checksum 表 SQL 的 ts BETWEEN '...' AND '...' 条件,
// 严格白名单校验后即可彻底规避潜在的 SQL 拼接注入面.
// 该函数与 struct tag 上的 validate 规则等价, 作为兜底第二道防线,
// 避免调用方绕过 validator 直接构造 struct 时校验缺失.
func (c *PtTableSyncComp) validateTimeParams() error {
	const dateLayout = "2006-01-02"
	const dateTimeLayout = "2006-01-02 15:04:05"

	check := func(field, val string) error {
		if val == "" {
			return nil
		}
		if _, err := time.ParseInLocation(dateLayout, val, time.Local); err == nil {
			return nil
		}
		if _, err := time.ParseInLocation(dateTimeLayout, val, time.Local); err == nil {
			return nil
		}
		return fmt.Errorf(
			"%s 格式非法, 期望 %q 或 %q, 实际 %q",
			field, dateLayout, dateTimeLayout, val,
		)
	}
	if err := check("start_time", c.Params.StartTime); err != nil {
		return err
	}
	if err := check("end_time", c.Params.EndTime); err != nil {
		return err
	}
	// 例行触发场景下, 两个时间必须成对出现
	if c.Params.IsRoutineTrigger &&
		(c.Params.StartTime == "" || c.Params.EndTime == "") {
		return fmt.Errorf(
			"is_routine_trigger=true 时, start_time 和 end_time 均不能为空",
		)
	}
	return nil
}

// Precheck 定义act的前置检测行为
// 检测记录异常的表,现在是否存在；
// 现在的节点的同步是否还是现在的主库，同步是否正常
func (c *PtTableSyncComp) Precheck() (err error) {

	// 判断传入过来的checksum表是否存在
	if !c.isExistCheckSumTable() {
		return fmt.Errorf("checksum 表 [%s.%s] 可能不存在", checkSumDB, c.Params.CheckSumTable)
	}

	slaveStatus, err := c.dbConn.ShowSlaveStatus()
	if err != nil {
		return err
	}
	// 同步是否正常
	if !slaveStatus.ReplSyncIsOk() {
		return fmt.Errorf(
			"主从同步异常, IOThread=%s, SQLThread=%s",
			slaveStatus.SlaveIORunning, slaveStatus.SlaveSQLRunning,
		)
	}
	// 目前节点的master是否是参数传入的master
	if slaveStatus.MasterHost != c.Params.MasterHost || slaveStatus.MasterPort != c.Params.MasterPort {
		return fmt.Errorf(
			"当前节点实际同步的主库为 [%s:%d], 与参数指定的主库 [%s:%d] 不一致",
			slaveStatus.MasterHost, slaveStatus.MasterPort, c.Params.MasterHost, c.Params.MasterPort,
		)
	}
	// 如果该节点如果了落后时间时间大于1800s ，则程序先异常退出，可等待主从复制同步后再重试任务
	if slaveStatus.SecondsBehindMaster.Int64 >= slaveBehindMasterLimit {
		return fmt.Errorf(
			"从库 [%s:%d] 落后主库 [%s:%d] 超过 %ds, 先退出, 待主从追平后重试",
			c.Params.Host, c.Params.Port, c.Params.MasterHost, c.Params.MasterPort, slaveBehindMasterLimit,
		)
	}
	// 判断最终待修复的表信息列表是否为空,后续引入忽略表的参数，最终可能会为空
	if len(c.tableSyncMap) == 0 {
		return fmt.Errorf("待修复的表列表为空")
	}
	// 加载pt-table-sync 工具路径
	c.tools, err = tools.NewToolSetWithPick(tools.ToolPtTableSync)
	if err != nil {
		logger.Error("初始化 pt-table-sync 工具集失败: %s", err.Error())
		return err
	}

	return nil
}

// ExecPtTableSync 定义下发pt-table-sync工具去执行数据修复的过程
// 目前的按照表的维度来下发修复，每修复进程完，记录对应的表已修复完成，打印到日志上
// 如果其中某张表修复出现异常，db-act进程不中断，对下一张表进行修复。失败的表打印到日志上
// 修复表之前看看表是否满足修复条件，如果不满足，则跳过对这个表的修复
func (c *PtTableSyncComp) ExecPtTableSync() (err error) {
	// 数据修复的checksum表名(常规=Params.CheckSumTable, 例行=临时表)
	var getChecksumName string

	// 获取工具文件路径
	PtTableSyncPath, err := c.tools.Get(tools.ToolPtTableSync)
	if err != nil {
		logger.Error("获取 %s 工具路径失败: %s", tools.ToolPtTableSync, err.Error())
		return err
	}

	for _, syncTable := range c.tableSyncMap {
		db, tbl := syncTable.DbName, syncTable.TableName

		// 1) 主库校验表是否符合修复规格(存在、事务引擎)
		isExist, tableCharSet := c.checkTable(db, tbl)
		if !isExist {
			logger.Warn("表 [%s.%s] 不符合修复规格,跳过修复", db, tbl)
			c.appendRepairResult(db, tbl, repairStatusSkipped, "表不存在或非事务引擎,跳过修复", 0, 0)
			continue
		}

		// 2) 主库探测表是否存在唯一索引(PRIMARY 或 UNIQUE)
		hasUniq, uErr := c.hasUniqueIndex(db, tbl)
		if uErr != nil {
			logger.Error("探测表 [%s.%s] 唯一索引失败: %s", db, tbl, uErr.Error())
			c.appendRepairResult(
				db, tbl, repairStatusFailed,
				fmt.Sprintf("探测唯一索引出错: %s", uErr.Error()), 0, 0,
			)
			continue
		}
		if !hasUniq {
			logger.Warn("表 [%s.%s] 没有唯一索引,不支持修复,跳过修复", db, tbl)
			c.appendRepairResult(
				db, tbl, repairStatusSkipped,
				"该表没有唯一索引,pt-table-sync 无法进行行级修复,跳过修复", 0, 0,
			)
			continue
		}

		// 3) 确定实际使用的 checksum 表名
		if c.Params.IsRoutineTrigger {
			// 例行检查发起的数据修复,用临时表作为修复依据
			getChecksumName = c.PtTableSyncCtx.tempCheckSumTableName
			if !c.CopyTableCheckSumReport(db, tbl, getChecksumName) {
				logger.Error("复制表 [%s.%s] 的 checksum 记录到临时表失败", db, tbl)
				c.appendRepairResult(
					db, tbl, repairStatusFailed,
					"复制 checksum 记录到临时表失败", 0, 0,
				)
				continue
			}
		} else {
			// 常规校验使用传入的 checksum 表
			getChecksumName = c.Params.CheckSumTable
		}

		// 4) 统计不一致 chunk 数,超过阈值则拦截
		chunks, cErr := c.countInconsistentChunks(db, tbl, getChecksumName)
		if cErr != nil {
			logger.Error("统计表 [%s.%s] 不一致 chunk 数失败: %s", db, tbl, cErr.Error())
			c.appendRepairResult(
				db, tbl, repairStatusFailed,
				fmt.Sprintf("统计不一致 chunk 数出错: %s", cErr.Error()), 0, 0,
			)
			continue
		}
		if chunks > maxInconsistentChunk {
			logger.Warn(
				"表 [%s.%s] 不一致 chunk 数=%d, 超过阈值(%d), 跳过修复", db, tbl, chunks, maxInconsistentChunk,
			)
			c.appendRepairResult(
				db, tbl, repairStatusFailed,
				fmt.Sprintf("不一致 chunk 数超过阈值(%d),修复时间过长, 会影响业务长时间抖动,建议走重建 slave 流程", maxInconsistentChunk),
				chunks, 0,
			)
			continue
		}

		// 5) 拼接 pt-table-sync 命令
		// 固定算法为 Nibble:
		//   - 不指定时工具默认 Chunk 优先：字符列（如 varchar 存数字串/中文，
		//     在差异范围内同首字符时，
		//     Chunk 算法 prepare 阶段 die "Cannot chunk table ... same character"，
		//     且 --algorithms 列表不会自动降级到下一算法，导致整表修复失败；
		//   - Nibble 按索引序逐段推进、不依赖字符空间切分，天然适配同首字符列，
		//     其中文边界双重编码问题已随 pt-table-sync 3.3.2-dbm-0.0.1 修复并实测通过；
		//   - 本修复模式（--replicate --sync-to-master）要求表有唯一索引（行级
		//     修复需唯一键定位行），有唯一索引则 Nibble 必可用，无需兜底算法。
		syncCmd := fmt.Sprintf(
			"%s --replicate=%s.%s --sync-to-master --no-buffer-to-client --no-check-child-tables "+
				"--algorithms=Nibble --chunk-size=%s --databases=%s --tables=%s --charset=%s h=%s,P=%d,u=%s,p=%s --execute",
			PtTableSyncPath, checkSumDB, getChecksumName, chunkSize, db,
			tbl, tableCharSet, c.Params.Host, c.Params.Port, c.Params.SyncUser, c.Params.SyncPass,
		)

		logger.Info("开始修复表 [%s.%s], 执行命令: %s", db, tbl, maskPasswordInCmd(syncCmd, c.Params.SyncPass))
		output, exitCode, execErr := osutil.StandardShellCommandForExitCode(false, syncCmd)

		// 6) 精细化处理 exitCode
		switch exitCode {
		case 0:
			// exitCode=0 表示 pt-table-sync 未发现实际不一致的行,
			// 可能是 pt-table-sync 的已知 bug,也可能是差异已被人工修复。
			// 但 checksum 表中差异记录仍然残留,DBHA 会依据这些记录判断主从数据一致性,
			// 若不清理将持续影响主从切换判断,因此这里也需要清理 checksum 差异记录。
			logger.Warn(
				"表 [%s.%s] pt-table-sync 未发现不一致记录,建议重新执行数据校验单据再次确认。输出: %s",
				db, tbl, output,
			)
			if uerr := c.UpdateOldRecords(db, tbl); uerr != nil {
				logger.Error(
					"表 [%s.%s] 未发现不一致但清理 checksum 差异记录失败: %s",
					db, tbl, uerr.Error(),
				)
				c.appendRepairResult(
					db, tbl, repairStatusFailed,
					fmt.Sprintf("未发现不一致但清理 checksum 差异记录失败(会影响 DBHA 切换判断): %s", uerr.Error()),
					chunks, 0,
				)
				continue
			}
			logger.Info(
				"表 [%s.%s] 未发现实际不一致,已清理 checksum 差异记录,避免影响 DBHA 切换判断", db, tbl,
			)
			c.appendRepairResult(
				db, tbl, repairStatusNoDiff,
				"pt-table-sync 未发现不一致记录(可能为工具 bug 或已人工修复),已清理 checksum 差异记录,建议重新执行数据校验单据再次确认",
				chunks, 0,
			)
		case 2:
			// exitCode=2 表示已修复差异,更新历史记录
			logger.Info("表 [%s.%s] pt-table-sync 修复完成, 输出: %s", db, tbl, output)
			if uerr := c.UpdateOldRecords(db, tbl); uerr != nil {
				logger.Error("表 [%s.%s] 更新 checksum 历史记录失败: %s", db, tbl, uerr.Error())
				c.appendRepairResult(
					db, tbl, repairStatusFailed,
					fmt.Sprintf("修复完成但更新历史记录失败: %s", uerr.Error()),
					chunks, 2,
				)
				continue
			}
			logger.Info("表 [%s.%s] 修复成功", db, tbl)
			c.appendRepairResult(db, tbl, repairStatusSuccess, "修复成功", chunks, 2)
		default:
			// 其他退出码统一视为失败,不中断,继续处理下一张表
			errMsg := ""
			if execErr != nil {
				errMsg = execErr.Error()
			}
			logger.Error(
				"表 [%s.%s] pt-table-sync 执行失败, exitCode=%d, output=%s, err=%s",
				db, tbl, exitCode, output, errMsg,
			)
			c.appendRepairResult(
				db, tbl, repairStatusFailed,
				fmt.Sprintf("pt-table-sync 执行失败, exitCode=%d, output=%s", exitCode, output),
				chunks, exitCode,
			)
		}
	}

	// 存在失败表则返回错误(保持"单表失败不中断"语义,修复报告由上层 defer 输出)
	for _, r := range c.repairResults {
		if r.Status == repairStatusFailed {
			return fmt.Errorf("存在修复失败的表,详见修复报告")
		}
	}
	return nil
}

// getTableSyncMap 查询本地实例的checksum检测结果异常的表信息
func (c *PtTableSyncComp) getTableSyncMap() (err error) {
	var checkSQL string
	if c.Params.IsRoutineTrigger {
		// 例行检测校验触发的数据修复场景
		checkSQL = fmt.Sprintf(
			`select db as DbName ,tbl as TableName from %s.%s where (this_crc <> master_crc or this_cnt <> master_cnt) 
			 and (ts between '%s' and '%s')  group by db, tbl`,
			checkSumDB, c.Params.CheckSumTable, c.Params.StartTime, c.Params.EndTime,
		)
	} else {
		// 常规校验而触发数据修复
		checkSQL = fmt.Sprintf(
			"select db as DbName ,tbl as TableName from %s.%s where this_crc <> master_crc or this_cnt <> master_cnt group by db, tbl",
			checkSumDB, c.Params.CheckSumTable,
		)
	}

	// 这里查询返回空的话，先不在这里报错退出
	err = c.dbConn.Queryx(&c.tableSyncMap, checkSQL)
	if err != nil && !c.dbConn.IsNotRowFound(err) {
		logger.Error("查询 checksum 异常表信息失败: %s", err.Error())
		return err
	}

	return nil

}

// isExistCheckSumTable 判断本地实例是否存在checksum表
func (c *PtTableSyncComp) isExistCheckSumTable() bool {
	checkSumSql := fmt.Sprintf(
		"select 1 from information_schema.tables where TABLE_SCHEMA = '%s' and TABLE_NAME = '%s' ;",
		checkSumDB, c.Params.CheckSumTable,
	)
	_, err := c.dbConn.Query(checkSumSql)
	if err != nil {
		logger.Error("查询 checksum 表是否存在失败: %s", err.Error())
		return false
	}
	return true
}

// checkTable 在master实例检验表是否符合修复规格: 检测表是否在主库存在；表的引擎是否事务引擎
func (c *PtTableSyncComp) checkTable(dbName string, tableName string) (bool, string) {

	var tableInfo []TableInfo

	checkSumSql := fmt.Sprintf(
		"select TABLE_SCHEMA, TABLE_NAME, ENGINE, TABLE_COLLATION from information_schema.tables where TABLE_SCHEMA = '%s' and TABLE_NAME = '%s' ;",
		dbName, tableName,
	)
	err := c.masterDbConn.Queryx(&tableInfo, checkSumSql)
	if err != nil {
		logger.Error("查询表 [%s.%s] 元信息失败: %s", dbName, tableName, err.Error())
		return false, ""
	}
	// 检测是否是非事务引擎表，目前事务引擎只有 innodb和tokudb
	if !c.Params.IsSyncNonInnodbTbls && !(tableInfo[0].Engine == "InnoDB" || tableInfo[0].Engine == "TokuDB") {
		logger.Error("表 [%s.%s] 非事务引擎表, 不支持修复", dbName, tableName)
		return false, ""
	}
	return true, getFirstSubstring(tableInfo[0].Collation)
}

// DropSyncUser 修复后删除主从节点的临时数据修复账号
func (c *PtTableSyncComp) DropSyncUser() (err error) {

	logger.Info("开始删除临时数据修复账号 ....")
	userHost := fmt.Sprintf("%s@%s", c.Params.SyncUser, c.Params.Host)

	// 在主节点删除
	if _, err := c.masterDbConn.Exec(fmt.Sprintf("drop user %s;", userHost)); err != nil {
		logger.Error(
			"在主库 [%s:%d] 删除账号 %s 失败: %s", c.Params.MasterHost, c.Params.MasterPort, userHost, err.Error(),
		)
		return err
	}
	// 在本地节点删除
	if _, err := c.dbConn.Exec(fmt.Sprintf("drop user %s;", userHost)); err != nil {
		logger.Error(
			"在本地实例 [%s:%d] 删除账号 %s 失败: %s", c.Params.Host, c.Params.Port, userHost, err.Error(),
		)
		return err
	}
	logger.Info("临时数据修复账号删除完成")
	return nil
}

// CopyTableCheckSumReport 处理将需要修复表的异常检验结果复制到临时表
// 这个针对巡检例行校验而触发的数据修复场景
// 原因是实例的checksum-report是历史表，包括存在很多历史记录，影响到pt-table-sync工具修复进度
func (c *PtTableSyncComp) CopyTableCheckSumReport(DBName string, tableName string, tempCheckSumTableName string) bool {
	// 定义复制数据SQL列表
	var copySQLs []string

	// 校验必要参数的逻辑
	if !(c.Params.IsRoutineTrigger && len(c.Params.StartTime) != 0 && len(c.Params.EndTime) != 0) {
		logger.Error(
			"必要参数不合法: is_routine_trigger 为 true 时, start_time 和 end_time 不能为空",
		)
		return false
	}

	// 导入异常记录在临时表上
	copySQLs = append(copySQLs, "set sql_log_bin = OFF;")
	copySQLs = append(
		copySQLs, fmt.Sprintf(
			"create table if not exists %s.%s like %s.%s ;",
			checkSumDB, tempCheckSumTableName, checkSumDB, c.Params.CheckSumTable,
		),
	)
	copySQLs = append(copySQLs, fmt.Sprintf("truncate table %s.%s ;", checkSumDB, tempCheckSumTableName))
	copySQLs = append(
		copySQLs,
		fmt.Sprintf(
			"insert into %s.%s select * from %s.%s  where db = '%s' and tbl = '%s' and ts between '%s' and '%s' ;",
			checkSumDB,
			tempCheckSumTableName,
			checkSumDB,
			c.Params.CheckSumTable,
			DBName,
			tableName,
			c.Params.StartTime,
			c.Params.EndTime,
		),
	)
	copySQLs = append(copySQLs, "set sql_log_bin = ON;")

	//  在主库执行
	if _, err := c.masterDbConn.ExecMore(copySQLs); err != nil {
		logger.Error("在主库创建临时表 %s 失败: %s", tempCheckSumTableName, err.Error())
		return false
	}
	logger.Info("在主库创建临时表 %s 成功", tempCheckSumTableName)
	// 在从库执行
	if _, err := c.dbConn.ExecMore(copySQLs); err != nil {
		logger.Error("在本地实例创建临时表 %s 失败: %s", tempCheckSumTableName, err.Error())
		return false
	}
	logger.Info("在本地实例创建临时表 %s 成功", tempCheckSumTableName)

	return true
}

// DropTempTable 删除临时表
func (c *PtTableSyncComp) DropTempTable() (err error) {

	if !c.Params.IsRoutineTrigger {
		// 判断临时表没有创建过，则主动跳过
		logger.Info("未使用临时 checksum 表, 跳过删除")
		return nil
	}

	logger.Info("开始删除临时表: %s ....", c.PtTableSyncCtx.tempCheckSumTableName)
	if _, err := c.masterDbConn.Exec(
		fmt.Sprintf(
			"drop table if exists %s.%s;",
			checkSumDB,
			c.PtTableSyncCtx.tempCheckSumTableName,
		),
	); err != nil {
		logger.Error("删除临时表失败: %s", err.Error())
		return err
	}
	logger.Info("临时表删除完成")
	return nil
}

// UpdateOldRecords 删除对应修复不一致表的记录，在本地执行，不打开binlog
func (c *PtTableSyncComp) UpdateOldRecords(dbName string, tableName string) (err error) {
	sqls := []string{
		"set session sql_log_bin = 0 ;",
	}
	if c.Params.IsRoutineTrigger {
		sqls = append(
			sqls, []string{
				fmt.Sprintf(
					`update %s.%s set this_crc=master_crc, this_cnt=master_cnt where db='%s' and tbl='%s';`,
					checkSumDB, checkSumTable, dbName, tableName,
				),
				fmt.Sprintf(
					`update %s.%s set this_crc=master_crc, this_cnt=master_cnt where db='%s' and tbl='%s';`,
					checkSumDB, checkSumHistoryTable, dbName, tableName,
				),
			}...,
		)
	} else {
		sqls = append(
			sqls, fmt.Sprintf(
				`update %s.%s set this_crc=master_crc, this_cnt=master_cnt where db='%s' and tbl='%s';`,
				checkSumDB, c.Params.CheckSumTable, dbName, tableName,
			),
		)
	}

	sqls = append(sqls, "set session sql_log_bin = 1 ;")

	if _, err := c.dbConn.ExecMore(sqls); err != nil {
		return fmt.Errorf("更新表 [%s.%s] 的 checksum 历史记录失败: %s", dbName, tableName, err.Error())
	}
	logger.Info("表 [%s.%s] 的 checksum 历史记录更新完成", dbName, tableName)
	return nil
}

// appendRepairResult 追加一条表级修复结果到上下文的结果集
func (c *PtTableSyncComp) appendRepairResult(db, tbl, status, reason string, chunks, exitCode int) {
	c.repairResults = append(c.repairResults, TableRepairResult{
		DbName:             db,
		TableName:          tbl,
		Status:             status,
		Reason:             reason,
		InconsistentChunks: chunks,
		ExitCode:           exitCode,
	})
}

// PrintRepairReport 汇总修复结果并返回格式化 JSON 字符串,由上层通过 OutputCtx 包装输出
func (c *PtTableSyncComp) PrintRepairReport() (string, error) {
	// 分类计数
	var successCnt, failedCnt, skippedCnt, noDiffCnt int
	for _, r := range c.repairResults {
		switch r.Status {
		case repairStatusSuccess:
			successCnt++
		case repairStatusFailed:
			failedCnt++
		case repairStatusSkipped:
			skippedCnt++
		case repairStatusNoDiff:
			noDiffCnt++
		}
	}

	logger.Info(
		"数据修复结果汇总: 成功=%d, 失败=%d, 跳过=%d, 无差异=%d, 总计=%d",
		successCnt, failedCnt, skippedCnt, noDiffCnt, len(c.repairResults),
	)

	// 序列化为格式化 JSON, 供上层 OutputCtx 包装输出
	// 使用 Encoder 并关闭 HTML 转义, 避免中文被转成 \uXXXX 形式, 保证可读性
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	enc.SetIndent("", "  ")
	if err := enc.Encode(c.repairResults); err != nil {
		logger.Error("修复结果 JSON 序列化失败: %s", err.Error())
		return "", err
	}
	// Encoder.Encode 会在末尾追加换行符, 去除以便 OutputCtx 输出紧凑
	report := strings.TrimRight(buf.String(), "\n")
	// 打印本地日志便于对比: 若日志里为原文中文, 而 <ctx> 展示端仍是 \uXXXX, 则是上游二次编码
	logger.Info("数据修复结果报告(JSON,原文):\n%s", report)
	return report, nil
}

// hasUniqueIndex 在主库探测表是否存在 PRIMARY 或 UNIQUE 索引(通过 Non_unique=0 判定)
// 注意: DbWorker.Query 在查询结果为空行时,会返回一个字面值为 "not row found" 的 error,
// 这不是真正的执行错误,而是"没有匹配到行"的业务语义,对于本函数就应当解释为"没有唯一索引",
// 因此需要显式兼容,避免误报为"探测失败"。
func (c *PtTableSyncComp) hasUniqueIndex(dbName, tableName string) (bool, error) {
	sqlStr := fmt.Sprintf("SHOW INDEX FROM `%s`.`%s` WHERE Non_unique = 0", dbName, tableName)
	rows, err := c.masterDbConn.Query(sqlStr)
	if err != nil {
		// 空结果集在 DbWorker 里被包装成 error, 这里等价于"无唯一索引"
		if strings.Contains(err.Error(), native.NotRowFound) {
			return false, nil
		}
		return false, err
	}
	return len(rows) > 0, nil
}

// countInconsistentChunks 统计指定 checksum 表中某张表不一致 chunk 记录数
// 常规场景查 Params.CheckSumTable, 例行场景查临时表且按 ts BETWEEN StartTime AND EndTime 过滤
func (c *PtTableSyncComp) countInconsistentChunks(dbName, tableName, checkSumName string) (int, error) {
	var countSQL string
	if c.Params.IsRoutineTrigger {
		countSQL = fmt.Sprintf(
			`select count(*) as cnt from %s.%s where db = '%s' and tbl = '%s' `+
				`and (this_crc <> master_crc or this_cnt <> master_cnt) `+
				`and (ts between '%s' and '%s')`,
			checkSumDB, checkSumName, dbName, tableName, c.Params.StartTime, c.Params.EndTime,
		)
	} else {
		countSQL = fmt.Sprintf(
			`select count(*) as cnt from %s.%s where db = '%s' and tbl = '%s' `+
				`and (this_crc <> master_crc or this_cnt <> master_cnt)`,
			checkSumDB, checkSumName, dbName, tableName,
		)
	}

	var result []struct {
		Cnt int `db:"cnt"`
	}
	if err := c.dbConn.Queryx(&result, countSQL); err != nil {
		return 0, err
	}
	if len(result) == 0 {
		return 0, nil
	}
	return result[0].Cnt, nil
}

func getFirstSubstring(s string) string {
	if idx := strings.Index(s, "_"); idx != -1 {
		return s[:idx] // 找到第一个 _ 前的内容
	}
	return s // 未找到则返回原字符串
}

// maskPasswordInCmd 对命令行中的 pt-table-sync DSN 密码进行脱敏,避免明文密码泄露到日志。
// pt-table-sync DSN 中密码通过 p=xxx 传递,通常形如: h=1.1.1.1,P=3306,u=user,p=secret --execute
// 使用正则锚定 DSN 内边界字符(前置 ',' 或空白, 后置 ',' 或空白/行尾),
// 将 p= 后的实际密码值统一替换为占位符 ***.
// 相较于 strings.ReplaceAll(cmd, "p="+pass, "p=***") 的字面替换:
//  1. 不会因为密码字面值恰好作为子串出现在其它位置(如库表名)而被误替换;
//  2. 密码含 DSN 分隔符时仍能精确匹配到真实边界;
//  3. 不再依赖 pass 明文入参, 传空也不影响功能.
func maskPasswordInCmd(cmd, _ string) string {
	return dsnPassRe.ReplaceAllString(cmd, "${1}***")
}
