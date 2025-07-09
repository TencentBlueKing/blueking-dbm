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
	"k8s-dbs/core/client"
	coreclient "k8s-dbs/core/client"
	clientconst "k8s-dbs/core/client/constants"
	coreconst "k8s-dbs/core/constant"
	"k8s-dbs/core/entity"
	metaenitty "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"
	"strings"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/util/intstr"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	kbv1 "github.com/apecloud/kubeblocks/apis/apps/v1alpha1"
	opv1 "github.com/apecloud/kubeblocks/apis/operations/v1alpha1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
)

// opsrequest 定义操作请求相关的常量
const (
	TTLSecondsAfterSucceed      int32 = 600
	PreConditionDeadlineSeconds int32 = 10
	TimeoutSeconds              int32 = 600
	OpsNameSuffixLength         int   = 10
)

// componentTargetPortsMap 组件目标端口映射表
// key: 组件名称
// value: 组件暴露的端口列表
var componentTargetPortsMap = map[string][]string{
	"surreal":   {"http"},
	"tikv":      {"peer", "status"},
	"pd":        {"client", "peer"},
	"attu":      {"attu"},
	"proxy":     {"milvus"},
	"minio":     {"console"},
	"vmstorage": {"vmselect"},
	"vminsert":  {"http"},
	"vmselect":  {"http"},
}

// switchTypeMap 暴露开关类型映射表
// key: 布尔值(true/false)
// value: 对应的ExposeSwitch枚举值
var switchTypeMap = map[bool]opv1.ExposeSwitch{
	true:  opv1.EnableExposeSwitch,
	false: opv1.DisableExposeSwitch,
}

// CreateVerticalScalingObject 创建垂直伸缩操作请求对象
// 参数:
//
//	request - 包含操作请求信息的结构体
//
// 返回值:
//
//	*entity.CustomResourceDefinition - 创建的CRD对象
//	error - 错误信息(如果有)
func CreateVerticalScalingObject(request *entity.Request) (*entity.CustomResourceDefinition, error) {
	objectName := util.ResourceName("ops-vscaling-", OpsNameSuffixLength)
	var verticalScalingList []opv1.VerticalScaling
	for _, comp := range request.ComponentList {
		err := checkResourceFromComp(comp)
		if err != nil {
			return nil, err
		}

		// Initializes the container for resource requests and limits
		requests := corev1.ResourceList{
			corev1.ResourceCPU:    comp.Request.CPU,
			corev1.ResourceMemory: comp.Request.Memory,
		}
		limits := corev1.ResourceList{
			corev1.ResourceCPU:    comp.Limit.CPU,
			corev1.ResourceMemory: comp.Limit.Memory,
		}

		vscaling := opv1.VerticalScaling{
			ComponentOps: opv1.ComponentOps{
				ComponentName: comp.ComponentName,
			},
			ResourceRequirements: corev1.ResourceRequirements{
				Requests: requests,
				Limits:   limits,
			},
		}
		verticalScalingList = append(verticalScalingList, vscaling)
	}

	verticalScaling := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: coreconst.APIVersion,
			Kind:       coreconst.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        coreconst.VerticalScaling,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: util.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              util.Int32Ptr(TimeoutSeconds),
			SpecificOpsRequest: opv1.SpecificOpsRequest{
				VerticalScalingList: verticalScalingList,
			},
		},
	}

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&verticalScaling)
	if err != nil {
		return nil, fmt.Errorf("转换对象为Unstructured类型失败: %v", err)
	}

	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}
	crd := &entity.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         coreconst.VerticalScaling,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateHorizontalScalingObject 创建水平伸缩操作请求对象
// 参数和返回值同CreateVerticalScalingObject
func CreateHorizontalScalingObject(request *entity.Request) (*entity.CustomResourceDefinition, error) {
	objectName := util.ResourceName("ops-hs-", OpsNameSuffixLength)

	horizontalScaling := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: coreconst.APIVersion,
			Kind:       coreconst.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        coreconst.HorizontalScaling,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: util.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              util.Int32Ptr(TimeoutSeconds),
			SpecificOpsRequest: opv1.SpecificOpsRequest{
				HorizontalScalingList: request.Spec.HorizontalScalingList,
			},
		},
	}

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&horizontalScaling)
	if err != nil {
		return nil, fmt.Errorf("转换对象为Unstructured类型失败: %v", err)
	}

	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}
	crd := &entity.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         coreconst.HorizontalScaling,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateStopClusterObject 创建停止集群操作请求对象
