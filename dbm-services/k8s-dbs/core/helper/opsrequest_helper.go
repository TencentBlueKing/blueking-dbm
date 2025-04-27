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
	utils2 "k8s-dbs/common/utils"
	"k8s-dbs/core/constant"
	entity2 "k8s-dbs/core/entity"
	provider2 "k8s-dbs/metadata/provider"
	models "k8s-dbs/metadata/provider/entity"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	kbv1 "github.com/apecloud/kubeblocks/apis/apps/v1alpha1"
	opv1 "github.com/apecloud/kubeblocks/apis/operations/v1alpha1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/util/intstr"
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
	"surreal": {"http"},
	"tikv":    {"peer", "status"},
	"pd":      {"client", "peer"},
	"attu":    {"attu"},
	"proxy":   {"milvus"},
	"minio":   {"console"},
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
func CreateVerticalScalingObject(request *entity2.Request) (*entity2.CustomResourceDefinition, error) {
	objectName := utils2.ResourceName("ops-vscaling-", OpsNameSuffixLength)

	verticalScaling := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: constant.APIVersion,
			Kind:       constant.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        constant.VerticalScaling,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: utils2.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              utils2.Int32Ptr(TimeoutSeconds),
			SpecificOpsRequest: opv1.SpecificOpsRequest{
				VerticalScalingList: request.Spec.VerticalScalingList,
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
	crd := &entity2.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         constant.VerticalScaling,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateHorizontalScalingObject 创建水平伸缩操作请求对象
// 参数和返回值同CreateVerticalScalingObject
func CreateHorizontalScalingObject(request *entity2.Request) (*entity2.CustomResourceDefinition, error) {
	objectName := utils2.ResourceName("ops-hs-", OpsNameSuffixLength)

	horizontalScaling := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: constant.APIVersion,
			Kind:       constant.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        constant.HorizontalScaling,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: utils2.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              utils2.Int32Ptr(TimeoutSeconds),
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
	crd := &entity2.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         constant.HorizontalScaling,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateStopClusterObject 创建停止集群操作请求对象
// 参数和返回值同CreateVerticalScalingObject
func CreateStopClusterObject(request *entity2.Request) (*entity2.CustomResourceDefinition, error) {
	objectName := utils2.ResourceName("ops-stop-", OpsNameSuffixLength)

	stop := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: constant.APIVersion,
			Kind:       constant.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        constant.Stop,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: utils2.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              utils2.Int32Ptr(TimeoutSeconds),
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
	crd := &entity2.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         constant.Stop,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateStartClusterObject 创建启动集群操作请求对象
// 参数和返回值同CreateVerticalScalingObject
func CreateStartClusterObject(request *entity2.Request) (*entity2.CustomResourceDefinition, error) {
	objectName := utils2.ResourceName("ops-start-", OpsNameSuffixLength)

	start := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: constant.APIVersion,
			Kind:       constant.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        constant.Start,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: utils2.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              utils2.Int32Ptr(TimeoutSeconds),
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
	crd := &entity2.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         constant.Start,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateRestartClusterObject 创建重启集群操作请求对象
// 参数和返回值同CreateVerticalScalingObject
func CreateRestartClusterObject(request *entity2.Request) (*entity2.CustomResourceDefinition, error) {
	objectName := utils2.ResourceName("ops-restart-", OpsNameSuffixLength)

	restart := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: constant.APIVersion,
			Kind:       constant.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        constant.Restart,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: utils2.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              utils2.Int32Ptr(TimeoutSeconds),
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
	crd := &entity2.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         constant.Restart,
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
func CreateUpgradeClusterObject(request *entity2.Request, clusterObject *kbv1.Cluster) (
	*entity2.CustomResourceDefinition, error,
) {
	objectName := utils2.ResourceName("ops-upgrade-", OpsNameSuffixLength)
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
					ComponentDefinitionName: utils2.StringPtr(cmpdName),
					ServiceVersion:          utils2.StringPtr(compFromReq.Version),
				})
			}
		}
	}

	upgrade := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: constant.APIVersion,
			Kind:       constant.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        constant.Upgrade,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: utils2.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              utils2.Int32Ptr(TimeoutSeconds),
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
	crd := &entity2.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         constant.Upgrade,
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
func CreateVolumeExpansionObject(request *entity2.Request, clusterObject *kbv1.Cluster) (
	*entity2.CustomResourceDefinition, error,
) {
	objectName := utils2.ResourceName("ops-vexpansion-", OpsNameSuffixLength)
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
					volumeClaimTemplates = append(volumeClaimTemplates, opv1.OpsRequestVolumeClaimTemplate{
						Name:    vct.Name,
						Storage: resource.MustParse(compFromReq.Storage),
					})
				}
				volumeExpansion.VolumeClaimTemplates = volumeClaimTemplates
			}
		}
		volumeExpansionList = append(volumeExpansionList, volumeExpansion)
	}

	volumeExpansion := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: constant.APIVersion,
			Kind:       constant.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        constant.VolumeExpansion,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: utils2.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              utils2.Int32Ptr(TimeoutSeconds),
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
	crd := &entity2.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         constant.VolumeExpansion,
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
func CreateExposeClusterObject(request *entity2.Request) (*entity2.CustomResourceDefinition, error) {
	objectName := utils2.ResourceName("ops-expose-", OpsNameSuffixLength)

	service := opv1.OpsService{
		Name:         request.Service.Name,
		ServiceType:  request.Service.ServiceType,
		Annotations:  request.Service.Annotations,
		Ports:        []corev1.ServicePort{},
		RoleSelector: request.Service.RoleSelector,
	}

	if ports, exists := componentTargetPortsMap[request.ComponentName]; exists {
		for i := 0; i < len(ports) && i < len(request.Service.Ports); i++ {
			service.Ports = append(service.Ports, corev1.ServicePort{
				Name:       ports[i],
				Port:       request.Service.Ports[i],
				TargetPort: intstr.FromString(ports[i]),
				Protocol:   corev1.ProtocolTCP,
			})
		}
	}

	ExposeObject := opv1.Expose{
		ComponentName: request.ComponentName,
		Switch:        switchTypeMap[request.Enable],
		Services:      []opv1.OpsService{service},
	}

	expose := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: constant.APIVersion,
			Kind:       constant.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        constant.Expose,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: utils2.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              utils2.Int32Ptr(TimeoutSeconds),
			SpecificOpsRequest: opv1.SpecificOpsRequest{
				ExposeList: []opv1.Expose{
					ExposeObject,
				},
			},
		},
	}

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&expose)
	if err != nil {
		return nil, fmt.Errorf("转换对象为Unstructured类型失败: %v", err)
	}

	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}
	crd := &entity2.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         constant.Expose,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateOpsRequestMetaData 构建 opsRequest 元数据
