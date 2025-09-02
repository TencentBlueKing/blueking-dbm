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
	dbserrors "k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"

	opv1 "github.com/apecloud/kubeblocks/apis/operations/v1alpha1"

	"k8s.io/apimachinery/pkg/runtime"
)

// SaveCommonAuditV2 记录通用审计日志
func SaveCommonAuditV2(
	reqRecordProvider metaprovider.ClusterRequestRecordProvider,
	dbsCtx *commentity.DbsContext,
) (*metaentity.ClusterRequestRecordEntity, error) {
	requestBytes, err := json.Marshal(dbsCtx.APIRequestParams)
	if err != nil {
		return nil, fmt.Errorf("serialization request failed: %v", err)
	}

	requestRecord := &metaentity.ClusterRequestRecordEntity{
		K8sClusterName: dbsCtx.K8sClusterName,
		ClusterName:    dbsCtx.ClusterName,
		NameSpace:      dbsCtx.Namespace,
		RequestID:      commutil.RequestID(),
		RequestType:    dbsCtx.RequestType,
		RequestParams:  string(requestBytes),
		CreatedBy:      dbsCtx.BkAuth.BkUserName,
		UpdatedBy:      dbsCtx.BkAuth.BkUserName,
	}

	addedRequestRecord, err := reqRecordProvider.CreateRequestRecord(requestRecord)
	if err != nil {
		return nil, fmt.Errorf("审计日志记录失败: %w", err)
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
		return nil, fmt.Errorf("审计日志记录失败: %w", err)
	}
	return addedRequestRecord, nil
}

// GetClusterMeta 获取集群元数据.
func GetClusterMeta(
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
	request *coreentity.Request,
	k8sClusterConfig *metaentity.K8sClusterConfigEntity,
) (*metaentity.K8sCrdClusterEntity, error) {
	clusterQueryParams := &metaentity.ClusterQueryParams{
		ClusterName:        request.ClusterName,
		Namespace:          request.Namespace,
		K8sClusterConfigID: k8sClusterConfig.ID,
	}
	clusterEntity, err := clusterMetaProvider.FindByParams(clusterQueryParams)
	if err != nil {
		return nil, dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError,
			fmt.Errorf("检索集群 %s 元数据失败 %w ", request.ClusterName, err))
	}
	if clusterEntity == nil {
		return nil, dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError,
			fmt.Errorf("集群 %s 不存在", request.ClusterName))
	}
	return clusterEntity, nil
}

// UpdateClusterMeta 更新 cluster 元数据
func UpdateClusterMeta(
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
	dbsCtx *commentity.DbsContext,
	request *coreentity.Request,
) error {
	clusterEntity, err := clusterMetaProvider.FindByParams(&metaentity.ClusterQueryParams{
		K8sClusterConfigID: dbsCtx.K8sClusterConfigID,
		ClusterName:        request.ClusterName,
		Namespace:          request.Namespace,
	})
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError,
			fmt.Errorf("检索集群 %s 元数据失败 %w ", request.ClusterName, err))
	}
	if clusterEntity == nil {
		return dbserrors.NewK8sDbsError(dbserrors.GetClusterError,
			fmt.Errorf("集群 %s 不存在", request.ClusterName))
	}
	if request.BkUserName != "" {
		clusterEntity.UpdatedBy = request.BkUserName
	}
	if request.TerminationPolicy != "" {
		clusterEntity.TerminationPolicy = request.TerminationPolicy
	}
	if request.AddonClusterVersion != "" {
		clusterEntity.AddonClusterVersion = request.AddonClusterVersion
	}
	_, err = clusterMetaProvider.UpdateCluster(clusterEntity)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.UpdateMetaDataError,
			fmt.Errorf("更新集群 %s 元数据失败 %w ", request.ClusterName, err))
	}
	return nil
}

// UpdateClusterLastUpdatedV2 v2版本 更新 cluster 元数据最近一次更新时间和更新人
func UpdateClusterLastUpdatedV2(
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
	dbsCtx *commentity.DbsContext,
) error {
	clusterEntity, err := clusterMetaProvider.FindByParams(&metaentity.ClusterQueryParams{
		K8sClusterConfigID: dbsCtx.K8sClusterConfigID,
		ClusterName:        dbsCtx.ClusterName,
		Namespace:          dbsCtx.Namespace,
	})
	if err != nil {
		return err
	}
	clusterEntity.UpdatedBy = dbsCtx.BkAuth.BkUserName
	_, err = clusterMetaProvider.UpdateCluster(clusterEntity)
	if err != nil {
		return err
	}
	return nil
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
	releaseEntity, values, err := getClusterMetaRelease(releaseMetaProvider, request, k8sClusterConfigID)
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
	releaseEntity.UpdatedBy = request.BkUserName
	_, err = releaseMetaProvider.UpdateClusterRelease(releaseEntity)
	if err != nil {
		return nil, err
	}
	return releaseEntity, nil
}

// UpdateValWithHScaling updates the release entity's chart values with horizontal scaling configurations.
func UpdateValWithHScaling(
	releaseMetaProvider metaprovider.AddonClusterReleaseProvider,
	request *coreentity.Request,
	k8sClusterConfigID uint64,
) (*metaentity.AddonClusterReleaseEntity, error) {
	releaseEntity, values, err := getClusterMetaRelease(releaseMetaProvider, request, k8sClusterConfigID)
	if err != nil {
		return nil, err
	}
	compListFromVal, _ := values["componentList"].([]interface{})
	for _, scaling := range request.HorizontalScalingList {
		for i, itemFromVal := range compListFromVal {
			compFromVal, ok := itemFromVal.(map[string]interface{})
			if ok && compFromVal["componentName"] == scaling.ComponentName {
				// modify the replica according to different status
				currentReplicas := int(compFromVal["replicas"].(float64))
				if scaling.ScaleOut != nil && scaling.ScaleOut.ReplicaChanges != nil {
					scaleOutValue := *scaling.ScaleOut.ReplicaChanges
					compFromVal["replicas"] = currentReplicas + int(scaleOutValue)
				}
				if scaling.ScaleIn != nil && scaling.ScaleIn.ReplicaChanges != nil {
					scaleInValue := *scaling.ScaleIn.ReplicaChanges
					compFromVal["replicas"] = currentReplicas - int(scaleInValue)
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
	releaseEntity.UpdatedBy = request.BkUserName
	_, err = releaseMetaProvider.UpdateClusterRelease(releaseEntity)
	if err != nil {
		return nil, err
	}
	return releaseEntity, nil
}

// getClusterMetaRelease 获取当前集群 release 信息
func getClusterMetaRelease(
	releaseMetaProvider metaprovider.AddonClusterReleaseProvider,
	request *coreentity.Request,
	k8sClusterConfigID uint64,
) (*metaentity.AddonClusterReleaseEntity,
	map[string]interface{},
	error,
) {
	params := &metaentity.ClusterReleaseQueryParams{
		K8sClusterConfigID: k8sClusterConfigID,
		ReleaseName:        request.ClusterName,
		Namespace:          request.Namespace,
	}
	releaseEntity, err := releaseMetaProvider.FindByParams(params)
	if err != nil {
		return nil, nil, err
	}

	values, err := commutil.JSONStrToMap(releaseEntity.ChartValues)
	if err != nil {
		return nil, nil, err
	}
	return releaseEntity, values, nil
}
