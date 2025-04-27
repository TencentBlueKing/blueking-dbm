package victoriametrics

import (
	"context"
	"fmt"
	"k8s-dbs/src/core/client"
	commonConst "k8s-dbs/src/core/constant"
	"k8s-dbs/src/core/engine/victoriametrics/constant"
	engineConst "k8s-dbs/src/core/engine/victoriametrics/constant"
	"k8s-dbs/src/core/entity"
	"log"
	"strings"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	kbv1 "github.com/apecloud/kubeblocks/apis/apps/v1alpha1"
	"github.com/gin-gonic/gin"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/util/intstr"
)

// Victoriametrics the Victoriametrics src structure.
type Victoriametrics struct {
	vminsert  *entity.ComponentResource
	vmselect  *entity.ComponentResource
	vmstorage *entity.ComponentResource
}

// NewVictoriametrics creates a new instance of the victoriametrics struct
func NewVictoriametrics() *Victoriametrics {
	return &Victoriametrics{}
}

// CreateCluster creates a new Victoriametrics cluster.
func (v *Victoriametrics) CreateCluster(k8sClient *client.K8sClient, ctx *gin.Context, request *entity.Request) (*entity.ClusterResponseData, error) {
	// create componentVersion if it is not already exists
	cmpv, err := v.CreateCmpvObject(ctx, request)
	if err != nil {
		return nil, err
	}
	err = client.CreateCRD(k8sClient, cmpv)
	if err = skipIfAlreadyExists(err); err != nil {
		return nil, err
	}

	// Create cmpd for Insert,Select,Storage if they are not already exists
	vminsert, err := v.CreateCmpdInsert(ctx, request)
	if err != nil {
		return nil, err
	}
	err = client.CreateCRD(k8sClient, vminsert)
	if err = skipIfAlreadyExists(err); err != nil {
		return nil, err
	}

	vmselect, err := v.CreateCmpdSelect(ctx, request)
	if err != nil {
		return nil, err
	}
	err = client.CreateCRD(k8sClient, vmselect)
	if err = skipIfAlreadyExists(err); err != nil {
		return nil, err
	}

	vmstorage, err := v.CreateCmpdStorage(ctx, request)
	if err != nil {
		return nil, err
	}
	err = client.CreateCRD(k8sClient, vmstorage)
	if err = skipIfAlreadyExists(err); err != nil {
		return nil, err
	}

	// create clusterDefinition if it is not already exists
	cd, err := v.CreateCdObject(ctx, request)
	if err != nil {
		return nil, err
	}
	err = client.CreateCRD(k8sClient, cd)
	if err = skipIfAlreadyExists(err); err != nil {
		return nil, err
	}

	cluster, err := v.CreateClusterObject(ctx, request)
	if err != nil {
		return nil, err
	}
	err = client.CreateCRD(k8sClient, cluster)
	if err != nil {
		return nil, err
	}
	return nil, nil
}

// DescribeCluster retrieves the details of a Victoriametrics cluster.
func (v *Victoriametrics) DescribeCluster(k8sClient *client.K8sClient, ctx *gin.Context, request *entity.Request) (*entity.ClusterResponseData, error) {
	clusterName := request.Metadata.ClusterName
	namespace := request.Metadata.Namespace
	gvr := kbtypes.ClusterGVR()

	cluster, err := k8sClient.DynamicClient.Resource(gvr).Namespace(namespace).Get(context.TODO(), clusterName, metav1.GetOptions{})
	if err != nil {
		return nil, err
	}

	dataResponse, err := entity.GetClusterResponseData(cluster)
	if err != nil {
		return nil, err
	}
	return dataResponse, nil
}

// DeleteCluster deletes a Victoriametrics cluster.
func (v *Victoriametrics) DeleteCluster(k8sClient *client.K8sClient, ctx *gin.Context, clusterData *entity.ClusterResponseData, request *entity.Request) error {
	cluster, err := v.CreateClusterObject(ctx, request)
	if err != nil {
		return err
	}
	err = client.DeleteCRD(k8sClient, cluster)
	if err != nil {
		return err
	}
	return nil
}

