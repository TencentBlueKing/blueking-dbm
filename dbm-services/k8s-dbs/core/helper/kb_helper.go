/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License");
 * you may not use this file except in compliance with the License.
 *
 * You may obtain a copy of the License at
 * https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package helper

import (
	"context"
	"fmt"
	commhelper "k8s-dbs/common/helper"
	commtypes "k8s-dbs/common/types"
	"k8s-dbs/core/constant"
	"k8s-dbs/core/entity"
	"log/slog"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	corev1 "k8s.io/api/core/v1"

	"k8s.io/apimachinery/pkg/api/resource"

	"k8s.io/apimachinery/pkg/labels"

	"github.com/imdario/mergo"
	"helm.sh/helm/v3/pkg/action"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/util/yaml"
)

// minStorageForSC 定义各存储类(StorageClass)允许的最小存储配额
// key: 存储类名称
// value: 存储容量字符串，单位建议使用二进制单位（Gi）
var minStorageForSC = map[string]resource.Quantity{
	"cbs": resource.MustParse("20Gi"),
}

// maxStorageForSC 定义各存储类(StorageClass)允许的最大存储配额
// key: 存储类名称
// value: 存储容量字符串，单位建议使用二进制单位（Gi）
var maxStorageForSC = map[string]resource.Quantity{
	"cbs": resource.MustParse("100000Gi"),
}

// CreateCRD create crd by k8sClient client
func CreateCRD(k8sClient *commhelper.K8sClient, crd *entity.CustomResourceDefinition) error {
	if crd == nil {
		return fmt.Errorf("CustomResourceDefinition can't be nil when creating resource")
	}
	if _, exists := constant.ResourceInGlobal[crd.ResourceType]; exists {
		_, err := k8sClient.DynamicClient.
			Resource(crd.GroupVersionResource).
			Create(context.TODO(), crd.ResourceObject, metav1.CreateOptions{})
		if err != nil {
			return err
		}
	} else {
		_, err := k8sClient.DynamicClient.
			Resource(crd.GroupVersionResource).
			Namespace(crd.Namespace).
			Create(context.TODO(), crd.ResourceObject, metav1.CreateOptions{})
		if err != nil {
			return err
		}
	}
	return nil
}

// DeleteCRD delete crd by k8sClient client
func DeleteCRD(k8sClient *commhelper.K8sClient, crd *entity.CustomResourceDefinition) error {
	if crd == nil {
		return fmt.Errorf("CustomResourceDefinition can't be nil when deleting resource")
	}
	if _, exists := constant.ResourceInGlobal[crd.ResourceType]; exists {
		err := k8sClient.DynamicClient.
			Resource(crd.GroupVersionResource).
			Delete(context.TODO(), crd.ResourceName, metav1.DeleteOptions{})
		if err != nil {
			return err
		}
	} else {
		err := k8sClient.DynamicClient.
			Resource(crd.GroupVersionResource).
			Namespace(crd.Namespace).
			Delete(context.TODO(), crd.ResourceName, metav1.DeleteOptions{})
		if err != nil {
			return err
		}
	}
	return nil
}

// GetCRD get crd by k8sClient client
func GetCRD(k8sClient *commhelper.K8sClient, crd *entity.CustomResourceDefinition) (*unstructured.Unstructured, error) {
	if crd == nil {
		return nil, fmt.Errorf("CustomResourceDefinition can't be nil when getting resource")
	}
	var unstructuredObj *unstructured.Unstructured
	var err error
	if _, exists := constant.ResourceInGlobal[crd.ResourceType]; exists {
		unstructuredObj, err = k8sClient.DynamicClient.
			Resource(crd.GroupVersionResource).
			Get(context.TODO(), crd.ResourceName, metav1.GetOptions{})
		if err != nil {
			return nil, err
		}
	} else {
		unstructuredObj, err = k8sClient.DynamicClient.
			Resource(crd.GroupVersionResource).
			Namespace(crd.Namespace).
			Get(context.TODO(), crd.ResourceName, metav1.GetOptions{})
		if err != nil {
			return nil, err
		}
	}
	return unstructuredObj, nil
}

