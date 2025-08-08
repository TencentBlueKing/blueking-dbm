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
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"fmt"
	"math"
	"strings"
	"sync"
	"time"
)

// TendbPartition 用于在Tendb集群上执行分区操作
// 遍历所有分区配置，获取实际库表信息并执行分区任务，错误统一记录
func (c *PartitionExecComp) TendbPartition() (err error) {

	// 并发执行所有分区配置，最大并发数为10，使用带缓冲的channel控制
	concurrency := 10
	sem := make(chan struct{}, concurrency)
	errCh := make(chan error, len(c.Params.Configs))
	var wg sync.WaitGroup

	// 强制执行是任务级别的，对此次所有分区配置通用，使用同一个ForceInitInfo
	var forceInitInfo *ForceInitInfo
	if c.Params.Force {
		forceInitInfo = &ForceInitInfo{
			Force: c.Params.Force,
			User:  c.GeneralParam.RuntimeAccountParam.PartitionYwUser,
			Pwd:   c.GeneralParam.RuntimeAccountParam.PartitionYwPwd,
			Host:  c.Params.Cluster.IP,
			Port:  c.Params.Cluster.Port,
		}
	}

	// 一个分区配置为维度，执行分区操作
	for _, conf := range c.Params.Configs {
		sem <- struct{}{} // 占用一个并发槽
		wg.Add(1)
		go func(conf *PartitionConfig) {
			defer func() {
				<-sem // 释放并发槽
				wg.Done()
			}()
			tdbhaPC := TdbhaPartConf{
				PartitionConfig: *conf,
				PartitionExecSummary: &TdbhaExecSummary{
					ConfigID:       conf.ConfigID,
					Status:         true, // 默认分区配置执行成功
					TableExecInfos: []*PartitionTableExecInfo{},
				},
			}
			// 获取真实库表名 是否分区
			partitionDetails, err := GetOneDbTbRealInfo(c.Conn, conf.DbLike, conf.TbLike)

			// 以分区配置为维度，上报执行结果
			partitionResult := &PartitionResultReportEvent{
				Cluster:    cst.TendbHA,
				BkBizId:    c.Params.Cluster.BkBizId,
				BkCloudId:  c.Params.Cluster.BkCloudID,
				ConfigId:   tdbhaPC.ConfigID,
				CreateTime: time.Now().Format(time.RFC3339),
			}

			// 库表名获取报错，则不继续执行
			if err != nil {
				tdbhaPC.PartitionExecSummary.Status = false
				tdbhaPC.PartitionExecSummary.TableCheckError = err
				// 整合错误信息并加上分区配置ID
				errMsg := fmt.Errorf("ConfigID: %d. TableCheckError: %v", conf.ConfigID, err)
				// 以分区配置为维度，上报执行结果
				partitionResult.Status = "failed"
				partitionResult.ExecLog = errMsg.Error()
				reportErr := ReportPartitionResult(partitionResult)
				if reportErr != nil {
					errCh <- fmt.Errorf("report partition result failed: %v, original error: %v", reportErr, err)
					return
				}
				errCh <- errMsg
				return
			}

			tdbhaPC.ExecuteOneConfPartition(c.Conn, partitionDetails, forceInitInfo)
			tableExecMsgs := tdbhaPC.CollectTdbHaPartitionResults()
			// 这里先整理信息，后面的逻辑在判断状态
			// fmt.Println("tableExecMsgs", tableExecMsgs)
			if !tdbhaPC.PartitionExecSummary.Status {
				// 有执行失败的表，记录错误并上报
				errMsg := fmt.Errorf("ConfigID: %d, Errors: %v", conf.ConfigID, tableExecMsgs)
				partitionResult.Status = "failed"
				partitionResult.ExecLog = strings.Join(tableExecMsgs, "\n")
				reportErr := ReportPartitionResult(partitionResult)
				if reportErr != nil {
					errCh <- fmt.Errorf("report partition result failed: %v, original error: %v", reportErr, err)
				} else {
					errCh <- errMsg
				}
			} else {
				// 都执行成功，状态正常，正常上报
				partitionResult.Status = "success"
				partitionResult.ExecLog = strings.Join(tableExecMsgs, "\n")
				// fmt.Println("report partition result", partitionResult)
				reportErr := ReportPartitionResult(partitionResult)
				if reportErr != nil {
					errCh <- reportErr
				}
			}
		}(conf)
	}

	wg.Wait()
	close(errCh)
	for err := range errCh {
		c.Params.ErrorLogs = append(c.Params.ErrorLogs, err)
	}

	if len(c.Params.ErrorLogs) > 0 {
		// 整合所有错误信息为一个字符串返回
		var allErrMsgs []string
		for _, err := range c.Params.ErrorLogs {
			allErrMsgs = append(allErrMsgs, err.Error())
		}
		return fmt.Errorf("error occurred during partition execution: %v", allErrMsgs)
	}

	return nil
}

