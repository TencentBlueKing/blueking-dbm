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
	"fmt"
	commutil "k8s-dbs/common/util"
	coreconst "k8s-dbs/core/constant"
	"k8s-dbs/core/entity"
	metaenitty "k8s-dbs/metadata/entity"
	"log/slog"
	"strconv"
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
	"qdrant":    {"tcp-qdrant", "grpc-qdrant"},
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
	objectName := commutil.ResourceName("ops-vscaling-", OpsNameSuffixLength)
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
			Namespace: request.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.ClusterName,
			Type:                        coreconst.VerticalScaling,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: commutil.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              commutil.Int32Ptr(TimeoutSeconds),
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
		Namespace:            request.Namespace,
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
	objectName := commutil.ResourceName("ops-hs-", OpsNameSuffixLength)

	horizontalScaling := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: coreconst.APIVersion,
			Kind:       coreconst.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.ClusterName,
			Type:                        coreconst.HorizontalScaling,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: commutil.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              commutil.Int32Ptr(TimeoutSeconds),
			SpecificOpsRequest: opv1.SpecificOpsRequest{
				HorizontalScalingList: request.HorizontalScalingList,
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
		Namespace:            request.Namespace,
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
	objectName := commutil.ResourceName("ops-stop-", OpsNameSuffixLength)

	stop := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: coreconst.APIVersion,
			Kind:       coreconst.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.ClusterName,
			Type:                        coreconst.Stop,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: commutil.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              commutil.Int32Ptr(TimeoutSeconds),
			SpecificOpsRequest: opv1.SpecificOpsRequest{
				StopList: request.StopList,
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
		Namespace:            request.Namespace,
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
	objectName := commutil.ResourceName("ops-start-", OpsNameSuffixLength)

	start := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: coreconst.APIVersion,
			Kind:       coreconst.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.ClusterName,
			Type:                        coreconst.Start,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: commutil.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              commutil.Int32Ptr(TimeoutSeconds),
			SpecificOpsRequest: opv1.SpecificOpsRequest{
				StartList: request.StartList,
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
		Namespace:            request.Namespace,
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
	objectName := commutil.ResourceName("ops-restart-", OpsNameSuffixLength)

	restart := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: coreconst.APIVersion,
			Kind:       coreconst.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.ClusterName,
			Type:                        coreconst.Restart,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: commutil.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              commutil.Int32Ptr(TimeoutSeconds),
			SpecificOpsRequest: opv1.SpecificOpsRequest{
				RestartList: request.RestartList,
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
		Namespace:            request.Namespace,
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
	objectName := commutil.ResourceName("ops-upgrade-", OpsNameSuffixLength)
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
					ComponentDefinitionName: commutil.StringPtr(cmpdName),
					ServiceVersion:          compFromReq.Version,
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
			Namespace: request.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.ClusterName,
			Type:                        coreconst.Upgrade,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: commutil.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              commutil.Int32Ptr(TimeoutSeconds),
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
		Namespace:            request.Namespace,
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
	objectName := commutil.ResourceName("ops-vexpansion-", OpsNameSuffixLength)
	volumeExpansionList, err := CreateVolumeExpansionList(request, clusterObject)
	if err != nil {
		return nil, err
	}

	volumeExpansion := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: coreconst.APIVersion,
			Kind:       coreconst.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.ClusterName,
			Type:                        coreconst.VolumeExpansion,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: commutil.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              commutil.Int32Ptr(TimeoutSeconds),
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
		Namespace:            request.Namespace,
		ResourceType:         coreconst.VolumeExpansion,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateVolumeExpansionList 创建存储卷扩容对象列表
func CreateVolumeExpansionList(request *entity.Request, clusterObject *kbv1.Cluster) (
	[]opv1.VolumeExpansion, error,
) {
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

					err := CheckStorageBySC(*storageClassName, currentStorage)
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

	return volumeExpansionList, nil
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
	objectName := commutil.ResourceName("ops-expose-", OpsNameSuffixLength)
	// Convert selector key about kb
	podSelect := request.Service.PodSelect
	for key, value := range podSelect {
		if newKey, exists := coreconst.PodSelectLabel[key]; exists {
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
		Labels:               request.Labels,
		Namespace:            request.Namespace,
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
			Namespace: request.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.ClusterName,
			Type:                        coreconst.Expose,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: commutil.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              commutil.Int32Ptr(TimeoutSeconds),
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
				slog.Info("got ports",
					"Name", ports[i],
					"Port", request.Service.Ports[i],
					"TargetPort", intstr.FromString(ports[i]),
					"Protocol", protocol,
				)
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

// VM 私有常量：vmstorage 实例级 CLB 暴露的固定规则
const (
	// vmStorageComponent vmstorage 组件名
	vmStorageComponent = "vmstorage"
	// vmStorageCLBServiceInfix 实例 Service 名称中缀，OpsService.Name 为 clb-storage-{ordinal}。
	vmStorageCLBServiceInfix = "clb-storage"
	// vmStorageBasePort 实例 Service 对外端口基数，实际端口 8000 + ordinal
	vmStorageBasePort int32 = 8000
	// vmStorageTargetPort 固定 targetPort，对应 vmstorage 的 vmselect 访问端口
	vmStorageTargetPort int32 = 8401
	// vmStorageMaxPort 对外端口上限
	vmStorageMaxPort int32 = 65535
	// 共享 CLB 上 vminsert/vmselect 源 Service 已占用的监听端口
	vmInsertCLBPort int32 = 8480
	vmSelectCLBPort int32 = 8481
	// CLB ID 标注键
	vmCLBAnnotationKey        = "service.kubernetes.io/loadbalance-id"
	vmCLBExistedAnnotationKey = "service.kubernetes.io/tke-existed-lbid"
	vmCLBDirectAccessKey      = "service.cloud.tencent.com/direct-access"
)

// vmCLBIDAnnotationKeys CLB ID 标注键，按读取优先级排序
var vmCLBIDAnnotationKeys = []string{
	vmCLBExistedAnnotationKey,
	vmCLBAnnotationKey,
}

// VMStoragePod vmstorage Pod 引用，Pod 名必须可解析出唯一非负 ordinal
type VMStoragePod struct {
	PodName string
	Ordinal int
}

// ParseVMStorageOrdinal 从 vmstorage Pod 名解析唯一非负 ordinal
func ParseVMStorageOrdinal(podName, clusterName string) (int, error) {
	prefix := clusterName + "-" + vmStorageComponent + "-"
	if !strings.HasPrefix(podName, prefix) {
		return 0, fmt.Errorf("pod 名 %s 不符合 %s{ordinal} 命名规则", podName, prefix)
	}
	ordinal, err := strconv.Atoi(strings.TrimPrefix(podName, prefix))
	if err != nil || ordinal < 0 {
		return 0, fmt.Errorf("pod 名 %s 无法解析出唯一非负 ordinal", podName)
	}
	return ordinal, nil
}

// ExtractVMCLBID 按优先级从 annotations 提取 CLB ID；两个键同时存在且值不同时视为冲突，不允许猜测
func ExtractVMCLBID(annotations map[string]string) (string, error) {
	values := map[string]string{}
	for _, key := range vmCLBIDAnnotationKeys {
		if value, exists := annotations[key]; exists && value != "" {
			values[key] = value
		}
	}
	if len(values) > 1 {
		unique := make(map[string]struct{})
		for _, value := range values {
			unique[value] = struct{}{}
		}
		if len(unique) > 1 {
			return "", fmt.Errorf("CLB ID 标注冲突: %v", values)
		}
	}
	for _, key := range vmCLBIDAnnotationKeys {
		if value, exists := values[key]; exists {
			return value, nil
		}
	}
	return "", nil
}

// CreateVMExposeInstanceObject 构造 vmstorage 实例级暴露 OpsRequest（参考 CreateExposeClusterObject，
// 区别：一个 Expose 条目携带全部实例 Service，每个 Service 的 selector 精确到 Pod，
// OpsService.Name 为 clb-storage-{ordinal}
func CreateVMExposeInstanceObject(
	request *entity.VMExposeInstanceRequest,
	pods []VMStoragePod,
) (*entity.CustomResourceDefinition, error) {
	objectName := commutil.ResourceName("ops-expose-instance-", OpsNameSuffixLength)

	opsServices, err := createVMStorageOpsServices(request, pods)
	if err != nil {
		return nil, err
	}

	exposeSwitch := opv1.DisableExposeSwitch
	if request.Enable {
		exposeSwitch = opv1.EnableExposeSwitch
	}
	opsRequest := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: coreconst.APIVersion,
			Kind:       coreconst.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.ClusterName,
			Type:                        coreconst.Expose,
			TTLSecondsAfterSucceed:      TTLSecondsAfterSucceed,
			PreConditionDeadlineSeconds: commutil.Int32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              commutil.Int32Ptr(TimeoutSeconds),
			SpecificOpsRequest: opv1.SpecificOpsRequest{
				ExposeList: []opv1.Expose{
					{
						ComponentName: vmStorageComponent,
						Switch:        exposeSwitch,
						Services:      opsServices,
					},
				},
			},
		},
	}

	unstructuredOpsRequest, err := runtime.DefaultUnstructuredConverter.ToUnstructured(opsRequest)
	if err != nil {
		return nil, fmt.Errorf("转换 OpsRequest 为 Unstructured 类型失败: %v", err)
	}
	return &entity.CustomResourceDefinition{
		Labels:               opsRequest.Labels,
		Namespace:            request.Namespace,
		ResourceType:         coreconst.Expose,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject: &unstructured.Unstructured{
			Object: unstructuredOpsRequest,
		},
	}, nil
}

// createVMStorageOpsServices 构造各 vmstorage Pod 的独立 CLB Service 配置。
func createVMStorageOpsServices(
	request *entity.VMExposeInstanceRequest,
	pods []VMStoragePod,
) ([]opv1.OpsService, error) {
	var opsServices []opv1.OpsService
	for _, pod := range pods {
		port := vmStorageBasePort + int32(pod.Ordinal)
		if port > vmStorageMaxPort {
			return nil, fmt.Errorf("实例 %d 的对外端口 %d 超出上限 65535", pod.Ordinal, port)
		}
		if port == vmInsertCLBPort || port == vmSelectCLBPort {
			return nil, fmt.Errorf("实例 %d 的对外端口 %d 与共享 CLB 上 vminsert(%d)/vmselect(%d) 监听端口冲突",
				pod.Ordinal, port, vmInsertCLBPort, vmSelectCLBPort)
		}
		serviceName := fmt.Sprintf("%s-%d", vmStorageCLBServiceInfix, pod.Ordinal)
		opsServices = append(opsServices, opv1.OpsService{
			Name:        serviceName,
			ServiceType: corev1.ServiceTypeLoadBalancer,
			Annotations: map[string]string{
				vmCLBAnnotationKey:        request.LoadBalancerID,
				vmCLBExistedAnnotationKey: request.LoadBalancerID,
				vmCLBDirectAccessKey:      "true",
			},
			Ports: []corev1.ServicePort{
				{
					Name:       "http-port",
					Port:       port,
					Protocol:   corev1.ProtocolTCP,
					TargetPort: intstr.FromInt(int(vmStorageTargetPort)),
				},
			},
			PodSelector: map[string]string{
				coreconst.InstanceName:  request.ClusterName,
				coreconst.ManagedBy:     coreconst.Kubeblocks,
				coreconst.ComponentName: vmStorageComponent,
				coreconst.PodName:       pod.PodName,
			},
		})
	}

	return opsServices, nil
}

// UpdateValWithHScaling updates the release entity's chart values with horizontal scaling configurations.
func UpdateValWithHScaling(
	request *entity.Request,
	releaseEntity *metaenitty.AddonClusterReleaseEntity,
) (*metaenitty.AddonClusterReleaseEntity, error) {
	values, err := commutil.JSONStrToMap(releaseEntity.ChartValues)
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

	jsonStr, err := commutil.MapToJSONStr(values)
	if err != nil {
		return nil, err
	}
	releaseEntity.ChartValues = jsonStr
	releaseEntity.UpdatedBy = request.BkUserName
	return releaseEntity, nil
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