// ListCRD 获取 crd 资源列表
func ListCRD(
	k8sClient *commhelper.K8sClient,
	crd *entity.CustomResourceDefinition,
) (*unstructured.UnstructuredList, error) {
	if crd == nil {
		return nil, fmt.Errorf("CustomResourceDefinition can't be nil when listing resources")
	}

	listOptions := metav1.ListOptions{}

	if len(crd.Labels) > 0 {
		labelSelector := labels.Set(crd.Labels).AsSelector()
		listOptions.LabelSelector = labelSelector.String()
	}

	var list *unstructured.UnstructuredList
	var err error

	if _, exists := constant.ResourceInGlobal[crd.ResourceType]; exists {
		list, err = k8sClient.DynamicClient.
			Resource(crd.GroupVersionResource).
			List(context.TODO(), listOptions)
	} else {
		list, err = k8sClient.DynamicClient.
			Resource(crd.GroupVersionResource).
			Namespace(crd.Namespace).
			List(context.TODO(), listOptions)
	}

	if err != nil {
		return nil, fmt.Errorf("failed to list resources: %v", err)
	}

	return list, nil
}

// CheckStorageAddonIsCreated 检查 addon 是否已安装
func CheckStorageAddonIsCreated(k8sClient *commhelper.K8sClient, targetChartFullName string) (bool, error) {
	// init helm client
	actionConfig, err := k8sClient.BuildHelmConfig(constant.AddonDefaultNamespace)
	if err != nil {
		return false, err
	}

	// check chart if exist
	listAction := action.NewList(actionConfig)
	releases, err := listAction.Run()
	if err != nil {
		return false, err
	}

	for _, release := range releases {
		chartName := release.Chart.Metadata.Name
		chartVersion := release.Chart.Metadata.Version
		chartFullName := chartName + "-" + chartVersion

		if chartFullName == targetChartFullName {
			return true, nil
		}
	}
	return false, nil
}

// DeleteStorageAddonCluster helm uninstall storage addon cluster
func DeleteStorageAddonCluster(k8sClient *commhelper.K8sClient, clusterName, namespace string) error {

	// init helm client
	actionConfig, err := k8sClient.BuildHelmConfig(namespace)
	if err != nil {
		return err
	}

	// uninstall helm chart
	uninstall := action.NewUninstall(actionConfig)
	_, err = uninstall.Run(clusterName)
	if err != nil {
		return err
	}

	return nil
}

// ReadValuesYaml 读取 values.yaml 文件并解析为 map[string]interface{}
func ReadValuesYaml(chartPath string) (map[string]interface{}, error) {
	valuesPath := filepath.Join(chartPath, "values.yaml")
	data, err := os.ReadFile(valuesPath)
	if err != nil {
		return nil, err
	}

	var values map[string]interface{}
	err = yaml.Unmarshal(data, &values)
	if err != nil {
		return nil, err
	}

	return values, nil
}

// MergeValues 将 request 中的参数合并到 values 映射中
func MergeValues(values map[string]interface{}, request *entity.Request) error {
	err := mergeMetaData(values, request)
	if err != nil {
		return err
	}

	err = mergeComponentList(values, request.ComponentList)
	if err != nil {
		return err
	}

	err = mergeDependencies(values, request.Dependencies)
	if err != nil {
		return err
	}

	err = mergeObserveConfig(values, request.ObserveConfig)
	if err != nil {
		return err
	}

	return nil
}

func mergeMetaData(values map[string]interface{}, request *entity.Request) error {
	setIfNotEmpty := func(key string, value string) {
		if value != "" {
			values[key] = value
		}
	}
	setIfNotEmpty("addonVersion", request.StorageAddonVersion)
	setIfNotEmpty("clusterName", request.ClusterName)
	setIfNotEmpty("namespace", request.Namespace)
	setIfNotEmpty("topoName", request.TopoName)
	setIfNotEmpty("terminationPolicy", request.TerminationPolicy)

	metaDataMap := map[string]interface{}{
		"labels":      request.Labels,
		"annotations": request.Annotations,
	}
	for configKey, depPtr := range metaDataMap {
		err := MergeObjectToVal(values, depPtr, configKey)
		if err != nil {
			return err
		}
	}
	return nil
}