// CreateCdCmpdCmpv creates the cluster definition, component definition, and component version if they don't exist.
func (v *Victoriametrics) CreateCdCmpdCmpv(k8sClient *client.K8sClient, ctx *gin.Context, request *entity.Request) error {
	// create componentVersion if it is not already exists
	cmpv, err := v.CreateCmpvObject(ctx, request)
	if err != nil {
		return err
	}
	err = client.CreateCRD(k8sClient, cmpv)
	if err = skipIfAlreadyExists(err); err != nil {
		return err
	}

	// Create cmpd for Insert,Select,Storage if they are not already exists
	vminsert, err := v.CreateCmpdInsert(ctx, request)
	if err != nil {
		return err
	}
	err = client.CreateCRD(k8sClient, vminsert)
	if err = skipIfAlreadyExists(err); err != nil {
		return err
	}

	vmselect, err := v.CreateCmpdSelect(ctx, request)
	if err != nil {
		return err
	}
	err = client.CreateCRD(k8sClient, vmselect)
	if err = skipIfAlreadyExists(err); err != nil {
		return err
	}

	vmstorage, err := v.CreateCmpdStorage(ctx, request)
	if err != nil {
		return err
	}
	err = client.CreateCRD(k8sClient, vmstorage)
	if err = skipIfAlreadyExists(err); err != nil {
		return err
	}

	// create clusterDefinition if it is not already exists
	cd, err := v.CreateCdObject(ctx, request)
	if err != nil {
		return err
	}
	err = client.CreateCRD(k8sClient, cd)
	if err = skipIfAlreadyExists(err); err != nil {
		return err
	}
	return nil
}

// GetClusterStatus retrieves the status of a SurrealDB cluster.
func (v *Victoriametrics) GetClusterStatus(k8sClient *client.K8sClient, ctx *gin.Context, request *entity.Request) (*entity.ClusterStatus, error) {
	clusterName := request.Metadata.ClusterName
	namespace := request.Metadata.Namespace
	gvr := kbtypes.ClusterGVR()

	cluster, err := k8sClient.DynamicClient.Resource(gvr).Namespace(namespace).Get(context.TODO(), clusterName, metav1.GetOptions{})
	if err != nil {
		return nil, err
	}
	dataResponse, err := entity.GetClusterResponseData(cluster)
	if err != nil {
		return nil, err
	}
	return dataResponse.ClusterStatus, nil
}

// skipIfAlreadyExists checks if the error message contains "already exists".
func skipIfAlreadyExists(err error) error {
	if err == nil {
		return nil
	}
	if strings.Contains(err.Error(), "already exists") {
		return nil
	}
	return err
}