// 整合所有表的执行结果
func (pc *TdbhaPartConf) CollectTdbHaPartitionResults() []string {
	var tableExecMsgs []string
	for _, tableExecInfo := range pc.PartitionExecSummary.TableExecInfos {
		baseMsg := fmt.Sprintf("DB:%s, Table:%s, Status:%v", tableExecInfo.DbName, tableExecInfo.TbName, tableExecInfo.Status)
		for _, stepInfo := range tableExecInfo.StepInfos {
			stepMsg := fmt.Sprintf("[Step:%s, Status:%v, Message:%s, Statement:%s]", stepInfo.Step, stepInfo.Status, stepInfo.Message, stepInfo.Statement)
			baseMsg += stepMsg
		}
		tableExecMsgs = append(tableExecMsgs, baseMsg)
	}
	return tableExecMsgs
}

// ExecuteOneConfPartition 一个分区配置为维度，执行分区操作
// pc: TdbhaPartConf 分区配置
// pd: []*PartitionDetail 一个分区配置下模糊匹配的真实库表信息
// ptError: *PartitionTableExecInfo 库表分区执行结果
func (pc *TdbhaPartConf) ExecuteOneConfPartition(conn *native.DbWorker, partitionDetails []*PartitionDetail, forceInitInfo *ForceInitInfo) {

	// 计算保留的分区数量
	pc.ReservedPartition = int(math.Ceil(float64(pc.ExpireTime) / float64(pc.PartitionTimeInterval)))

	for _, pd := range partitionDetails {
		ptExecInfo := pc.ExecuteOneTbPartition(pd, conn, forceInitInfo)
		if !ptExecInfo.Status {
			pc.PartitionExecSummary.Status = false
			pc.PartitionExecSummary.TableExecInfos = append(pc.PartitionExecSummary.TableExecInfos, ptExecInfo)
		} else {
			pc.PartitionExecSummary.TableExecInfos = append(pc.PartitionExecSummary.TableExecInfos, ptExecInfo)
		}
	}

}

// ExecuteOneTbPartition 具体的一个表为维度
func (pc *TdbhaPartConf) ExecuteOneTbPartition(pd *PartitionDetail, conn *native.DbWorker, forceInitInfo *ForceInitInfo) (ptExecInfo *PartitionTableExecInfo) {

	defer func() {
		_, _ = conn.Exec(fmt.Sprintf("FLUSH TABLES `%s`.`%s`", pd.DbName, pd.TbName))
	}()

	ptExecInfo = &PartitionTableExecInfo{
		DbName:    pd.DbName,
		TbName:    pd.TbName,
		Status:    true,
		StepInfos: []*PartitionStepInfo{},
	}
	// 非强制执行，且表已经是分区表，则不执行初始化分区，只执行添加和删除分区
	if pd.IsPartitioned && forceInitInfo == nil {
		// 目标表已是分区表
		// 先执行添加分区
		partitionAddStepInfo := pc.ExecuteAddStatement(pd, conn)
		if partitionAddStepInfo.Status {
			ptExecInfo.StepInfos = append(ptExecInfo.StepInfos, partitionAddStepInfo)
		} else {
			ptExecInfo.Status = false
			ptExecInfo.StepInfos = append(ptExecInfo.StepInfos, partitionAddStepInfo)
		}

		// 再执行删除分区
		partitionDropStepInfo := pc.ExecuteDropStatement(pd, conn)
		if partitionDropStepInfo.Status {
			ptExecInfo.StepInfos = append(ptExecInfo.StepInfos, partitionDropStepInfo)
		} else {
			ptExecInfo.Status = false
			ptExecInfo.StepInfos = append(ptExecInfo.StepInfos, partitionDropStepInfo)
		}
	} else {
		// 执行初始化分区
		// 强制执行，或 表不是分区表，则执行初始化分区
		partitionInitStepInfo := pc.ExecuteInitStatement(pd, conn, forceInitInfo)
		if partitionInitStepInfo.Status {
			ptExecInfo.StepInfos = append(ptExecInfo.StepInfos, partitionInitStepInfo)
		} else {
			ptExecInfo.Status = false
			ptExecInfo.StepInfos = append(ptExecInfo.StepInfos, partitionInitStepInfo)
		}
	}
	return ptExecInfo
}