// 参数和返回值同CreateVerticalScalingObject
func CreateStopClusterObject(request *entity.Request) (*entity.CustomResourceDefinition, error) {
	objectName := util.ResourceName("ops-stop-", OpsNameSuffixLength)

	stop := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: coreconst.APIVersion,
			Kind:       coreconst.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        coreconst.Stop,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: util.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              util.Int32Ptr(TimeoutSeconds),
			SpecificOpsRequest: opv1.SpecificOpsRequest{
				StopList: request.Spec.StopList,
			},
		},
	}

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&stop)
	if err != nil {
		return nil, fmt.Errorf("转换对象为Unstructured类型失败: %v", err)
	}

	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}
	crd := &entity.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         coreconst.Stop,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateStartClusterObject 创建启动集群操作请求对象
// 参数和返回值同CreateVerticalScalingObject
func CreateStartClusterObject(request *entity.Request) (*entity.CustomResourceDefinition, error) {
	objectName := util.ResourceName("ops-start-", OpsNameSuffixLength)

	start := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: coreconst.APIVersion,
			Kind:       coreconst.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        coreconst.Start,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: util.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              util.Int32Ptr(TimeoutSeconds),
			SpecificOpsRequest: opv1.SpecificOpsRequest{
				StartList: request.Spec.StartList,
			},
		},
	}

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&start)
	if err != nil {
		return nil, fmt.Errorf("转换对象为Unstructured类型失败: %v", err)
	}

	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}
	crd := &entity.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         coreconst.Start,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateRestartClusterObject 创建重启集群操作请求对象
// 参数和返回值同CreateVerticalScalingObject
func CreateRestartClusterObject(request *entity.Request) (*entity.CustomResourceDefinition, error) {
	objectName := util.ResourceName("ops-restart-", OpsNameSuffixLength)

	restart := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: coreconst.APIVersion,
			Kind:       coreconst.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        coreconst.Restart,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: util.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              util.Int32Ptr(TimeoutSeconds),
			SpecificOpsRequest: opv1.SpecificOpsRequest{
				RestartList: request.Spec.RestartList,
			},
		},
	}

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&restart)
	if err != nil {
		return nil, fmt.Errorf("转换对象为Unstructured类型失败: %v", err)
	}

	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}
	crd := &entity.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         coreconst.Restart,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateUpgradeClusterObject 创建升级集群操作请求对象
// 参数:
//
//	request - 包含操作请求信息的结构体
//	clusterObject - 集群对象
//
// 返回值:
//
//	*entity.CustomResourceDefinition - 创建的CRD对象
//	error - 错误信息(如果有)
func CreateUpgradeClusterObject(request *entity.Request, clusterObject *kbv1.Cluster) (
	*entity.CustomResourceDefinition, error,
) {
	objectName := util.ResourceName("ops-upgrade-", OpsNameSuffixLength)
	var upgradeComponents []opv1.UpgradeComponent
	for _, compFromReq := range request.ComponentList {
		for _, compFromCluster := range clusterObject.Spec.ComponentSpecs {
			if compFromCluster.Name == compFromReq.ComponentName {
				var cmpdName string
				if compFromReq.ComponentDef != "" {
					cmpdName = compFromReq.ComponentDef
				} else {
					cmpdName = compFromCluster.ComponentDef
				}

				upgradeComponents = append(upgradeComponents, opv1.UpgradeComponent{
					ComponentOps: opv1.ComponentOps{
						ComponentName: compFromReq.ComponentName,
					},
					ComponentDefinitionName: util.StringPtr(cmpdName),
					ServiceVersion:          util.StringPtr(compFromReq.Version),
				})
			}
		}
	}

	upgrade := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: coreconst.APIVersion,
			Kind:       coreconst.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        coreconst.Upgrade,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: util.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              util.Int32Ptr(TimeoutSeconds),
			SpecificOpsRequest: opv1.SpecificOpsRequest{
				Upgrade: &opv1.Upgrade{
					Components: upgradeComponents,
				},
			},
		},
	}

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&upgrade)
	if err != nil {
		return nil, fmt.Errorf("转换对象为Unstructured类型失败: %v", err)
	}

	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}
	crd := &entity.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         coreconst.Upgrade,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateVolumeExpansionObject 创建存储卷扩容操作请求对象
