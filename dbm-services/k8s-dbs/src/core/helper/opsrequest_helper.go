package helper

import (
	"encoding/json"
	"fmt"
	constants "k8s-dbs/src/core/constant"
	"k8s-dbs/src/core/entity"
	"k8s-dbs/src/metadata/provider"
	models "k8s-dbs/src/metadata/provider/entity"

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

// opsrequest
const (
	TTLSecondsAfterSucceed      = 600
	PreConditionDeadlineSeconds = 10
	TimeoutSeconds              = 600
)

// Define global variables to query targetPorts in component
// When initializing the addon, update this map. Currently, fill it in directly
var componentTargetPortsMap = map[string][]string{
	"surreal": {"http"},
	"tikv":    {"peer", "status"},
	"pd":      {"client", "peer"},
	"attu":    {"attu"},
	"proxy":   {"milvus"},
	"minio":   {"console"},
}

var switchTypeMap = map[bool]opv1.ExposeSwitch{
	true:  opv1.EnableExposeSwitch,
	false: opv1.DisableExposeSwitch,
}

// CreateVerticalScalingObject Create VerticalScaling Object
func CreateVerticalScalingObject(request *entity.Request) (*entity.CustomResourceDefinition, error) {
	objectName := entity.AppendRandomSuffix("ops-vscaling-", 10)

	verticalScaling := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: constants.ApiVersion,
			Kind:       constants.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        constants.VerticalScaling,
			TTLSecondsAfterSucceed:      int32(TTLSecondsAfterSucceed),
			PreConditionDeadlineSeconds: entity.IntToInt32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              entity.IntToInt32Ptr(TimeoutSeconds),
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
	crd := &entity.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         constants.VerticalScaling,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateHorizontalScalingObject Create HorizontalScaling Object
func CreateHorizontalScalingObject(request *entity.Request) (*entity.CustomResourceDefinition, error) {
	objectName := entity.AppendRandomSuffix("ops-hs-", 10)

	horizontalScaling := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: constants.ApiVersion,
			Kind:       constants.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        constants.HorizontalScaling,
			TTLSecondsAfterSucceed:      int32(TTLSecondsAfterSucceed),
			PreConditionDeadlineSeconds: entity.IntToInt32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              entity.IntToInt32Ptr(TimeoutSeconds),
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
		ResourceType:         constants.HorizontalScaling,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateStopClusterObject Create StopCluster Object
func CreateStopClusterObject(request *entity.Request) (*entity.CustomResourceDefinition, error) {
	objectName := entity.AppendRandomSuffix("ops-stop-", 10)

	stop := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: constants.ApiVersion,
			Kind:       constants.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        constants.Stop,
			TTLSecondsAfterSucceed:      int32(TTLSecondsAfterSucceed),
			PreConditionDeadlineSeconds: entity.IntToInt32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              entity.IntToInt32Ptr(TimeoutSeconds),
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
		ResourceType:         constants.Stop,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateStartClusterObject Create StartCluster Object
func CreateStartClusterObject(request *entity.Request) (*entity.CustomResourceDefinition, error) {
	objectName := entity.AppendRandomSuffix("ops-start-", 10)

	start := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: constants.ApiVersion,
			Kind:       constants.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        constants.Start,
			TTLSecondsAfterSucceed:      int32(TTLSecondsAfterSucceed),
			PreConditionDeadlineSeconds: entity.IntToInt32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              entity.IntToInt32Ptr(TimeoutSeconds),
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
		ResourceType:         constants.Start,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateRestartClusterObject Create RestartCluster Object
func CreateRestartClusterObject(request *entity.Request) (*entity.CustomResourceDefinition, error) {
	objectName := entity.AppendRandomSuffix("ops-restart-", 10)

	restart := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: constants.ApiVersion,
			Kind:       constants.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        constants.Restart,
			TTLSecondsAfterSucceed:      int32(TTLSecondsAfterSucceed),
			PreConditionDeadlineSeconds: entity.IntToInt32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              entity.IntToInt32Ptr(TimeoutSeconds),
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
		ResourceType:         constants.Restart,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateUpgradeClusterObject Create UpgradeCluster Object
func CreateUpgradeClusterObject(request *entity.Request, clusterObject *kbv1.Cluster) (*entity.CustomResourceDefinition, error) {
	objectName := entity.AppendRandomSuffix("ops-upgrade-", 10)
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
					ComponentDefinitionName: entity.StringToPointer(cmpdName),
					ServiceVersion:          entity.StringToPointer(compFromReq.Version),
				})
			}
		}
	}

	upgrade := &opv1.OpsRequest{
		TypeMeta: metav1.TypeMeta{
			APIVersion: constants.ApiVersion,
			Kind:       constants.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        constants.Upgrade,
			TTLSecondsAfterSucceed:      int32(TTLSecondsAfterSucceed),
			PreConditionDeadlineSeconds: entity.IntToInt32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              entity.IntToInt32Ptr(TimeoutSeconds),
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
		ResourceType:         constants.Upgrade,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateVolumeExpansionObject Create VolumeExpansion Object
func CreateVolumeExpansionObject(request *entity.Request, clusterObject *kbv1.Cluster) (*entity.CustomResourceDefinition, error) {
	objectName := entity.AppendRandomSuffix("ops-vexpansion-", 10)
	var volumeExpansionList []opv1.VolumeExpansion
	for _, compFromReq := range request.ComponentList {
		//get component names
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
			APIVersion: constants.ApiVersion,
			Kind:       constants.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        constants.VolumeExpansion,
			TTLSecondsAfterSucceed:      int32(TTLSecondsAfterSucceed),
			PreConditionDeadlineSeconds: entity.IntToInt32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              entity.IntToInt32Ptr(TimeoutSeconds),
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
		ResourceType:         constants.VolumeExpansion,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateExposeClusterObject CreateRestartClusterObject Create RestartCluster Object
func CreateExposeClusterObject(request *entity.Request) (*entity.CustomResourceDefinition, error) {
	objectName := entity.AppendRandomSuffix("ops-expose-", 10)

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
			APIVersion: constants.ApiVersion,
			Kind:       constants.OpsRequest,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      objectName,
			Namespace: request.Metadata.Namespace,
		},
		Spec: opv1.OpsRequestSpec{
			ClusterName:                 request.Metadata.ClusterName,
			Type:                        constants.Expose,
			TTLSecondsAfterSucceed:      int32(TTLSecondsAfterSucceed),
			PreConditionDeadlineSeconds: entity.IntToInt32Ptr(PreConditionDeadlineSeconds),
			TimeoutSeconds:              entity.IntToInt32Ptr(TimeoutSeconds),
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
	crd := &entity.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         constants.Expose,
		ResourceName:         objectName,
		GroupVersionResource: kbtypes.OpsGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

func CreateOpsRequestMetaData(opsRequestProvider provider.K8sCrdOpsRequestProvider, crdClusterProvider provider.K8sCrdClusterProvider, request *entity.Request, crd *entity.CustomResourceDefinition) error {
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

func getEntityFromReq(crd *entity.CustomResourceDefinition) (*models.K8sCrdOpsRequestEntity, error) {
	var opsRequestObject opv1.OpsRequest
	err := runtime.DefaultUnstructuredConverter.FromUnstructured(crd.ResourceObject.Object, &opsRequestObject)
	if err != nil {
		return nil, err
	}

	metaDataJSON, err := json.Marshal(opsRequestObject.ObjectMeta)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal metaData to JSON: %w", err)
	}
	specJson, err := json.Marshal(opsRequestObject.Spec)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal spec to JSON: %w", err)
	}

	opsReqEntity := &models.K8sCrdOpsRequestEntity{
		OpsRequestName: opsRequestObject.Name,
		OpsRequestType: crd.ResourceType,
		Metadata:       string(metaDataJSON),
		Spec:           string(specJson),
	}
	return opsReqEntity, nil
}
