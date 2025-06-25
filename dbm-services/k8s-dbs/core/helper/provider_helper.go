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

package helper

import (
	"encoding/json"
	"fmt"
	"k8s-dbs/common/util"
	coreclient "k8s-dbs/core/client"
	metaprovider "k8s-dbs/metadata/provider"
	providerentity "k8s-dbs/metadata/provider/entity"
	"log/slog"

	"helm.sh/helm/v3/pkg/action"
)

// CreateRequestRecord Save request
func CreateRequestRecord(
	requestParams interface{},
	requestType string,
	reqRecordProvider metaprovider.ClusterRequestRecordProvider,
) (*providerentity.ClusterRequestRecordEntity, error) {
	if requestParams == nil {
		return nil, fmt.Errorf("requestParams is nil")
	}

	if requestType == "" {
		return nil, fmt.Errorf("requestType is empty")
	}
	serializedRequest, err := json.Marshal(requestParams)
	if err != nil {
		return nil, fmt.Errorf("failed to serialize request parameters: %w", err)
	}

	requestRecord := &providerentity.ClusterRequestRecordEntity{
		RequestID:     util.RequestID(),
		RequestType:   requestType,
		RequestParams: string(serializedRequest),
	}
	addedRequestRecord, err := reqRecordProvider.CreateRequestRecord(requestRecord)
	if err != nil {
		return nil, fmt.Errorf("failed to create request record entity: %w", err)
	}
	return addedRequestRecord, nil
}

// BuildHelmActionConfig 构建 helm action config
func BuildHelmActionConfig(
	namespace string,
	k8sClient *coreclient.K8sClient,
) (*action.Configuration, error) {
	actionConfig, err := k8sClient.BuildHelmConfig(namespace)
	if err != nil {
		slog.Error("failed to build Helm configuration",
			"namespace", namespace,
			"error", err,
		)
		return nil, fmt.Errorf("failed to build Helm configuration for namespace %q: %w",
			namespace, err)
	}
	return actionConfig, nil
}
