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

package entity

import (
	kbv1 "github.com/apecloud/kubeblocks/apis/apps/v1alpha1"
	opv1 "github.com/apecloud/kubeblocks/apis/operations/v1alpha1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
)

// ClusterResponseData cluster Response Data
type ClusterResponseData struct {
	Metadata      Metadata       `json:"metadata,omitempty"`
	Spec          Spec           `json:"spec,omitempty"`
	ClusterStatus *ClusterStatus `json:"status,omitempty"`
}

// Metadata the metadata of request and response
type Metadata struct {
	ClusterName         string            `json:"clusterName,omitempty"`
	ClusterAlias        string            `json:"clusterAlias,omitempty"`
	ComponentName       string            `json:"componentName,omitempty"`
	OpsRequestName      string            `json:"opsRequestName,omitempty"`
	Namespace           string            `json:"namespace,omitempty"`
	StorageAddonType    string            `json:"storageAddonType,omitempty"`
	StorageAddonVersion string            `json:"storageAddonVersion,omitempty"`
	AddonClusterVersion string            `json:"addonClusterVersion,omitempty"`
	Kind                string            `json:"kind,omitempty"`
	Labels              map[string]string `json:"labels,omitempty"`
	Annotations         map[string]string `json:"annotations,omitempty"`
}

// Spec Specific data
type Spec struct {
	Version                 string                       `json:"version,omitempty"`
	TopoName                string                       `json:"topoName,omitempty"`
	TerminationPolicy       string                       `json:"terminationPolicy,omitempty"`
	ComponentMap            map[string]ComponentResource `json:"componentMap,omitempty"`
	ComponentList           []ComponentResource          `json:"componentList,omitempty"`
	Dependencies            *Dependencies                `json:"dependencies,omitempty"`
	opv1.SpecificOpsRequest `json:",inline"`
	OpsService              `json:",inline"`
	ObserveConfig           *ObserveConfig `json:"observeConfig,omitempty"`
}

// ClusterStatus cluster status
type ClusterStatus struct {
	Phase      kbv1.ClusterPhase  `json:"phase,omitempty"`
	CreateTime metav1.Time        `json:"createTime,omitempty"`
	UpdateTime metav1.Time        `json:"updateTime,omitempty"`
	Messages   []metav1.Condition `json:"messages,omitempty"`
}

// Connect connect info
type Connect struct {
	Host     string `json:"host,omitempty"`
	Port     int32  `json:"port,omitempty"`
	User     string `json:"user,omitempty"`
	Password string `json:"password,omitempty"`
}

// ComponentResource component info
type ComponentResource struct {
	// Current request
	ComponentName          string                  `json:"componentName,omitempty"`
	ComponentDef           string                  `json:"componentDef,omitempty"`
	Version                string                  `json:"version,omitempty"`
	Replicas               int32                   `json:"replicas,omitempty"`
	Env                    map[string]interface{}  `json:"env,omitempty"`
	Request                *Resource               `json:"request,omitempty"`
	Limit                  *Resource               `json:"limit,omitempty"`
	VolumeClaimTemplates   *VolumeClaimTemplates   `json:"volumeClaimTemplates,omitempty"`
	InstanceUpdateStrategy *InstanceUpdateStrategy `json:"instanceUpdateStrategy,omitempty"`

	// Deleted in the future
	Storage resource.Quantity `json:"storage,omitempty"`
	Connect *Connect          `json:"connect,omitempty"`
}

// VolumeClaimTemplates defines persistent storage requirements for Component pods.
// Equivalent to Kubernetes cluster.spec.volumeClaimTemplates field.
type VolumeClaimTemplates struct {
	AccessModes      []string          `json:"accessModes,omitempty"`
	Storage          resource.Quantity `json:"storage,omitempty"`
	StorageClassName string            `json:"storageClassName,omitempty"`
	VolumeMode       string            `json:"volumeMode,omitempty"`
}

// InstanceUpdateStrategy Provides fine-grained control over the spec update process of all instances.
type InstanceUpdateStrategy struct {
	MaxUnavailable string `json:"maxUnavailable,omitempty"`
}

// GetClusterResponseData 获取 cluster 集群详情
func GetClusterResponseData(cluster *unstructured.Unstructured) (*ClusterResponseData, error) {
	var data *kbv1.Cluster
	err := runtime.DefaultUnstructuredConverter.FromUnstructured(cluster.Object, &data)
	if err != nil {
		return nil, err
	}
	clusterData := &ClusterResponseData{
		Metadata: Metadata{
			ClusterName: data.Name,
			Namespace:   data.Namespace,
			Kind:        data.Kind,
			Labels:      data.Labels,
			Annotations: data.Annotations,
		},
		ClusterStatus: &ClusterStatus{
			Phase:      data.Status.Phase,
			CreateTime: data.CreationTimestamp,
			UpdateTime: *data.ManagedFields[0].Time,
			Messages:   data.Status.Conditions,
		},
	}

	spec := Spec{
		//Version: data.Spec.ComponentSpecs[0].ServiceVersion,
	}

	// get src
	servicePortMap := make(map[string]int32)
	for _, service := range data.Spec.Services {
		servicePortMap[service.Name] = service.Spec.Ports[0].Port
	}

	var componentList []ComponentResource
	for _, componentSpec := range data.Spec.ComponentSpecs {

		var connect *Connect
		if componentSpec.Services != nil {
			connect = &Connect{
				Host: data.Name + "-" + componentSpec.Services[0].Name + "." + data.Namespace + ".svc.cluster.local",
				Port: servicePortMap[componentSpec.Services[0].Name],
			}
		}

		var storage resource.Quantity
		if componentSpec.VolumeClaimTemplates != nil {
			storage = *componentSpec.VolumeClaimTemplates[0].Spec.Resources.Requests.Storage()
		}

		componentResource := ComponentResource{
			ComponentName: componentSpec.Name,
			Version:       componentSpec.ServiceVersion,
			Replicas:      componentSpec.Replicas,
			Connect:       connect,
			Request: &Resource{
				CPU:    *componentSpec.Resources.Requests.Cpu(),
				Memory: *componentSpec.Resources.Requests.Memory(),
			},
			Limit: &Resource{
				CPU:    *componentSpec.Resources.Limits.Cpu(),
				Memory: *componentSpec.Resources.Limits.Memory(),
			},
			Storage: storage,
		}

		componentList = append(componentList, componentResource)
	}
	spec.ComponentList = componentList
	clusterData.Spec = spec
	return clusterData, nil
}