func mergeComponentList(values map[string]interface{}, compListFromReq []entity.ComponentResource) error {
	if compListFromReq == nil {
		return nil
	}
	compListFromVal, _ := values["componentList"].([]interface{})
	for _, compFromReq := range compListFromReq {
		for i, itemFromVal := range compListFromVal {
			compFromVal, ok := itemFromVal.(map[string]interface{})
			if ok && compFromVal["componentName"] == compFromReq.ComponentName {
				if compFromReq.Version != "" {
					compFromVal["serviceVersion"] = compFromReq.Version
				}
				if compFromReq.Replicas != 0 {
					compFromVal["replicas"] = int(compFromReq.Replicas)
				}
				if err := mergeResources(compFromVal, compFromReq); err != nil {
					slog.Error("failed to merge component Resources", "err", err)
					return err
				}
				if err := checkStorageByComp(&compFromReq); err != nil {
					slog.Error("failed to check storage by SC", "err", err)
					return err
				}
				if err := MergeObjectToVal(compFromVal, compFromReq.VolumeClaimTemplates, "volumeClaimTemplates"); err != nil {
					slog.Error("failed to merge volume claim templates", "err", err)
					return err
				}
				if err := mergeExtraArgs(compFromReq); err != nil {
					slog.Error("failed to merge extra args", "err", err)
					return err
				}
				if err := MergeObjectToVal(compFromVal, compFromReq.Env, "env"); err != nil {
					slog.Error("failed to merge env", "err", err)
					return err
				}

				if err := MergeObjectToVal(compFromVal, compFromReq.InstanceUpdateStrategy, "instanceUpdateStrategy"); err != nil {
					slog.Error("failed to merge instance update strategy", "err", err)
					return err
				}
				compListFromVal[i] = compFromVal
			}
		}
	}
	values["componentList"] = compListFromVal
	return nil
}

func mergeExtraArgs(compFromReq entity.ComponentResource) error {
	// Extract EXTRA_ARGS and type assert
	extraArgsRaw, exists := compFromReq.Env["EXTRA_ARGS"]
	if exists {
		extraArgsMap, ok := extraArgsRaw.(map[string]interface{})
		if !ok {
			return fmt.Errorf("EXTRA_ARGS is not a valid key-value map")
		}
		sortedKeys := make([]string, 0, len(extraArgsMap))
		for k := range extraArgsMap {
			sortedKeys = append(sortedKeys, k)
		}
		sort.Strings(sortedKeys)
		args := make([]string, 0, len(extraArgsMap))
		for _, k := range sortedKeys {
			strValue := fmt.Sprintf("%v", extraArgsMap[k])
			args = append(args, fmt.Sprintf("--%s=%s", k, strValue))
		}
		joinedArgs := strings.Join(args, " ")
		compFromReq.Env["EXTRA_ARGS"] = joinedArgs

	}
	return nil
}

func mergeResources(compFromVal map[string]interface{}, compFromReq entity.ComponentResource) error {
	resources, resOk := compFromVal["resources"].(map[string]interface{})
	if !resOk {
		resources = make(map[string]interface{})
		compFromVal["resources"] = resources
	}
	if err := MergeObjectToVal(resources, compFromReq.Request, "requests"); err != nil {
		slog.Error("failed to merge requests", "err", err)
		return err
	}
	if err := MergeObjectToVal(resources, compFromReq.Limit, "limits"); err != nil {
		slog.Error("failed to merge limits", "err", err)
		return err
	}
	return nil
}

