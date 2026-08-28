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
	"strconv"
	"sync"
	"time"
)

// TendbClusterPartition 用于spider集群分区执行
func (c *PartitionExecComp) TendbClusterPartition() (err error) {

	// 获取分片信息
	err = c.Params.Cluster.GetShardInfo(c.Conn)
	if err != nil {
		return fmt.Errorf("error occurred while getting shard info: %s", err.Error())
	}

	// 强制执行是任务级别的开关，DSN 在各分片上再组装
	// 非强制执行，则为nil
	var forceInitInfo *ForceInitInfo
	if c.Params.Force {
		forceInitInfo = &ForceInitInfo{
			Force: c.Params.Force,
		}
	}
	// 使用带缓冲的channel实现并发控制，最大并发数为3
	// TODO: 需要根据实际情况调整并发数 如果单机分片比较少 可以根据机器数据量调整并发数
	concurrency := 3
	sem := make(chan struct{}, concurrency)
	errCh := make(chan error, len(c.Params.Configs))
	wg := sync.WaitGroup{}
	for _, conf := range c.Params.Configs {
		// 传参给每一个分区配置
		conf.IntervalCheck = c.Params.IntervalCheck

		sem <- struct{}{} // 占用一个并发槽
		wg.Add(1)
		go func(conf *PartitionConfig) {
			defer func() {
				<-sem
				wg.Done()
			}() // 释放并发槽

			tdbCluPartConf := TdbCluPartConf{
				PartitionConfig: *conf,
				PartitionExecSummary: &TdbCluExecSummary{
					ConfigID:     conf.ConfigID,
					Status:       true,
					ShardResults: []*PartitionShardResult{},
				},
			}
			err := c.ExecuteOneConfigOnShards(&tdbCluPartConf, forceInitInfo, c.Params.PartialForce)

			// 以分区配置为维度，上报执行结果
			partitionResult := &PartitionResultReportEvent{
				Cluster:    cst.TendbCluster,
				BkBizId:    c.Params.Cluster.BkBizId,
				BkCloudId:  c.Params.Cluster.BkCloudID,
				ConfigId:   tdbCluPartConf.ConfigID,
				CreateTime: time.Now().Format(time.RFC3339),
			}

			if err != nil {
				partitionResult.Status = "failed"
				partitionResult.ExecLog = err.Error()
				reportErr := ReportPartitionResult(partitionResult)
				if reportErr != nil {
					errCh <- fmt.Errorf("report partition result failed: %v, original error: %v", reportErr, err)
				} else {
					errCh <- err
				}
			} else {
				partitionResult.Status = "success"
				reportErr := ReportPartitionResult(partitionResult)
				if reportErr != nil {
					errCh <- reportErr
				}
			}
		}(conf)
	}

	wg.Wait()

	close(errCh)
	for e := range errCh {
		// 收集所有分区配置执行结果的错误信息
		c.Params.ErrorLogs = append(c.Params.ErrorLogs, e)
	}

	if len(c.Params.ErrorLogs) > 0 {
		return fmt.Errorf("error occurred during partition execution: %v", c.Params.ErrorLogs)
	}

	return nil
}