// CreateClusterObject creates a custom resource definition object for the Victoriametrics cluster.
func (v *Victoriametrics) CreateClusterObject(ctx *gin.Context, request *entity.Request) (*entity.CustomResourceDefinition, error) {
	serviceNameByInsert, err := entity.GetDefaultServiceName(v.vminsert.Connect.Host)
	if err != nil {
		return nil, err
	}
	serviceNameBySelect, err := entity.GetDefaultServiceName(v.vmselect.Connect.Host)
	if err != nil {
		return nil, err
	}
	serviceNameByStorage, err := entity.GetDefaultServiceName(v.vmstorage.Connect.Host)
	if err != nil {
		return nil, err
	}

	cluster := kbv1.Cluster{
		TypeMeta: metav1.TypeMeta{
			Kind:       commonConst.Cluster,
			APIVersion: commonConst.ApiVersion,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:        request.Metadata.ClusterName,
			Namespace:   request.Metadata.Namespace,
			Labels:      request.Metadata.Labels,
			Annotations: request.Metadata.Annotations,
		},
		Spec: kbv1.ClusterSpec{
			ClusterDefRef:     constant.ClusterDefinitionName + "-" + request.Spec.Version,
			Topology:          constant.ClusterTopologyName,
			TerminationPolicy: kbv1.Delete,
			ComponentSpecs: []kbv1.ClusterComponentSpec{
				{
					Name:           engineConst.CompTopoNameByStorage,
					Replicas:       v.vmstorage.Replicas,
					ServiceVersion: request.Spec.Version,
					Services: []kbv1.ClusterComponentService{
						{
							Name:       serviceNameByStorage,
							PodService: entity.GetTrue(),
						},
					},
					Resources: corev1.ResourceRequirements{
						Requests: corev1.ResourceList{
							"cpu":    resource.MustParse(v.vmstorage.Request.Cpu),
							"memory": resource.MustParse(v.vmstorage.Request.Memory),
						},
						Limits: corev1.ResourceList{
							"cpu":    resource.MustParse(v.vmstorage.Limit.Cpu),
							"memory": resource.MustParse(v.vmstorage.Limit.Memory),
						},
					},
					VolumeClaimTemplates: []kbv1.ClusterComponentVolumeClaimTemplate{
						{
							Name: engineConst.VolumeMountNameByStorage,
							Spec: kbv1.PersistentVolumeClaimSpec{
								AccessModes: []corev1.PersistentVolumeAccessMode{
									corev1.ReadWriteOnce,
								},
								Resources: corev1.VolumeResourceRequirements{
									Requests: corev1.ResourceList{
										"storage": resource.MustParse(v.vmstorage.Storage),
									},
								},
								StorageClassName: nil,
								VolumeMode: func() *corev1.PersistentVolumeMode {
									mode := corev1.PersistentVolumeFilesystem
									return &mode
								}(),
							},
						},
					},
				},
				{
					Name:           engineConst.CompTopoNameBySelect,
					Replicas:       v.vmselect.Replicas,
					ServiceVersion: request.Spec.Version,
					Services: []kbv1.ClusterComponentService{
						{
							Name: serviceNameBySelect,
						},
					},
					Resources: corev1.ResourceRequirements{
						Requests: corev1.ResourceList{
							"cpu":    resource.MustParse(v.vmselect.Request.Cpu),
							"memory": resource.MustParse(v.vmselect.Request.Memory),
						},
						Limits: corev1.ResourceList{
							"cpu":    resource.MustParse(v.vmselect.Limit.Cpu),
							"memory": resource.MustParse(v.vmselect.Limit.Memory),
						},
					},
				},
				{
					Name:           engineConst.CompTopoNameByInsert,
					Replicas:       v.vminsert.Replicas,
					ServiceVersion: request.Spec.Version,
					Services: []kbv1.ClusterComponentService{
						{
							Name: serviceNameByInsert,
						},
					},
					Resources: corev1.ResourceRequirements{
						Requests: corev1.ResourceList{
							"cpu":    resource.MustParse(v.vminsert.Request.Cpu),
							"memory": resource.MustParse(v.vminsert.Request.Memory),
						},
						Limits: corev1.ResourceList{
							"cpu":    resource.MustParse(v.vminsert.Limit.Cpu),
							"memory": resource.MustParse(v.vminsert.Limit.Memory),
						},
					},
				},
			},
			Services: []kbv1.ClusterService{
				{
					Service: kbv1.Service{
						Name:        serviceNameBySelect,
						ServiceName: serviceNameBySelect,
						Spec: corev1.ServiceSpec{
							Selector: map[string]string{
								"apps.kubeblocks.io/component-name": "vmselect",
							},
							Ports: []corev1.ServicePort{
								{
									Name:       "http",
									Port:       v.vmselect.Connect.Port,
									TargetPort: intstr.FromString("http"),
									Protocol:   corev1.ProtocolTCP,
								},
							},
						},
					},
				},
				{
					Service: kbv1.Service{
						Name:        serviceNameByInsert,
						ServiceName: serviceNameByInsert,
						Spec: corev1.ServiceSpec{
							Selector: map[string]string{
								"apps.kubeblocks.io/component-name": "vminsert",
							},
							Ports: []corev1.ServicePort{
								{
									Name:       "http",
									Port:       v.vminsert.Connect.Port,
									TargetPort: intstr.FromString("http"),
									Protocol:   corev1.ProtocolTCP,
								},
							},
						},
					},
				},
				{
					Service: kbv1.Service{
						Name:        serviceNameByStorage,
						ServiceName: serviceNameByStorage,
						Spec: corev1.ServiceSpec{
							Selector: map[string]string{
								"apps.kubeblocks.io/component-name": "vmstorage",
							},
							Ports: []corev1.ServicePort{
								{
									Name:       "http",
									Port:       v.vmstorage.Connect.Port,
									TargetPort: intstr.FromString("http"),
									Protocol:   corev1.ProtocolTCP,
								},
								//{
								//	Name:       "vmselect",
								//	Port:       8401,
								//	TargetPort: intstr.FromString("vmselect"),
								//	Protocol:   corev1.ProtocolTCP,
								//},
								//{
								//	Name:       "vminsert",
								//	Port:       8400,
								//	TargetPort: intstr.FromString("vminsert"),
								//	Protocol:   corev1.ProtocolTCP,
								//},
							},
						},
					},
				},
			},
		},
	}
	log.Printf("v.vmselect.Connect.Port: %d\n", v.vmselect.Connect.Port)

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&cluster)
	if err != nil {
		return nil, fmt.Errorf("转换对象为Unstructured类型失败: %v", err)
	}

	gvr := schema.GroupVersionResource{
		Group:    "apps.kubeblocks.io",
		Version:  "v1alpha1",
		Resource: "clusters",
	}
	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}
	crd := &entity.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         commonConst.Cluster,
		ResourceName:         request.Metadata.ClusterName,
		GroupVersionResource: gvr,
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateCdObject creates a custom resource definition object for the Victoriametrics cluster definition.
func (v *Victoriametrics) CreateCdObject(ctx *gin.Context, request *entity.Request) (*entity.CustomResourceDefinition, error) {
	clusterDefinition := kbv1.ClusterDefinition{
		TypeMeta: metav1.TypeMeta{
			Kind:       commonConst.ClusterDefinition,
			APIVersion: commonConst.ApiVersion,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name: constant.ClusterDefinitionName + "-" + request.Spec.Version,
			Labels: map[string]string{
				"app": constant.AppLables,
			},
		},
		Spec: kbv1.ClusterDefinitionSpec{
			Topologies: []kbv1.ClusterTopology{
				{
					Name:    constant.ClusterTopologyName,
					Default: true,
					Components: []kbv1.ClusterTopologyComponent{
						{
							Name:    engineConst.CompTopoNameByInsert,
							CompDef: engineConst.CmpdNameByInsert + "-" + request.Spec.Version,
						},
						{
							Name:    engineConst.CompTopoNameBySelect,
							CompDef: engineConst.CmpdNameBySelect + "-" + request.Spec.Version,
						},
						{
							Name:    engineConst.CompTopoNameByStorage,
							CompDef: engineConst.CmpdNameByStorage + "-" + request.Spec.Version,
						},
					},
					Orders: &kbv1.ClusterTopologyOrders{
						Provision: []string{
							"vmstorage",
							"vminsert,vmselect",
						},
					},
				},
			},
		},
	}

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&clusterDefinition)
	if err != nil {
		return nil, fmt.Errorf("转换对象为Unstructured类型失败: %v", err)
	}

	gvr := schema.GroupVersionResource{
		Group:    "apps.kubeblocks.io",
		Version:  "v1alpha1",
		Resource: "clusterdefinitions",
	}
	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}
	crd := &entity.CustomResourceDefinition{
		ResourceType:         commonConst.ClusterDefinition,
		ResourceName:         constant.ClusterDefinitionName + "-" + request.Spec.Version,
		GroupVersionResource: gvr,
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateCmpdInsert creates a custom resource definition object for the insert component definition.
func (v *Victoriametrics) CreateCmpdInsert(ctx *gin.Context, request *entity.Request) (*entity.CustomResourceDefinition, error) {
	componentDefinition := kbv1.ComponentDefinition{
		TypeMeta: metav1.TypeMeta{
			APIVersion: commonConst.ApiVersion,
			Kind:       commonConst.ComponentDefinition,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name: engineConst.CmpdNameByInsert + "-" + request.Spec.Version,
		},
		Spec: kbv1.ComponentDefinitionSpec{
			ServiceVersion: request.Spec.Version,
			ServiceKind:    engineConst.SvcKindByInsert,
			UpdateStrategy: entity.GetBestEffortParallelStrategy(),
			Exporter: &kbv1.Exporter{
				ScrapePath: "/metrics",
				ScrapePort: "http",
			},
			//Services: []kbv1.ComponentService{
			//	{
			//		Service: kbv1.Service{
			//			Name:        SvcNameByInsert,
			//			ServiceName: SvcNameByInsert,
			//			Spec: corev1.ServiceSpec{
			//				Ports: []corev1.ServicePort{
			//					{
			//						Name:       "http",
			//						Port:       8480, //v.vmselect.Connect.Port,
			//						TargetPort: intstr.FromString("http"),
			//						Protocol:   corev1.ProtocolTCP,
			//					},
			//				},
			//			},
			//		},
			//	},
			//},
			Vars: []kbv1.EnvVar{
				{
					Name: "VMSTORAGE_ENDPOINT",
					ValueFrom: &kbv1.VarSource{
						ServiceVarRef: &kbv1.ServiceVarSelector{
							ClusterObjectReference: kbv1.ClusterObjectReference{
								CompDef:  engineConst.CmpdNameByStorage + "-" + request.Spec.Version,
								Optional: entity.GetTrue(),
							},
							ServiceVars: kbv1.ServiceVars{
								Host: entity.GetRequiredVarOption(),
							},
						},
					},
				},
				{
					Name: "VMSTORAGE_ADDR",
					ValueFrom: &kbv1.VarSource{
						ServiceVarRef: &kbv1.ServiceVarSelector{
							ClusterObjectReference: kbv1.ClusterObjectReference{
								CompDef: engineConst.CmpdNameByStorage + "-" + request.Spec.Version,
							},
							ServiceVars: kbv1.ServiceVars{
								Port: &kbv1.NamedVar{
									Name:   engineConst.SvcNameByInsert,
									Option: entity.GetRequiredVarOption(),
								},
							},
						},
					},
				},
			},
			Runtime: corev1.PodSpec{
				AutomountServiceAccountToken:  entity.GetTrue(),
				TerminationGracePeriodSeconds: entity.IntToInt64Ptr(60),
				Containers: []corev1.Container{
					{
						Name:            engineConst.InsertContainerName,
						ImagePullPolicy: corev1.PullIfNotPresent,
						Args: []string{
							"--storageNode=$(VMSTORAGE_ADDR)",
							"--envflag.enable=true",
							"--envflag.prefix=VM_",
							"--loggerFormat=json",
							"--httpListenAddr=:8480",
						},
						Env: []corev1.EnvVar{
							{
								Name:  "SERVICE_PORT",
								Value: "8480",
							},
						},
						Ports: []corev1.ContainerPort{
							{
								ContainerPort: 8480,
								Name:          "http",
								Protocol:      corev1.ProtocolTCP,
							},
						},
						ReadinessProbe: &corev1.Probe{
							ProbeHandler: corev1.ProbeHandler{
								HTTPGet: &corev1.HTTPGetAction{
									Path:   "/health",
									Port:   intstr.FromString("http"),
									Scheme: corev1.URISchemeHTTP,
								},
							},
							InitialDelaySeconds: 5,
							PeriodSeconds:       15,
							TimeoutSeconds:      5,
							FailureThreshold:    3,
						},
						LivenessProbe: &corev1.Probe{
							ProbeHandler: corev1.ProbeHandler{
								TCPSocket: &corev1.TCPSocketAction{
									Port: intstr.FromString("http"),
								},
							},
							InitialDelaySeconds: 5,
							PeriodSeconds:       15,
							TimeoutSeconds:      5,
							FailureThreshold:    3,
						},
						VolumeMounts: []corev1.VolumeMount{
							{
								MountPath: "/cache/insert",
								Name:      "cache-insert",
							},
						},
					},
				},
			},
		},
	}

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&componentDefinition)
	if err != nil {
		return nil, fmt.Errorf("转换对象为Unstructured类型失败: %v", err)
	}

	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}
	crd := &entity.CustomResourceDefinition{
		ResourceType:         commonConst.ComponentDefinition,
		ResourceName:         engineConst.CmpdNameByInsert + "-" + request.Spec.Version,
		GroupVersionResource: kbtypes.CompDefGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateCmpdSelect creates a custom resource definition object for the select component definition.
func (v *Victoriametrics) CreateCmpdSelect(ctx *gin.Context, request *entity.Request) (*entity.CustomResourceDefinition, error) {

	componentDefinition := kbv1.ComponentDefinition{
		TypeMeta: metav1.TypeMeta{
			APIVersion: commonConst.ApiVersion,
			Kind:       commonConst.ComponentDefinition,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name: engineConst.CmpdNameBySelect + "-" + request.Spec.Version,
		},
		Spec: kbv1.ComponentDefinitionSpec{
			ServiceVersion: request.Spec.Version,
			ServiceKind:    engineConst.SvcKindBySelect,
			UpdateStrategy: entity.GetBestEffortParallelStrategy(),
			Exporter: &kbv1.Exporter{
				ScrapePath: "/metrics",
				ScrapePort: "http",
			},
			//Services: []kbv1.ComponentService{
			//	{
			//		Service: kbv1.Service{
			//			Name:        SvcNameBySelect,
			//			ServiceName: SvcNameBySelect,
			//			Spec: corev1.ServiceSpec{
			//				Ports: []corev1.ServicePort{
			//					{
			//						Name:       "http",
			//						Port:       8481, //v.vmselect.Connect.Port,
			//						TargetPort: intstr.FromString("http"),
			//						Protocol:   corev1.ProtocolTCP,
			//					},
			//				},
			//			},
			//		},
			//	},
			//},
			Vars: []kbv1.EnvVar{
				{
					Name: "VMSTORAGE_ENDPOINT",
					ValueFrom: &kbv1.VarSource{
						ServiceVarRef: &kbv1.ServiceVarSelector{
							ClusterObjectReference: kbv1.ClusterObjectReference{
								CompDef:  engineConst.CmpdNameByStorage + "-" + request.Spec.Version,
								Optional: entity.GetTrue(),
							},
							ServiceVars: kbv1.ServiceVars{
								Host: entity.GetRequiredVarOption(),
							},
						},
					},
				},
				{
					Name: "VMSTORAGE_ADDR",
					ValueFrom: &kbv1.VarSource{
						ServiceVarRef: &kbv1.ServiceVarSelector{
							ClusterObjectReference: kbv1.ClusterObjectReference{
								CompDef: engineConst.CmpdNameByStorage + "-" + request.Spec.Version,
							},
							ServiceVars: kbv1.ServiceVars{
								Port: &kbv1.NamedVar{
									Name:   engineConst.SvcNameBySelect,
									Option: entity.GetRequiredVarOption(),
								},
							},
						},
					},
				},
			},
			Runtime: corev1.PodSpec{
				AutomountServiceAccountToken:  entity.GetTrue(),
				TerminationGracePeriodSeconds: entity.IntToInt64Ptr(60),
				Containers: []corev1.Container{
					{
						Name:            engineConst.SelectContainerName,
						ImagePullPolicy: corev1.PullIfNotPresent,
						SecurityContext: &corev1.SecurityContext{},
						Args: []string{
							"--storageNode=$(VMSTORAGE_ADDR)",
							"--cacheDataPath=/cache",
							"--envflag.enable=true",
							"--envflag.prefix=VM_",
							"--loggerFormat=json",
							"--httpListenAddr=:8481",
						},
						Env: []corev1.EnvVar{
							{
								Name:  "SERVICE_PORT",
								Value: "8481",
							},
						},
						Ports: []corev1.ContainerPort{
							{
								ContainerPort: 8481,
								Name:          "http",
								Protocol:      corev1.ProtocolTCP,
							},
						},
						ReadinessProbe: &corev1.Probe{
							ProbeHandler: corev1.ProbeHandler{
								HTTPGet: &corev1.HTTPGetAction{
									Path:   "/health",
									Port:   intstr.FromString("http"),
									Scheme: corev1.URISchemeHTTP,
								},
							},
							InitialDelaySeconds: 5,
							PeriodSeconds:       15,
							TimeoutSeconds:      5,
							FailureThreshold:    3,
						},
						LivenessProbe: &corev1.Probe{
							ProbeHandler: corev1.ProbeHandler{
								TCPSocket: &corev1.TCPSocketAction{
									Port: intstr.FromString("http"),
								},
							},
							InitialDelaySeconds: 5,
							PeriodSeconds:       15,
							TimeoutSeconds:      5,
							FailureThreshold:    3,
						},
						VolumeMounts: []corev1.VolumeMount{
							{
								MountPath: "/cache/select",
								Name:      "cache-select",
							},
						},
					},
				},
			},
		},
	}

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&componentDefinition)
	if err != nil {
		return nil, fmt.Errorf("转换对象为Unstructured类型失败: %v", err)
	}

	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}
	crd := &entity.CustomResourceDefinition{
		ResourceType:         commonConst.ComponentDefinition,
		ResourceName:         engineConst.CmpdNameBySelect + "-" + request.Spec.Version,
		GroupVersionResource: kbtypes.CompDefGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateCmpdStorage  creates a custom resource definition object for the storage  component definition.
func (v *Victoriametrics) CreateCmpdStorage(ctx *gin.Context, request *entity.Request) (*entity.CustomResourceDefinition, error) {
	componentDefinition := kbv1.ComponentDefinition{
		TypeMeta: metav1.TypeMeta{
			APIVersion: commonConst.ApiVersion,
			Kind:       commonConst.ComponentDefinition,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name: engineConst.CmpdNameByStorage + "-" + request.Spec.Version,
		},
		Spec: kbv1.ComponentDefinitionSpec{
			ServiceKind:    engineConst.SvcKindByStorage,
			ServiceVersion: request.Spec.Version,
			Services: []kbv1.ComponentService{
				{
					Service: kbv1.Service{
						Name:        engineConst.SvcNameByStorage,
						ServiceName: engineConst.SvcNameByStorage,
						Spec: corev1.ServiceSpec{
							Ports: []corev1.ServicePort{
								//{
								//	Name:       "http",
								//	Port:       8482, //v.vmstorage.Connect.Port,
								//	TargetPort: intstr.FromString("http"),
								//	Protocol:   corev1.ProtocolTCP,
								//},
								{
									Name:       "vmselect",
									Port:       8401,
									TargetPort: intstr.FromString("vmselect"),
									Protocol:   corev1.ProtocolTCP,
								},
								{
									Name:       "vminsert",
									Port:       8400,
									TargetPort: intstr.FromString("vminsert"),
									Protocol:   corev1.ProtocolTCP,
								},
							},
						},
					},
					PodService: entity.GetTrue(),
				},
			},
			UpdateStrategy: entity.GetBestEffortParallelStrategy(),
			Exporter: &kbv1.Exporter{
				ScrapePath: "/metrics",
				ScrapePort: "http",
			},
			Runtime: corev1.PodSpec{
				AutomountServiceAccountToken:  entity.GetTrue(),
				TerminationGracePeriodSeconds: entity.IntToInt64Ptr(60),
				//Volumes: []corev1.Volume{
				//	{
				//		Name: "data",
				//		VolumeSource: corev1.VolumeSource{
				//			PersistentVolumeClaim: &corev1.PersistentVolumeClaimVolumeSource{
				//				ClaimName: "vm-pvc-manual",
				//			},
				//		},
				//	},
				//},
				Containers: []corev1.Container{
					{
						Name:            engineConst.StorageContainerName,
						ImagePullPolicy: corev1.PullIfNotPresent,
						SecurityContext: &corev1.SecurityContext{},
						Args: []string{
							"--retentionPeriod=1",
							"--storageDataPath=/storage",
							"--envflag.enable=true",
							"--envflag.prefix=VM_",
							"--loggerFormat=json",
							"--httpListenAddr=:8482",
							"--vminsertAddr=:8400",
							"--vmselectAddr=:8401",
						},
						Env: []corev1.EnvVar{
							{
								Name:  "SERVICE_PORT",
								Value: "8482",
							},
						},
						Ports: []corev1.ContainerPort{
							{
								ContainerPort: 8482,
								Name:          "http",
							},
							{
								ContainerPort: 8400,
								Name:          "vminsert",
							},
							{
								ContainerPort: 8401,
								Name:          "vmselect",
							},
						},
						LivenessProbe: &corev1.Probe{
							ProbeHandler: corev1.ProbeHandler{
								TCPSocket: &corev1.TCPSocketAction{
									Port: intstr.FromString("http"),
								},
							},
							FailureThreshold:    10,
							InitialDelaySeconds: 30,
							PeriodSeconds:       30,
							TimeoutSeconds:      5,
						},
						ReadinessProbe: &corev1.Probe{
							ProbeHandler: corev1.ProbeHandler{
								HTTPGet: &corev1.HTTPGetAction{
									Path: "/health",
									Port: intstr.FromString("http"),
								},
							},
							FailureThreshold:    3,
							InitialDelaySeconds: 5,
							PeriodSeconds:       15,
							TimeoutSeconds:      5,
						},
						VolumeMounts: []corev1.VolumeMount{
							{
								Name:      engineConst.VolumeMountNameByStorage,
								MountPath: "/storage",
							},
						},
					},
				},
			},
		},
	}

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&componentDefinition)
	if err != nil {
		return nil, fmt.Errorf("转换对象为Unstructured类型失败: %v", err)
	}

	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}
	crd := &entity.CustomResourceDefinition{
		ResourceType:         commonConst.ComponentDefinition,
		ResourceName:         engineConst.CmpdNameByStorage + "-" + request.Spec.Version,
		GroupVersionResource: kbtypes.CompDefGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateCmpvObject creates a custom resource definition object for the Victoriametrics component version.
func (v *Victoriametrics) CreateCmpvObject(ctx *gin.Context, request *entity.Request) (*entity.CustomResourceDefinition, error) {
	componentVersion := kbv1.ComponentVersion{
		TypeMeta: metav1.TypeMeta{
			APIVersion: commonConst.ApiVersion,
			Kind:       commonConst.ComponentVersion,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name: constant.ComponentVersionName + "-" + request.Spec.Version,
		},
		Spec: kbv1.ComponentVersionSpec{
			CompatibilityRules: []kbv1.ComponentVersionCompatibilityRule{
				{
					Releases: []string{
						engineConst.ReleasesNameByInsert + "-" + request.Spec.Version,
					},
					CompDefs: []string{
						engineConst.CmpdNameByInsert + "-" + request.Spec.Version,
					},
				},
				{
					Releases: []string{
						engineConst.ReleasesNameBySelect + "-" + request.Spec.Version,
					},
					CompDefs: []string{
						engineConst.CmpdNameBySelect + "-" + request.Spec.Version,
					},
				},
				{
					Releases: []string{
						engineConst.ReleasesNameByStorage + "-" + request.Spec.Version,
					},
					CompDefs: []string{
						engineConst.CmpdNameByStorage + "-" + request.Spec.Version,
					},
				},
			},
			Releases: []kbv1.ComponentVersionRelease{
				{
					Name:           engineConst.ReleasesNameByInsert + "-" + request.Spec.Version,
					ServiceVersion: request.Spec.Version,
					Images: map[string]string{
						engineConst.InsertContainerName: "victoriametrics/vminsert:v" + request.Spec.Version + "-cluster",
					},
				},
				{
					Name:           engineConst.ReleasesNameBySelect + "-" + request.Spec.Version,
					ServiceVersion: request.Spec.Version,
					Images: map[string]string{
						engineConst.SelectContainerName: "victoriametrics/vmselect:v" + request.Spec.Version + "-cluster",
					},
				},
				{
					Name:           engineConst.ReleasesNameByStorage + "-" + request.Spec.Version,
					ServiceVersion: request.Spec.Version,
					Images: map[string]string{
						engineConst.StorageContainerName: "victoriametrics/vmstorage:v" + request.Spec.Version + "-cluster",
					},
				},
			},
		},
	}

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&componentVersion)
	if err != nil {
		return nil, fmt.Errorf("转换对象为Unstructured类型失败: %v", err)
	}

	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}
	gvr := schema.GroupVersionResource{
		Group:    "apps.kubeblocks.io",
		Version:  "v1alpha1",
		Resource: "componentversions",
	}
	crd := &entity.CustomResourceDefinition{
		ResourceType:         commonConst.ComponentVersion,
		ResourceName:         engineConst.ComponentVersionName + "-" + request.Spec.Version,
		GroupVersionResource: gvr,
		ResourceObject:       Obj,
	}
	return crd, err
}
