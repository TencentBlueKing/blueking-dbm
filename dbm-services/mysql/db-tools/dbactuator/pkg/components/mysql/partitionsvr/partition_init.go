/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package partitionsvr

import (
	"fmt"
	"os/exec"

	"strings"
	"time"

	"dbm-services/common/go-pubpkg/errno"

	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

const PT_MAX_LOAD_THREADS_RUNNING = 80
const PT_CRITICAL_LOAD_THREADS_RUNNING = 100
const PT_LOCK_WAIT_TIMEOUT = 10

func (pc *PartitionConfig) ExecuteInitStatement(pd *PartitionDetail, conn *native.DbWorker, forceInitInfo *ForceInitInfo) (partitionStepInfo *PartitionStepInfo) {

	partitionStepInfo = &PartitionStepInfo{
		Step:      "init",
		Status:    false,
		Message:   "",
		Statement: "",
	}

	if forceInitInfo != nil {
		// 只有强制执行，才会用到pt工具，因此首先检查是否存在唯一键
		// 强制执行不用检查表大小
		err := pd.CheckUniqueKey(conn)
		if err != nil {
			partitionStepInfo.Message = err.Error()
			return partitionStepInfo
		}

	} else {
		// 非强制执行，检查表大小，不满足条件则不在日常任务中执行，报错回去，由执行者判断是否强制执行
		err := pd.CheckTableSize(conn)
		if err != nil {
			partitionStepInfo.Message = err.Error()
			return partitionStepInfo
		}
	}

	initStatement, err := pc.GetInitStatement(pd, conn)
	if err != nil {
		partitionStepInfo.Message = err.Error()
		return partitionStepInfo
	}

	// 三种情况:
	// 1. 强制执行且有唯一键
	// 2. 强制执行且没有唯一键
	// 3. 其他（非强制）
	if forceInitInfo != nil {
		// 强制执行
		if pd.HasUniqueKey {
			pc.ExecuteInitStatementByPTTool(initStatement, forceInitInfo, partitionStepInfo)
		} else {
			// 没有唯一键强制执行，不设置超时时间
			pc.ExecuteInitStatementByDDL(initStatement, conn, partitionStepInfo)
		}
	} else {
		// 非强制执行，直接执行分区DDL
		pc.ExecuteInitStatementByDDL(initStatement, conn, partitionStepInfo)
	}
	return partitionStepInfo
}

func (pc *PartitionConfig) ExecuteInitStatementByPTTool(initStatement string, forceInitInfo *ForceInitInfo, partitionStepInfo *PartitionStepInfo) {
	// 有唯一键，使用pt工具
	pt_tool := "percona-toolkit-3.5.0/bin/pt-online-schema-change"
	user := forceInitInfo.User
	pwd := forceInitInfo.Pwd
	host := forceInitInfo.Host
	port := forceInitInfo.Port
	command := fmt.Sprintf("%s/%s h=%s,P=%d,u=%s,p=%s,%s",
		cst.DBAToolkitPath, pt_tool, host, port, user, pwd, initStatement)
	partitionStepInfo.Statement = command

	output, err := exec.Command("/bin/bash", "-c", command).CombinedOutput()
	if err != nil {
		partitionStepInfo.Message = fmt.Sprintf("执行失败: %s, stderr: %s", err.Error(), string(output))
		return
	}
	// 成功执行的结果信息暂时不返回 用success表示
	// partitionStepInfo.Message = string(output)
	partitionStepInfo.Status = true
	partitionStepInfo.Message = "success"
}

func (pc *PartitionConfig) ExecuteInitStatementByDDL(initStatement string, conn *native.DbWorker, partitionStepInfo *PartitionStepInfo) {
	// 记录执行的SQL语句
	partitionStepInfo.Statement = initStatement
	// ddl的初始化只设置锁等待超时时间
	_, err := conn.ExecMore([]string{fmt.Sprintf("set session lock_wait_timeout=%d", LockWaitTimeout), initStatement})
	if err != nil {
		partitionStepInfo.Message = err.Error()
	} else {
		partitionStepInfo.Status = true
		partitionStepInfo.Message = "success"
	}
}

func (pc *PartitionConfig) GetInitStatement(pd *PartitionDetail, conn *native.DbWorker) (string, error) {
	var sqlPartitionDesc []string
	var pkey, descKey, descFormat, initSql string
	var diff int

	switch pc.PartitionType {
	case 0:
		pkey = fmt.Sprintf("RANGE (TO_DAYS(%s))", pc.PartitionColumn)
		descKey = "less than"
		descFormat = "to_days('2006-01-02')"
		diff = DiffOneDay
	case 1:
		pkey = fmt.Sprintf("LIST (TO_DAYS(%s))", pc.PartitionColumn)
		descKey = "in"
		descFormat = "to_days('2006-01-02')"
		diff = 0
	case 3:
		pkey = fmt.Sprintf("LIST (%s)", pc.PartitionColumn)
		descKey = "in"
		descFormat = "20060102"
		diff = 0
	case 4:
		pkey = fmt.Sprintf("RANGE COLUMNS(%s)", pc.PartitionColumn)
		descKey = "less than"
		descFormat = "'2006-01-02'"
		diff = DiffOneDay
	case 5:
		pkey = fmt.Sprintf("RANGE (UNIX_TIMESTAMP(%s))", pc.PartitionColumn)
		descKey = "less than"
		descFormat = "UNIX_TIMESTAMP('2006-01-02')"
		diff = DiffOneDay
	case 6:
		pkey = fmt.Sprintf("RANGE (%s)", pc.PartitionColumn)
		descKey = "less than"
		descFormat = "UNIX_TIMESTAMP('2006-01-02')"
		diff = DiffOneDay
	case 101:
		pkey = fmt.Sprintf("RANGE (%s)", pc.PartitionColumn)
		descKey = "less than"
		descFormat = "20060102"
		diff = 0
	default:
		return initSql, errno.NotSupportedPartitionType
	}
	// 兼容历史遗留的PARTITION p20230325 VALUES LESS THAN (20230325)的格式，虽然是less than但是分区名和desc是同一天
	if pc.PartitionType == 101 {
		for i := -pc.ReservedPartition + 1; i < pc.ExtraPartition+1; i++ {
			pname := time.Now().AddDate(0, 0, i*pc.PartitionTimeInterval).Format("p20060102")
			pdesc := time.Now().AddDate(0, 0, i*pc.PartitionTimeInterval+diff).Format(descFormat)
			palter := fmt.Sprintf(" partition %s values %s (%s)", pname, descKey, pdesc)
			sqlPartitionDesc = append(sqlPartitionDesc, palter)
		}
	} else {
		for i := -pc.ReservedPartition; i < pc.ExtraPartition; i++ {
			pname := time.Now().AddDate(0, 0, i*pc.PartitionTimeInterval).Format("p20060102")
			pdesc := time.Now().AddDate(0, 0, i*pc.PartitionTimeInterval+diff).Format(descFormat)
			palter := fmt.Sprintf(" partition %s values %s (%s)", pname, descKey, pdesc)
			sqlPartitionDesc = append(sqlPartitionDesc, palter)
		}
	}

	if pd.HasUniqueKey {
		options := fmt.Sprintf(
			// --charset=utf8                             设置字符集为utf8
			// --recursion-method=NONE                   递归方法设为NONE，避免对分区表递归处理
			// --alter-foreign-keys-method=auto          外键约束处理方式自动
			// --max-load Threads_running=%d             设置最大"Threads_running"负载阈值
			// --critical-load=Threads_running=%d        设置关键"Threads_running"负载阈值，超过则中止
			// --set-vars lock_wait_timeout=%d           设置会话级lock_wait_timeout超时时间
			// --print                                   打印pt-online-schema-change的操作SQL
			// --pause-file=/tmp/partition_osc_pause_%s_%s  如果该文件存在则暂停操作(用于维护调停)
			// --execute                                 实际执行更改
			"--charset=utf8 --recursion-method=NONE --alter-foreign-keys-method=auto --max-load Threads_running=%d "+
				"--critical-load=Threads_running=%d --set-vars lock_wait_timeout=%d --print --pause-file=/tmp/partition_osc_pause_%s_%s --execute ",
			PT_MAX_LOAD_THREADS_RUNNING,
			PT_CRITICAL_LOAD_THREADS_RUNNING, PT_LOCK_WAIT_TIMEOUT, pd.DbName, pd.TbName)
		initSql = fmt.Sprintf(`D=%s,t=%s --alter "partition by %s (%s)" %s`, pd.DbName, pd.TbName, pkey,
			strings.Join(sqlPartitionDesc, ","), options)
	} else {
		initSql = fmt.Sprintf("alter table `%s`.`%s` partition by %s (%s)", pd.DbName, pd.TbName, pkey,
			strings.Join(sqlPartitionDesc, ","))
	}
	return initSql, nil
}
