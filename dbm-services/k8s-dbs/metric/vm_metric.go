/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package metric

import (
	"bytes"
	"encoding/json"
	"fmt"
	"strconv"
	"text/template"
	"time"

	"k8s.io/utils/env"

	commutil "k8s-dbs/common/util"
)

const (
	BaseVMApiV1Path     = "http://%s:%s/select/0/prometheus/api/v1/"
	VMApiV1QueryPattern = BaseVMApiV1Path + "query"
)

var pvcStorageUsageTemplate = `sum(vm_data_size_bytes_value{bcs_cluster_id="{{.ClusterID}}", 
job="{{.JobName}}", namespace="{{.Namespace}}", pod="{{.PodName}}"})`

// VMClusterMetricFetcher VictoriaMetrics 获取集群指标实现
type VMClusterMetricFetcher struct{}

// buildPvcStorageUsagePromQL 构建获取 Pvc 使用量的查询 PromQL
func (v *VMClusterMetricFetcher) buildPvcStorageUsagePromQL(params *ClusterMetricQueryParams) (string, error) {
	tmpl, err := template.New("pvcStoragePromQL").Parse(pvcStorageUsageTemplate)
	if err != nil {
		return "", err
	}
	var buf bytes.Buffer
	err = tmpl.Execute(&buf, map[string]string{
		"ClusterID": params.K8sClusterName,
		"Namespace": params.Namespace,
		"JobName":   params.JobName,
		"PodName":   params.PodName,
	})
	if err != nil {
		return "", err
	}
	return buf.String(), nil
}

// GetStorageUsage 获取存储使用量
func (v *VMClusterMetricFetcher) GetStorageUsage(params *ClusterMetricQueryParams) (float64, error) {
	vmMetricServerHost := env.GetString("VM_METRIC_SERVER_HOST", "localhost")
	vmMetricServerPort := env.GetString("VM_METRIC_SERVER_PORT", "8080")
	url := fmt.Sprintf(VMApiV1QueryPattern, vmMetricServerHost, vmMetricServerPort)
	promQL, err := v.buildPvcStorageUsagePromQL(params)
	if err != nil {
		return 0, err
	}
	requestParams := map[string]string{
		"query": promQL,
		"time":  strconv.FormatInt(time.Now().Unix(), 10),
	}
	httpResponse, err := commutil.BaseHTTPClient.PostForm(url, requestParams)
	if err != nil {
		return 0, err
	}
	var vmQueryResponse VMQueryResponse
	if err := json.Unmarshal(httpResponse, &vmQueryResponse); err != nil {
		return 0, err
	}
	// 空结果的检查
	if vmQueryResponse.Status != "success" || len(vmQueryResponse.Data.Result) == 0 {
		return 0, fmt.Errorf("prometheus query returned no data or failed, status: %s", vmQueryResponse.Status)
	}

	metricValue := vmQueryResponse.Data.Result[0].Value
	if len(metricValue) < 2 {
		return 0, fmt.Errorf("invalid metric value format, expected at least 2 elements, got %d", len(metricValue))
	}
	storageSizeBytesStr := fmt.Sprintf("%v", metricValue[1])
	storageSizeBytes, err := strconv.ParseFloat(storageSizeBytesStr, 64)

	if err != nil {
		return 0, err
	}
	storageSizeGB := commutil.RoundToDecimal(commutil.ConvertByteToGB(storageSizeBytes), 3)
	return storageSizeGB, nil
}

// VMQueryResponse vm http 请求响应结构体
type VMQueryResponse struct {
	Status    string `json:"status"`
	IsPartial bool   `json:"isPartial"`
	Data      struct {
		ResultType string `json:"resultType"`
		Result     []struct {
			Metric map[string]string `json:"metric"`
			Value  []interface{}     `json:"value"`
		}
	}
	//nolint:unused
	stats struct {
		SeriesFetched     string `json:"seriesFetched"`
		ExecutionTimeMsec int64  `json:"executionTimeMsec"`
	}
}