func mergeDependencies(values map[string]interface{}, dependencies *entity.Dependencies) error {
	if dependencies == nil {
		return nil
	}
	dependencyMap := map[string]interface{}{
		"externalS3":    dependencies.ExternalS3,
		"externalEtcd":  dependencies.ExternalEtcd,
		"externalKafka": dependencies.ExternalKafka,
	}
	for configKey, depPtr := range dependencyMap {
		err := MergeObjectToVal(values, depPtr, configKey)
		if err != nil {
			return err
		}
	}
	return nil
}

/*
mergeObserveConfig merges the observation configuration into the target map
Function:
- Merges the BkLogConfig and SvcMonitor configurations in the observeConfig object into values["observeConfig"]
- If the observeConfig key does not exist in the target map, an empty map will be automatically created
*/
func mergeObserveConfig(values map[string]interface{}, observeConfig *entity.ObserveConfig) error {
	if observeConfig == nil {
		return nil
	}
	observeConfigMap := map[string]interface{}{
		"bkLogConfig": observeConfig.BkLogConfig,
		"svcMonitor":  observeConfig.SvcMonitor,
	}
	observeConfigFromVal, ok := values["observeConfig"].(map[string]interface{})
	if !ok {
		observeConfigFromVal = make(map[string]interface{})
		values["observeConfig"] = observeConfigFromVal
	}
	for configKey, depPtr := range observeConfigMap {
		err := MergeObjectToVal(observeConfigFromVal, depPtr, configKey)
		if err != nil {
			return err
		}
	}
	return nil
}

// MergeObjectToVal merges a given object into the target values map under the specified key.
func MergeObjectToVal(values map[string]interface{}, object interface{}, objectName string) error {
	if object == nil || reflect.ValueOf(object).IsNil() {
		return nil
	}

	depData, err := ConvertToMap(object)
	if err != nil {
		return fmt.Errorf("convert %s to map failed: %w", objectName, err)
	}

	target := make(map[string]interface{})
	if existing, ok := values[objectName].(map[string]interface{}); ok {
		target = existing
	}

	if err := mergo.Map(&target, depData, mergo.WithOverride); err != nil {
		return fmt.Errorf("merge %s to values failed : %w", objectName, err)
	}

	values[objectName] = target

	return nil
}

// ConvertToMap recursively convert structures to maps
func ConvertToMap(s interface{}) (interface{}, error) {
	v := reflect.ValueOf(s)
	if v.Kind() == reflect.Ptr {
		if v.IsNil() {
			return nil, nil
		}
		v = v.Elem()
	}

	switch v.Kind() {
	case reflect.Struct:
		// Identify resource.Quantity types, Avoid access non-exported structure fields via reflection
		if q, ok := s.(resource.Quantity); ok {
			return (&q).String(), nil
		}
		out := make(map[string]interface{})
		t := v.Type()
		for i := 0; i < v.NumField(); i++ {
			field := t.Field(i)
			key := getJSONTagName(field)
			value := v.Field(i).Interface()

			nestedValue, err := ConvertToMap(value)
			if err != nil {
				return nil, err
			}
			out[key] = nestedValue
		}
		return out, nil
	default:
		return s, nil
	}
}

// Parse json tag (handle omitempty and nested fields)
func getJSONTagName(field reflect.StructField) string {
	tag := field.Tag.Get("json")
	// Use field name when no tag is given
	if tag == "" {
		return field.Name
	}
	// Handle tags such as "componentName,omitempty"
	if idx := strings.Index(tag, ","); idx != -1 {
		return tag[:idx]
	}
	return tag
}

func checkStorageByComp(comp *entity.ComponentResource) error {
	if comp.VolumeClaimTemplates == nil {
		return nil
	}
	storageClassName := comp.VolumeClaimTemplates.StorageClassName
	currentStorage := comp.VolumeClaimTemplates.Storage

	err := CheckStorageBySC(storageClassName, currentStorage)
	if err != nil {
		slog.Error("failed to check storage by sc", "storageClass", storageClassName, "err", err)
		return fmt.Errorf("storage validation failed by sc '%s' : %w", storageClassName, err)
	}

	return nil
}

