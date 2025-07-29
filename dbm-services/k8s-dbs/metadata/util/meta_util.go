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

package util

import (
	"encoding/json"
	"fmt"
	commentity "k8s-dbs/common/entity"
	commutil "k8s-dbs/common/util"
	coreentity "k8s-dbs/core/entity"
	coreutil "k8s-dbs/core/util"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"

	opv1 "github.com/apecloud/kubeblocks/apis/operations/v1alpha1"

	"k8s.io/apimachinery/pkg/runtime"
)

// CreateRequestRecord Save request
func CreateRequestRecord(
	dbsContext *commentity.DbsContext,
	requestParams interface{},
	requestType string,
	reqRecordProvider metaprovider.ClusterRequestRecordProvider,
) (*metaentity.ClusterRequestRecordEntity, error) {
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

	requestRecord := &metaentity.ClusterRequestRecordEntity{
		RequestID:     commutil.RequestID(),
		RequestType:   requestType,
		RequestParams: string(serializedRequest),
		CreatedBy:     dbsContext.BkAuth.BkUserName,
		UpdatedBy:     dbsContext.BkAuth.BkUserName,
	}
	addedRequestRecord, err := reqRecordProvider.CreateRequestRecord(requestRecord)
	if err != nil {
		return nil, fmt.Errorf("failed to create request record entity: %w", err)
	}
	return addedRequestRecord, nil
}

// SaveAuditLog 记录审计日志
func SaveAuditLog(
	reqRecordProvider metaprovider.ClusterRequestRecordProvider,
	request *coreentity.Request,
	requestType string,
) (*metaentity.ClusterRequestRecordEntity, error) {
	requestBytes, err := json.Marshal(request)
	if err != nil {
		return nil, fmt.Errorf("serialization request failed: %v", err)
	}

	requestRecord := &metaentity.ClusterRequestRecordEntity{
		K8sClusterName: request.K8sClusterName,
		ClusterName:    request.ClusterName,
		NameSpace:      request.Namespace,
		RequestID:      commutil.RequestID(),
		RequestType:    requestType,
		RequestParams:  string(requestBytes),
		CreatedBy:      request.BKAuth.BkUserName,
		UpdatedBy:      request.BKAuth.BkUserName,
	}

	addedRequestRecord, err := reqRecordProvider.CreateRequestRecord(requestRecord)
	if err != nil {
		return nil, fmt.Errorf("failed to create request entity: %w", err)
	}
	return addedRequestRecord, nil
}

// CreateOpsRequestMetaData 构建 opsRequest 元数据
func CreateOpsRequestMetaData(
	opsRequestProvider metaprovider.K8sCrdOpsRequestProvider,
	crdClusterProvider metaprovider.K8sCrdClusterProvider,
	request *coreentity.Request,
	crd *coreentity.CustomResourceDefinition,
	requestID string,
	k8sClusterConfigID uint64,
) error {
	opsReqEntity, err := getEntityFromReq(crd)
	if err != nil {
		return err
	}
	params := metaentity.ClusterQueryParams{
		ClusterName: request.ClusterName,
		Namespace:   request.Namespace,
	}
	clusterEntity, err := crdClusterProvider.FindByParams(&params)
	if err != nil {
		return err
	}

	opsReqEntity.CrdClusterID = clusterEntity.ID
	opsReqEntity.RequestID = requestID
	opsReqEntity.K8sClusterConfigID = k8sClusterConfigID

	_, err = opsRequestProvider.CreateOpsRequest(opsReqEntity)
	if err != nil {
		return err
	}
	return nil
}

// getEntityFromReq 解析 request 构建 K8sCrdOpsRequestEntity
func getEntityFromReq(crd *coreentity.CustomResourceDefinition) (*metaentity.K8sCrdOpsRequestEntity, error) {
	var opsRequestObject opv1.OpsRequest
	err := runtime.DefaultUnstructuredConverter.FromUnstructured(crd.ResourceObject.Object, &opsRequestObject)
	if err != nil {
		return nil, err
	}

	metaDataJSON, err := json.Marshal(opsRequestObject.ObjectMeta)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal metaData to JSON: %w", err)
	}
	specJSON, err := json.Marshal(opsRequestObject.Spec)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal spec to JSON: %w", err)
	}

	opsReqEntity := &metaentity.K8sCrdOpsRequestEntity{
		OpsRequestName: opsRequestObject.Name,
		OpsRequestType: crd.ResourceType,
		Metadata:       string(metaDataJSON),
		Spec:           string(specJSON),
	}
	return opsReqEntity, nil
}

// UpdateValWithCompList updates the release entity's chart values with component configurations.
func UpdateValWithCompList(
	releaseMetaProvider metaprovider.AddonClusterReleaseProvider,
	request *coreentity.Request,
	k8sClusterConfigID uint64,
) (*metaentity.AddonClusterReleaseEntity, error) {

	params := &metaentity.ClusterReleaseQueryParams{
		K8sClusterConfigID: k8sClusterConfigID,
		ReleaseName:        request.ClusterName,
		Namespace:          request.Namespace,
	}
	releaseEntity, err := releaseMetaProvider.FindByParams(params)
	if err != nil {
		return nil, err
	}

	values, err := commutil.JSONStrToMap(releaseEntity.ChartValues)
	if err != nil {
		return nil, err
	}

	compListFromVal, _ := values["componentList"].([]interface{})
	for _, compFromReq := range request.ComponentList {
		for i, itemFromVal := range compListFromVal {
			compFromVal, ok := itemFromVal.(map[string]interface{})
			if ok && compFromVal["componentName"] == compFromReq.ComponentName {

				if compFromReq.Version != "" {
					compFromVal["serviceVersion"] = compFromReq.Version
				}

				volumeClaimTemplates, vctOk := compFromVal["volumeClaimTemplates"].(map[string]interface{})
				if vctOk && !compFromReq.Storage.IsZero() {
					volumeClaimTemplates["storage"] = compFromReq.Storage
					compFromVal["volumeClaimTemplates"] = volumeClaimTemplates
				}

				resources, resOk := compFromVal["resources"].(map[string]interface{})
				if !resOk {
					resources = make(map[string]interface{})
					compFromVal["resources"] = resources
				}
				err = coreutil.MergeObjectToVal(resources, compFromReq.Request, "requests")
				if err != nil {
					return nil, err
				}
				err = coreutil.MergeObjectToVal(resources, compFromReq.Limit, "limits")
				if err != nil {
					return nil, err
				}

				compListFromVal[i] = compFromVal
			}
		}
	}
	values["componentList"] = compListFromVal

	jsonStr, err := commutil.MapToJSONStr(values)
	if err != nil {
		return nil, err
	}
	releaseEntity.ChartValues = jsonStr

	_, err = releaseMetaProvider.UpdateClusterRelease(releaseEntity)
	if err != nil {
		return nil, err
	}
	return releaseEntity, nil
}