// 在所有分片上执行同一个分区配置
func (c *PartitionExecComp) ExecuteOneConfigOnShards(tdbCluPartConf *TdbCluPartConf, forceInitInfo *ForceInitInfo, partialForce bool) (err error) {

	const maxConcurrency = 3
	var wg sync.WaitGroup
	sem := make(chan struct{}, maxConcurrency)
	mu := sync.Mutex{}

	for _, shard := range c.Params.Cluster.ShardInfos {
		wg.Add(1)
		sem <- struct{}{}
		go func(shard *ShardInfo) {
			defer wg.Done()
			defer func() { <-sem }()

			partitionShardResult := &PartitionShardResult{
				ShardID:         shard.ShardID,
				ShardIP:         shard.IP,
				ShardPort:       shard.Port,
				ShardStatus:     true,
				ConnectionError: nil,
				TableExecInfos:  []*PartitionTableExecInfo{},
			}

			// 获取分片连接
			shardConn, err := shard.GetShardConn()
			if err != nil {
				// 任意分片失败，则该分区配置整体执行失败
				mu.Lock()
				tdbCluPartConf.PartitionExecSummary.Status = false
				// 具体分片的执行结果
				partitionShardResult.ShardStatus = false
				partitionShardResult.ConnectionError = err
				tdbCluPartConf.PartitionExecSummary.ShardResults = append(tdbCluPartConf.PartitionExecSummary.ShardResults, partitionShardResult)
				mu.Unlock()
				return
			}
			var shardForceInitInfo *ForceInitInfo
			if forceInitInfo != nil {
				shardForceInitInfo = &ForceInitInfo{
					Force: forceInitInfo.Force,
					User:  shard.Account,
					Pwd:   shard.PWD,
					Host:  shard.IP,
					Port:  shard.Port,
				}
			}
			tdbCluPartConf.ExecuteOneShardPartition(tdbCluPartConf, shard, shardConn, partitionShardResult, shardForceInitInfo, partialForce)

			if !partitionShardResult.ShardStatus {
				mu.Lock()
				tdbCluPartConf.PartitionExecSummary.Status = false
				tdbCluPartConf.PartitionExecSummary.ShardResults = append(tdbCluPartConf.PartitionExecSummary.ShardResults, partitionShardResult)
				mu.Unlock()
			}
		}(shard)
	}

	wg.Wait()

	if !tdbCluPartConf.PartitionExecSummary.Status {
		// 整合所有分片下的表错误信息
		// tendbcluster分片多，返回信息多，因此只针对错误返回，正确的不返回具体执行信息
		allTableErrors := collectTdbCluPartitionErrors(tdbCluPartConf)
		return fmt.Errorf("ConfigID: %d, Errors: %v", tdbCluPartConf.ConfigID, allTableErrors)
	}

	return nil

}

// ExecuteOneShardPartition 在指定分片上执行分区相关操作。
// 获取该分片上的真实库表信息后，逐一执行分区任务，返回分片执行结果
func (pc *TdbCluPartConf) ExecuteOneShardPartition(tdbCluPartConf *TdbCluPartConf, shard *ShardInfo, conn *native.DbWorker, partitionShardResult *PartitionShardResult, forceInitInfo *ForceInitInfo, partialForce bool) {
	// 会基于传入分片的 `ShardID` 改写配置中的 `DbLike`，获取该分片上的真实库表信息
	ShardDbLike := fmt.Sprintf("%s_%d", tdbCluPartConf.DbLike, shard.ShardID)
	partitionDetails, err := GetOneDbTbRealInfo(conn, ShardDbLike, tdbCluPartConf.TbLike)
	if err != nil {
		partitionShardResult.ShardStatus = false
		partitionShardResult.TableCheckError = err
		return
	}

	// 具体执行分区操作
	tdbCluPartConf.ExecuteOneConfPartition(conn, partitionDetails, partitionShardResult, forceInitInfo, partialForce)
}

// ExecuteOneConfPartition
// 维度：
// 一个分区配置
// 一个具体的库表
func (pc *TdbCluPartConf) ExecuteOneConfPartition(conn *native.DbWorker, partitionDetails []*PartitionDetail, partitionShardResult *PartitionShardResult, forceInitInfo *ForceInitInfo, partialForce bool) {

	// 计算保留的分区数量
	pc.ReservedPartition = int(math.Ceil(float64(pc.ExpireTime) / float64(pc.PartitionTimeInterval)))

	for _, pd := range partitionDetails {
		ptError := pc.ExecuteOneTbPartition(pd, conn, forceInitInfo, partialForce)
		if !ptError.Status {
			partitionShardResult.ShardStatus = false
			partitionShardResult.TableExecInfos = append(partitionShardResult.TableExecInfos, ptError)
		}
	}

}

