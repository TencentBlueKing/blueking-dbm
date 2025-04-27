package entity

import (
	kbv1 "github.com/apecloud/kubeblocks/apis/apps/v1alpha1"
	opv1 "github.com/apecloud/kubeblocks/apis/operations/v1alpha1"
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
	OpsRequestName      string            `json:"opsRequestName,omitempty"`
	Namespace           string            `json:"namespace,omitempty"`
	StorageAddonType    string            `json:"storageAddonType,omitempty"`
	StorageAddonVersion string            `json:"storageAddonVersion,omitempty"`
	Kind                string            `json:"kind,omitempty"`
	Labels              map[string]string `json:"labels,omitempty"`
	Annotations         map[string]string `json:"annotations,omitempty"`
}

// Spec Specific data
type Spec struct {
	Version                 string                       `json:"version,omitempty"`
	TopoName                string                       `json:"topoName,omitempty"`
	ComponentMap            map[string]ComponentResource `json:"componentMap,omitempty"`
	ComponentList           []ComponentResource          `json:"componentList,omitempty"`
	Dependencies            *Dependencies                `json:"dependencies,omitempty"`
	opv1.SpecificOpsRequest `json:",inline"`
	OpsService              `json:",inline"`
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
	ComponentName    string            `json:"componentName,omitempty"`
	ComponentDef     string            `json:"componentDef,omitempty"`
	Version          string            `json:"version,omitempty"`
	Replicas         int32             `json:"replicas,omitempty"`
	ExternalEndpoint ExternalEndpoint  `json:"externalEndpoint,omitempty"`
	Env              map[string]string `json:"env,omitempty"`
	Request          *Resource         `json:"request,omitempty"`
	Limit            *Resource         `json:"limit,omitempty"`
	Storage          string            `json:"storage,omitempty"`

	// Deleted in the future
	Connect *Connect `json:"connect,omitempty"`
}

// Resource the resource of component need
type Resource struct {
	Cpu    string `json:"cpu,omitempty"`
	Memory string `json:"memory,omitempty"`
}

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
		var user, password string
		for _, env := range componentSpec.Env {
			if env.Name == "SURREAL_USER" {
				user = env.Value
			} else if env.Name == "SURREAL_PASS" {
				password = env.Value
			}
		}
		if componentSpec.Services != nil {
			connect = &Connect{
				Host: data.Name + "-" + componentSpec.Services[0].Name + "." + data.Namespace + ".svc.cluster.local",
				Port: servicePortMap[componentSpec.Services[0].Name],
			}
		}
		if user != "" && password != "" {
			if connect == nil {
				connect = &Connect{}
			}
			connect.User = user
			connect.Password = password
		}

		var storage string
		if componentSpec.VolumeClaimTemplates != nil {
			storage = componentSpec.VolumeClaimTemplates[0].Spec.Resources.Requests.Storage().String()
		}

		componentResource := ComponentResource{
			ComponentName: componentSpec.Name,
			Version:       componentSpec.ServiceVersion,
			Replicas:      componentSpec.Replicas,
			Connect:       connect,
			Request: &Resource{
				Cpu:    componentSpec.Resources.Requests.Cpu().String(),
				Memory: componentSpec.Resources.Requests.Memory().String(),
			},
			Limit: &Resource{
				Cpu:    componentSpec.Resources.Limits.Cpu().String(),
				Memory: componentSpec.Resources.Limits.Memory().String(),
			},
			Storage: storage,
		}

		componentList = append(componentList, componentResource)
	}
	spec.ComponentList = componentList
	clusterData.Spec = spec
	return clusterData, nil
}