func CreateOpsRequestMetaData(
	opsRequestProvider provider2.K8sCrdOpsRequestProvider,
	crdClusterProvider provider2.K8sCrdClusterProvider,
	request *entity2.Request,
	crd *entity2.CustomResourceDefinition,
) error {
	opsReqEntity, err := getEntityFromReq(crd)
	if err != nil {
		return err
	}
	params := map[string]interface{}{
		"cluster_name": request.ClusterName,
		"namespace":    request.Namespace,
	}
	clusterEntity, err := crdClusterProvider.FindByParams(params)
	if err != nil {
		return err
	}
	opsReqEntity.CrdClusterID = clusterEntity.ID
	_, err = opsRequestProvider.CreateOpsRequest(opsReqEntity)
	if err != nil {
		return err
	}
	return nil
}

// getEntityFromReq 解析 request 构建 K8sCrdOpsRequestEntity
func getEntityFromReq(crd *entity2.CustomResourceDefinition) (*models.K8sCrdOpsRequestEntity, error) {
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

	opsReqEntity := &models.K8sCrdOpsRequestEntity{
		OpsRequestName: opsRequestObject.Name,
		OpsRequestType: crd.ResourceType,
		Metadata:       string(metaDataJSON),
		Spec:           string(specJSON),
	}
	return opsReqEntity, nil
}