// ExecuteOneTbPartition 具体的一个表为维度
func (pc *TdbCluPartConf) ExecuteOneTbPartition(pd *PartitionDetail, conn *native.DbWorker, forceInitInfo *ForceInitInfo, partialForce bool) (ptError *PartitionTableExecInfo) {

	defer func() {
		// _, _ = conn.Exec(fmt.Sprintf("set session lock_wait_timeout=%d; FLUSH TABLES `%s`.`%s`", LockWaitTimeout, pd.DbName, pd.TbName))
		flushSQL := fmt.Sprintf("FLUSH TABLES `%s`.`%s`", pd.DbName, pd.TbName)
		_, _ = conn.ExecWithTimeout(
			ExecTimeout,
			fmt.Sprintf("set session lock_wait_timeout=%d; %s", LockWaitTimeout, flushSQL))
	}()

	ptError = &PartitionTableExecInfo{
		DbName:    pd.DbName,
		TbName:    pd.TbName,
		Status:    true,
		StepInfos: []*PartitionStepInfo{},
	}
	// 非强制执行，且表已经是分区表，则不执行初始化分区，只执行添加和删除分区
	if pd.IsPartitioned && forceInitInfo == nil {
		// 目标表已是分区表
		psError := pc.ExecuteAddStatement(pd, conn)
		if !psError.Status {
			ptError.Status = false
			ptError.StepInfos = append(ptError.StepInfos, psError)
		}

		psError = pc.ExecuteDropStatement(pd, conn)
		if !psError.Status {
			ptError.Status = false
			ptError.StepInfos = append(ptError.StepInfos, psError)
			return ptError
		}
	} else {

		//  如果强制执行，且是部分强制执行，且表已经是分区表，则不执行初始化分区，只执行添加和删除分区
		// 针对部分分片未执行，只对这些分片初始化分区，其他分片不动
		if forceInitInfo != nil && partialForce && pd.IsPartitioned {
			return ptError
		}
		psError := pc.ExecuteInitStatement(pd, conn, forceInitInfo)
		if !psError.Status {
			ptError.Status = false
			ptError.StepInfos = append(ptError.StepInfos, psError)
		}
	}

	return ptError
}

func (c *Cluster) GetShardInfo(conn *native.DbWorker) (err error) {
	querySQL := `
		SELECT
			Host AS host,
			Port AS port,
			Username AS username,
			Password AS password,
			replace(server_name,'SPT','') AS shard_id 
		FROM
			mysql.servers
		WHERE
			Wrapper = ?
			AND Server_name LIKE ?;`
	rows, err := conn.QueryWithArgs(querySQL, "mysql", "SPT%")

	if err != nil {
		return err
	}

	for _, row := range rows {
		shardInfo := &ShardInfo{}
		shardInfo.IP = row["host"].(string)
		shardInfo.Port, _ = strconv.Atoi(row["port"].(string))
		shardInfo.Account = row["username"].(string)
		shardInfo.PWD = row["password"].(string)
		shardInfo.ShardID, _ = strconv.Atoi(row["shard_id"].(string))
		c.ShardInfos = append(c.ShardInfos, shardInfo)
	}

	return nil
}

func (s *ShardInfo) GetShardConn() (conn *native.DbWorker, err error) {
	conn, err = native.InsObject{
		Host: s.IP,
		Port: s.Port,
		User: s.Account,
		Pwd:  s.PWD,
	}.Conn()
	if err != nil {
		return nil, err
	}
	return conn, err
}

// 整合所有分片下的表错误信息
func collectTdbCluPartitionErrors(tdbCluPartConf *TdbCluPartConf) []string {
	// 整合所有分片下的表错误信息
	var allTableErrors []string
	for _, shardResult := range tdbCluPartConf.PartitionExecSummary.ShardResults {

		if shardResult.ConnectionError != nil {
			allTableErrors = append(allTableErrors, fmt.Sprintf("ShardID:%d, IP:%s, Port:%d, Connection error: %v", shardResult.ShardID, shardResult.ShardIP, shardResult.ShardPort, shardResult.ConnectionError))
			continue
		}

		if shardResult.TableCheckError != nil {
			allTableErrors = append(allTableErrors, fmt.Sprintf("ShardID:%d, IP:%s, Port:%d, Table check error: %v", shardResult.ShardID, shardResult.ShardIP, shardResult.ShardPort, shardResult.TableCheckError))
			continue
		}

		for _, tableErr := range shardResult.TableExecInfos {
			errMsg := fmt.Sprintf("ShardID:%d, DB:%s, Table:%s, ExecError:", shardResult.ShardID, tableErr.DbName, tableErr.TbName)
			// If there are step errors, further aggregate
			if !tableErr.Status {
				for _, stepErr := range tableErr.StepInfos {
					if !stepErr.Status {
						errMsg += fmt.Sprintf(" {Step:%s, Status:%v, Message:%s, Statement:%s}", stepErr.Step, stepErr.Status, stepErr.Message, stepErr.Statement)
					}
				}
			}
			allTableErrors = append(allTableErrors, errMsg)
		}
	}
	return allTableErrors
}