// 参数:
//
//	request - 包含操作请求信息的结构体
//	clusterObject - 集群对象
//
// 返回值:
//
//	*entity.CustomResourceDefinition - 创建的CRD对象
//	error - 错误信息(如果有)
func CreateVolumeExpansionObject(request *entity.Request, clusterObject *kbv1.Cluster) (
	*entity.CustomResourceDefinition, error,
) {
	objectName := util.ResourceName("ops-vexpansion-", OpsNameSuffixLength)
	var volumeExpansionList []opv1.VolumeExpansion
	for _, compFromReq := range request.ComponentList {
		// get component names
		volumeExpansion := opv1.VolumeExpansion{
			ComponentOps: opv1.ComponentOps{
				ComponentName: compFromReq.ComponentName,
			},
		}
		for _, compFromCluster := range clusterObject.Spec.ComponentSpecs {
			if compFromCluster.Name == compFromReq.ComponentName {
				// get vct names
				var volumeClaimTemplates []opv1.OpsRequestVolumeClaimTemplate
				for _, vct := range compFromCluster.VolumeClaimTemplates {

					// Check whether the storage increment is reasonable
					currentStorage := vct.Spec.Resources.Requests.Storage().DeepCopy()
					currentStorage.Add(compFromReq.Storage)
					storageClassName := vct.Spec.StorageClassName

					err := coreclient.CheckStorageBySC(*storageClassName, currentStorage)
					if err != nil {
						slog.Error("failed to check storage by SC", "err", err)
						return nil, err
					}

					volumeClaimTemplates = append(volumeClaimTemplates, opv1.OpsRequestVolumeClaimTemplate{
						Name:    vct.Name,
						Storage: currentStorage,
					})
				}
				volumeExpansion.VolumeClaimTemplates = volumeClaimTemplates
			}
		}
		volumeExpansionList = append(volumeExpansionList, volumeExpansion)
	}

	volumeExpansion := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: coreconst.APIVersion,
			Kind:       coreconst.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        coreconst.VolumeExpansion,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: util.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              util.Int32Ptr(TimeoutSeconds),
			SpecificOpsRequest: opv1.SpecificOpsRequest{
				VolumeExpansionList: volumeExpansionList,
			},
		},
	}

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&volumeExpansion)
	if err != nil {
		return nil, fmt.Errorf("转换对象为Unstructured类型失败: %v", err)
	}

	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}
	crd := &entity.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         coreconst.VolumeExpansion,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateExposeClusterObject 创建暴露服务操作请求对象
// 参数:
//
//	request - 包含操作请求信息的结构体
//
// 返回值:
//
//	*entity.CustomResourceDefinition - 创建的CRD对象
//	error - 错误信息(如果有)
func CreateExposeClusterObject(request *entity.Request) (*entity.CustomResourceDefinition, error) {
	objectName := util.ResourceName("ops-expose-", OpsNameSuffixLength)
	// Convert selector key about kb
	podSelect := request.Service.PodSelect
	for key, value := range podSelect {
		if newKey, exists := clientconst.PodSelectLabel[key]; exists {
			delete(podSelect, key)
			podSelect[newKey] = value
		}
	}
	opsService, err := createOpsService(request, podSelect)
	if err != nil {
		return nil, err
	}

	opsRequest := createExposeOpsRequest(request, opsService, objectName)

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&opsRequest)
	if err != nil {
		return nil, fmt.Errorf("转换对象为 Unstructured 类型失败: %v", err)
	}
	crd := &entity.CustomResourceDefinition{
		Labels:               request.Metadata.Labels,
		Namespace:            request.Metadata.Namespace,
		ResourceType:         coreconst.Expose,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject: &unstructured.Unstructured{
			Object: unstructuredClusterDef,
		},
	}
	return crd, nil
}

func createExposeOpsRequest(
	request *entity.Request,
	service opv1.OpsService,
	objectName string,
) *opv1.OpsRequest {
	expose := opv1.Expose{
		ComponentName: request.ComponentName,
		Switch:        switchTypeMap[request.Enable],
		Services:      []opv1.OpsService{service},
	}

	opsRequest := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: coreconst.APIVersion,
			Kind:       coreconst.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        coreconst.Expose,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: util.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              util.Int32Ptr(TimeoutSeconds),
			SpecificOpsRequest: opv1.SpecificOpsRequest{
				ExposeList: []opv1.Expose{
					expose,
				},
			},
		},
	}
	return opsRequest
}

