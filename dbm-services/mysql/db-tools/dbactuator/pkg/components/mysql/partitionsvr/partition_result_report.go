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
	"time"

	"dbm-services/common/go-pubpkg/logger"
	reapi "dbm-services/common/reverseapi/apis/common"
	recore "dbm-services/common/reverseapi/pkg/core"
)

// 定义一个事件类型，实现 ISyncReportEvent 接口
type PartitionResultReportEvent struct {
	Cluster    string `json:"cluster_type"`
	BkBizId    int64  `json:"bk_biz_id"`   // 映射数据库字段 bk_biz_id bigint(20)
	BkCloudId  int    `json:"bk_cloud_id"` // 映射数据库字段 bk_cloud_id bigint(20)
	ConfigId   int64  `json:"config_id"`   // 映射数据库字段 config_id int
	CreateTime string `json:"create_time"` // 映射数据库字段 create_time timestamp
	Status     string `json:"status"`      // 映射数据库字段 status varchar(32) success/failed
	ExecLog    string `json:"exec_log"`    // 映射数据库字段 exec_log text
}

func (e *PartitionResultReportEvent) ClusterType() string {
	return e.Cluster
}

func (e *PartitionResultReportEvent) EventType() string {
	return "mysql_partition_result"
}

func (e *PartitionResultReportEvent) EventCreateTime() time.Time {
	createTime, err := time.Parse(time.RFC3339, e.CreateTime)
	if err != nil {
		return time.Now().UTC()
	}
	return createTime
}

func (e *PartitionResultReportEvent) EventBkBizId() int64 {
	if e.BkBizId != 0 {
		return e.BkBizId
	}
	return 0
}

func ReportPartitionResult(result *PartitionResultReportEvent) (err error) {
	logger.Info("ReportPartitionResult: %+v", result)
	reportCore, err := recore.NewCore(int64(result.BkCloudId))
	if err != nil {
		return fmt.Errorf("report NewCore failed: %s", err.Error())
	}

	resp, err := reapi.SyncReportWithDelegateRetry(reportCore, result)
	if err != nil {
		if resp != nil {
			logger.Error("reverseapi protocol error: %s", string(resp))
			return fmt.Errorf("reverseapi protocol error: %s", string(resp))
		}
		logger.Error("report partition result failed: %s", err.Error())
		return fmt.Errorf("report partition result failed: %s", err.Error())
	}
	return nil
}

func FakeReport() *PartitionResultReportEvent {
	now := time.Now().UTC()
	results := []*PartitionResultReportEvent{
		{
			BkBizId:    1001,
			BkCloudId:  1,
			ConfigId:   2,
			CreateTime: now.Add(10 * time.Minute).Format(time.RFC3339),
			Status:     "failed",
			ExecLog:    "partition failed on table foo",
		},
		{
			BkBizId:    1001,
			BkCloudId:  1,
			ConfigId:   3,
			CreateTime: now.Add(20 * time.Minute).Format(time.RFC3339),
			Status:     "success",
			ExecLog:    "partition completed successfully again",
		},
	}

	for _, result := range results {
		fmt.Printf("result: %+v\n", result)
		err := ReportPartitionResult(result)
		if err != nil {
			fmt.Printf("report partition result failed: %s\n", err.Error())
		}
	}
	// 返回最后一条数据
	return results[len(results)-1]
}