// CheckStorageBySC 检查Storage是否符合对应的存储类的要求限制
func CheckStorageBySC(storageClassName string, currentStorage resource.Quantity) error {
	// Get storage class limit configuration
	minStorage, minExists := minStorageForSC[storageClassName]
	maxStorage, maxExists := maxStorageForSC[storageClassName]

	// If there is no limit, return the original value directly
	if !minExists && !maxExists {
		return nil
	}

	// Minimum value check
	if minExists && currentStorage.Cmp(minStorage) < 0 {
		slog.Error("Storage below minimum",
			"storageClass", storageClassName,
			"requested", currentStorage.String(),
			"minAllowed", minStorage.String(),
		)
		return fmt.Errorf(
			"requested storage %s is below minimum %s for class '%s'",
			currentStorage.String(),
			minStorage.String(),
			storageClassName,
		)
	}

	// Maximum value check
	if maxExists && currentStorage.Cmp(maxStorage) > 0 {
		slog.Error("Storage exceeds maximum",
			"storageClass", storageClassName,
			"requested", currentStorage.String(),
			"maxAllowed", maxStorage.String(),
		)
		return fmt.Errorf(
			"requested storage %s exceeds maximum %s for class '%s'",
			currentStorage.String(),
			maxStorage.String(),
			storageClassName,
		)
	}

	return nil
}

// GetComponentPods 获取组件实例列表
func GetComponentPods(
	addonType string,
	params *entity.ComponentQueryParams,
	k8sClient *commhelper.K8sClient,
) ([]*entity.Pod, error) {
	crd := &entity.CustomResourceDefinition{
		GroupVersionResource: kbtypes.PodGVR(),
		Namespace:            params.Namespace,
		Labels: map[string]string{
			constant.InstanceName:  params.ClusterName,
			constant.ComponentName: params.ComponentName,
		},
	}
	podList, err := ListCRD(k8sClient, crd)
	if err != nil {
		return nil, err
	}
	if len(podList.Items) == 0 {
		return []*entity.Pod{}, nil
	}
	pods, err := ExtractPodsInfo(addonType, params.K8sClusterName, k8sClient, podList)
	if err != nil {
		return nil, err
	}
	return pods, err
}

// ExtractPodsInfo 从 Pod 列表中提取 Pod 信息
func ExtractPodsInfo(
	addonType string,
	k8sClusterName string,
	k8sClient *commhelper.K8sClient,
	podList *unstructured.UnstructuredList,
) ([]*entity.Pod, error) {
	var pods []*entity.Pod
	for _, item := range podList.Items {
		pod, err := ConvertUnstructuredToPod(item)
		if err != nil {
			return nil, fmt.Errorf("failed to convert unstructured pod %s: %w", item.GetName(), err)
		}
		var resourceQuota *entity.PodResourceQuota
		var resourceUsage *entity.PodResourceUsage
		if pod.Status.Phase == corev1.PodRunning {
			// 获取资源配额
			resourceQuota, err = GetPodResourceQuota(k8sClient, pod)
			if err != nil {
				return nil, err
			}
			// 获取资源利用率
			resourceUsage, err = GetPodResourceUsage(addonType, k8sClusterName, k8sClient, pod, resourceQuota)
			if err != nil {
				// 这里新拉起 Pod 的时候，metric 会有延迟，需要进行兼容处理
				slog.Warn("failed to get pod resource usage", "namespace", pod.Namespace, "pod", pod.Name)
			}
		}
		pods = append(pods, &entity.Pod{
			PodName:       pod.Name,
			Status:        pod.Status.Phase,
			Node:          pod.Spec.NodeName,
			Role:          GetPodRole(pod),
			ResourceQuota: resourceQuota,
			ResourceUsage: resourceUsage,
			CreatedTime:   commtypes.JSONDatetime(pod.CreationTimestamp.Time),
		})
	}

	return pods, nil
}

// GetPodRole 从 Pod 的标签中提取角色信息
func GetPodRole(pod *corev1.Pod) string {
	if role, exists := pod.Labels["kubeblocks.io/role"]; exists {
		return role
	}
	return "" // 默认为空字符串
}