func createOpsService(request *entity.Request, podSelect map[string]string) (opv1.OpsService, error) {
	service := opv1.OpsService{
		Name:         request.Service.Name,
		ServiceType:  request.Service.ServiceType,
		Annotations:  request.Service.Annotations,
		Ports:        []corev1.ServicePort{},
		RoleSelector: request.Service.RoleSelector,
		PodSelector:  podSelect,
	}
	if ports, exists := componentTargetPortsMap[request.ComponentName]; exists {
		componentPortsLen := len(ports)
		exposePortsLen := len(request.Service.Ports)
		if exposePortsLen > componentPortsLen {
			return opv1.OpsService{}, fmt.Errorf("暴露端口数 %d 超过组件可暴露的端口数 %d", exposePortsLen, componentPortsLen)
		}
		for i := 0; i < exposePortsLen; i++ {
			protocol := corev1.ProtocolTCP
			if i < len(request.Service.Protocols) {
				protocol = request.Service.Protocols[i]
			}
			if i < len(request.Service.NodePorts) &&
				strings.EqualFold(string(request.Service.ServiceType), string(corev1.ServiceTypeNodePort)) {
				service.Ports = append(service.Ports, corev1.ServicePort{
					Name:       ports[i],
					Port:       request.Service.Ports[i],
					TargetPort: intstr.FromString(ports[i]),
					Protocol:   protocol,
					NodePort:   request.Service.NodePorts[i],
				})
			} else {
				service.Ports = append(service.Ports, corev1.ServicePort{
					Name:       ports[i],
					Port:       request.Service.Ports[i],
					TargetPort: intstr.FromString(ports[i]),
					Protocol:   protocol,
				})
			}
		}
	}
	return service, nil
}

// CreateOpsRequestMetaData 构建 opsRequest 元数据
func CreateOpsRequestMetaData(
	opsRequestProvider metaprovider.K8sCrdOpsRequestProvider,
	crdClusterProvider metaprovider.K8sCrdClusterProvider,
	request *entity.Request,
	crd *entity.CustomResourceDefinition,
	requestID string,
	k8sClusterConfigID uint64,
) error {
	opsReqEntity, err := getEntityFromReq(crd)
	if err != nil {
		return err
	}
	params := metaenitty.ClusterQueryParams{
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
func getEntityFromReq(crd *entity.CustomResourceDefinition) (*metaenitty.K8sCrdOpsRequestEntity, error) {
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

	opsReqEntity := &metaenitty.K8sCrdOpsRequestEntity{
		OpsRequestName: opsRequestObject.Name,
		OpsRequestType: crd.ResourceType,
		Metadata:       string(metaDataJSON),
		Spec:           string(specJSON),
	}
	return opsReqEntity, nil
}

// UpdateValWithHScaling updates the release entity's chart values with horizontal scaling configurations.
func UpdateValWithHScaling(
	request *entity.Request,
	releaseEntity *metaenitty.AddonClusterReleaseEntity,
) (*metaenitty.AddonClusterReleaseEntity, error) {
	values, err := stringToMap(releaseEntity.ChartValues)
	if err != nil {
		return nil, err
	}

	compListFromVal, _ := values["componentList"].([]interface{})
	for _, hscaling := range request.HorizontalScalingList {
		for i, itemFromVal := range compListFromVal {
			compFromVal, ok := itemFromVal.(map[string]interface{})
			if ok && compFromVal["componentName"] == hscaling.ComponentName {

				// modify the replica according to different status
				currentReplicas := int(compFromVal["replicas"].(float64))
				if hscaling.ScaleOut != nil && hscaling.ScaleOut.ReplicaChanges != nil {
					scaleOutValue := *hscaling.ScaleOut.ReplicaChanges
					compFromVal["replicas"] = currentReplicas + int(scaleOutValue)
				}
				if hscaling.ScaleIn != nil && hscaling.ScaleIn.ReplicaChanges != nil {
					scaleInValue := *hscaling.ScaleIn.ReplicaChanges
					compFromVal["replicas"] = currentReplicas - int(scaleInValue)
				}
				compListFromVal[i] = compFromVal
			}
		}
	}
	values["componentList"] = compListFromVal

	jsonStr, err := mapToString(values, request)
	if err != nil {
		return nil, err
	}
	releaseEntity.ChartValues = jsonStr
	return releaseEntity, nil
}

// UpdateValWithCompList updates the release entity's chart values with component configurations.
func UpdateValWithCompList(
	releaseMetaProvider metaprovider.AddonClusterReleaseProvider,
	request *entity.Request,
	k8sClusterConfigID uint64,
) (*metaenitty.AddonClusterReleaseEntity, error) {

	params := &metaenitty.ClusterReleaseQueryParams{
		K8sClusterConfigID: k8sClusterConfigID,
		ReleaseName:        request.ClusterName,
		Namespace:          request.Namespace,
	}
	releaseEntity, err := releaseMetaProvider.FindByParams(params)
	if err != nil {
		return nil, err
	}

	values, err := stringToMap(releaseEntity.ChartValues)
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
				err = client.MergeObjectToVal(resources, compFromReq.Request, "requests")
				if err != nil {
					return nil, err
				}
				err = client.MergeObjectToVal(resources, compFromReq.Limit, "limits")
				if err != nil {
					return nil, err
				}

				compListFromVal[i] = compFromVal
			}
		}
	}
	values["componentList"] = compListFromVal

	jsonStr, err := mapToString(values, request)
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

func stringToMap(value string) (map[string]interface{}, error) {
	var result map[string]interface{}
	// convert string to byte array and then parse
	if err := json.Unmarshal([]byte(value), &result); err != nil {
		slog.Error("Failed to unmarshal chart values",
			"error", err,
			"value", value,
		)
		return nil, fmt.Errorf("unmarshal failed: %w", err)
	}
	return result, nil
}

func mapToString(value map[string]interface{}, request *entity.Request) (string, error) {
	jsonData, err := json.Marshal(value)
	if err != nil {
		slog.Error("failed to marshal release values",
			"release_name", request.ClusterName,
			"error", err,
		)
		return "", fmt.Errorf("failed to marshal release values: %w", err)
	}

	return string(jsonData), nil
}

func checkResourceFromComp(comp entity.ComponentResource) error {
	// Check whether resource configuration is complete
	if comp.Limit == nil || comp.Request == nil {
		slog.Error("component resource validation failed",
			"component", comp.ComponentName,
			"error", "resource limits or requests must be defined",
		)
		return fmt.Errorf(
			"component '%s' resource validation failed: limits and requests must be defined (missing field)",
			comp.ComponentName,
		)
	}

	// Verify the Limits field
	if comp.Limit.CPU.IsZero() {
		slog.Error("component resource validation failed",
			"component", comp.ComponentName,
			"field", "limits.cpu",
			"error", "CPU limit must be greater than zero",
		)
		return fmt.Errorf(
			"component '%s' resource validation failed: CPU limit cannot be zero",
			comp.ComponentName,
		)
	}
	if comp.Limit.Memory.IsZero() {
		slog.Error("component resource validation failed",
			"component", comp.ComponentName,
			"field", "limits.memory",
			"error", "memory limit must be greater than zero",
		)
		return fmt.Errorf(
			"component '%s' resource validation failed: memory limit cannot be zero",
			comp.ComponentName,
		)
	}

	// Verify the Request field
	if comp.Request.CPU.IsZero() {
		slog.Error("component resource validation failed",
			"component", comp.ComponentName,
			"field", "requests.cpu",
			"error", "CPU request must be greater than zero",
		)
		return fmt.Errorf(
			"component '%s' resource validation failed: CPU request cannot be zero",
			comp.ComponentName,
		)
	}
	if comp.Request.Memory.IsZero() {
		slog.Error("component resource validation failed",
			"component", comp.ComponentName,
			"field", "requests.memory",
			"error", "memory request must be greater than zero",
		)
		return fmt.Errorf(
			"component '%s' resource validation failed: memory request cannot be zero",
			comp.ComponentName,
		)
	}

	// Verify Requests ≤ Limits
	if comp.Request.CPU.Cmp(comp.Limit.CPU) > 0 {
		return fmt.Errorf(
			"component '%s' CPU request (%s) cannot exceed limit (%s)",
			comp.ComponentName,
			comp.Request.CPU.String(),
			comp.Limit.CPU.String(),
		)
	}
	if comp.Request.Memory.Cmp(comp.Limit.Memory) > 0 {
		return fmt.Errorf(
			"component '%s' memory request (%s) cannot exceed limit (%s)",
			comp.ComponentName,
			comp.Request.Memory.String(),
			comp.Limit.Memory.String(),
		)
	}
	return nil
}
