package surrealdb

import (
	"context"
	"fmt"
	"k8s-dbs/src/core/client"
	commonConst "k8s-dbs/src/core/constant"
	engineConst "k8s-dbs/src/core/engine/surrealdb/constant"
	"k8s-dbs/src/core/entity"
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

// Surreal represents the SurrealDB src structure.
type Surreal struct {
	surreal *entity.ComponentResource
}

// NewSurreal creates a new instance of the Surreal struct.
func NewSurreal() *Surreal {
	return &Surreal{}
}

func (s *Surreal) CreateCluster(k8sClient *client.K8sClient, ctx *gin.Context, request *entity.Request) (*entity.ClusterResponseData, error) {
	// create componentVersion if it is not already exists
	cmpv, err := s.CreateCmpvObject(ctx, request)
	if err != nil {
		return nil, err
	}
	err = client.CreateCRD(k8sClient, cmpv)
	if err = skipIfAlreadyExists(err); err != nil {
		return nil, err
	}

	// create componentDefinition if it is not already exists
	cmpd, err := s.CreateCmpdObject(ctx, request)
	if err != nil {
		return nil, err
	}
	err = client.CreateCRD(k8sClient, cmpd)
	if err = skipIfAlreadyExists(err); err != nil {
		return nil, err
	}

	// create clusterDefinition if it is not already exists
	cd, err := s.CreateCdObject(ctx, request)
	if err != nil {
		return nil, err
	}
	err = client.CreateCRD(k8sClient, cd)
	if err = skipIfAlreadyExists(err); err != nil {
		return nil, err
	}

	cluster, err := s.CreateClusterObject(ctx, request)
	if err != nil {
		return nil, err
	}
	err = client.CreateCRD(k8sClient, cluster)
	if err != nil {
		return nil, err
	}
	return nil, nil
}

// DescribeCluster retrieves the details of a SurrealDB cluster.
func (s *Surreal) DescribeCluster(k8sClient *client.K8sClient, ctx *gin.Context, request *entity.Request) (*entity.ClusterResponseData, error) {
	clusterName := request.Metadata.ClusterName
	namespace := request.Metadata.Namespace
	gvr := kbtypes.ClusterGVR()

	cluster, err := k8sClient.DynamicClient.
		Resource(gvr).
		Namespace(namespace).
		Get(context.TODO(), clusterName, metav1.GetOptions{})
	if err != nil {
		return nil, err
	}

	dataResponse, err := entity.GetClusterResponseData(cluster)
	if err != nil {
		return nil, err
	}
	return dataResponse, nil
}

// DeleteCluster deletes a SurrealDB cluster.
func (s *Surreal) DeleteCluster(k8sClient *client.K8sClient, ctx *gin.Context, clusterData *entity.ClusterResponseData, request *entity.Request) error {
	cluster, err := s.CreateClusterObject(ctx, request)
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
func (s *Surreal) CreateCdCmpdCmpv(k8sClient *client.K8sClient, ctx *gin.Context, request *entity.Request) error {
	// create componentVersion if it is not already exists
	cmpv, err := s.CreateCmpvObject(ctx, request)
	if err != nil {
		return err
	}
	err = client.CreateCRD(k8sClient, cmpv)
	if err = skipIfAlreadyExists(err); err != nil {
		return err
	}

	// create componentDefinition if it is not already exists
	cmpd, err := s.CreateCmpdObject(ctx, request)
	if err != nil {
		return err
	}
	err = client.CreateCRD(k8sClient, cmpd)
	if err = skipIfAlreadyExists(err); err != nil {
		return err
	}

	// create clusterDefinition if it is not already exists
	cd, err := s.CreateCdObject(ctx, request)
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
func (s *Surreal) GetClusterStatus(k8sClient *client.K8sClient, ctx *gin.Context, request *entity.Request) (*entity.ClusterStatus, error) {
	clusterName := request.Metadata.ClusterName
	namespace := request.Metadata.Namespace
	gvr := kbtypes.ClusterGVR()

	cluster, err := k8sClient.DynamicClient.
		Resource(gvr).
		Namespace(namespace).
		Get(context.TODO(), clusterName, metav1.GetOptions{})
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

// CreateClusterObject creates a custom resource definition object for the SurrealDB cluster.
func (s *Surreal) CreateClusterObject(ctx *gin.Context, request *entity.Request) (*entity.CustomResourceDefinition, error) {
	serviceName, err := entity.GetDefaultServiceName(s.surreal.Connect.Host)
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
			ClusterDefRef:     engineConst.ClusterDefinitionName + "-" + request.Spec.Version,
			Topology:          engineConst.ClusterTopologyName,
			TerminationPolicy: kbv1.Delete,
			ComponentSpecs: []kbv1.ClusterComponentSpec{
				{
					Name:           engineConst.CompTopoNameBySurreal,
					ServiceVersion: request.Spec.Version,
					Services: []kbv1.ClusterComponentService{
						{
							Name: serviceName,
						},
					},
					Env: []corev1.EnvVar{
						{
							Name:  "SURREAL_USER",
							Value: s.surreal.Connect.User,
						},
						{
							Name:  "SURREAL_PASS",
							Value: s.surreal.Connect.Password,
						},
					},
					Replicas: s.surreal.Replicas,
					Resources: corev1.ResourceRequirements{
						Requests: corev1.ResourceList{
							"cpu":    resource.MustParse(s.surreal.Request.Cpu),
							"memory": resource.MustParse(s.surreal.Request.Memory),
						},
						Limits: corev1.ResourceList{
							"cpu":    resource.MustParse(s.surreal.Limit.Cpu),
							"memory": resource.MustParse(s.surreal.Limit.Memory),
						},
					},
					VolumeClaimTemplates: []kbv1.ClusterComponentVolumeClaimTemplate{
						{
							Name: engineConst.VolumeName,
							Spec: kbv1.PersistentVolumeClaimSpec{
								AccessModes: []corev1.PersistentVolumeAccessMode{
									corev1.ReadWriteOnce,
								},
								Resources: corev1.VolumeResourceRequirements{
									Requests: corev1.ResourceList{
										"storage": resource.MustParse(s.surreal.Storage),
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
			},
			Services: []kbv1.ClusterService{
				{
					Service: kbv1.Service{
						Name:        serviceName,
						ServiceName: serviceName,
						Spec: corev1.ServiceSpec{
							Ports: []corev1.ServicePort{
								{
									Name:       "http",
									Port:       s.surreal.Connect.Port,
									TargetPort: intstr.FromString("http"),
									Protocol:   corev1.ProtocolTCP,
								},
							},
						},
					},
				},
			},
		},
	}

	crd := &entity.CustomResourceDefinition{}
	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&cluster)
	if err != nil {
		return crd, fmt.Errorf("转换对象为Unstructured类型失败: %v", err)
	}

	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}
	crd = &entity.CustomResourceDefinition{
		Namespace:            request.Metadata.Namespace,
		ResourceType:         commonConst.Cluster,
		ResourceName:         request.Metadata.ClusterName,
		GroupVersionResource: kbtypes.ClusterGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateCdObject creates a custom resource definition object for the SurrealDB cluster definition.
func (s *Surreal) CreateCdObject(ctx *gin.Context, request *entity.Request) (*entity.CustomResourceDefinition, error) {
	clusterDefinition := kbv1.ClusterDefinition{
		TypeMeta: metav1.TypeMeta{
			Kind:       commonConst.ClusterDefinition,
			APIVersion: commonConst.ApiVersion,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name: engineConst.ClusterDefinitionName + "-" + request.Spec.Version,
		},
		Spec: kbv1.ClusterDefinitionSpec{
			Topologies: []kbv1.ClusterTopology{
				{
					Name:    engineConst.ClusterTopologyName,
					Default: true,
					Components: []kbv1.ClusterTopologyComponent{
						{
							Name:    engineConst.CompTopoNameBySurreal,
							CompDef: engineConst.ComponentDefinitionName + "-" + request.Spec.Version,
						},
					},
				},
			},
		},
	}

	crd := &entity.CustomResourceDefinition{}
	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&clusterDefinition)
	if err != nil {
		return crd, fmt.Errorf("转换对象为Unstructured类型失败: %v", err)
	}

	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}
	crd = &entity.CustomResourceDefinition{
		ResourceType:         commonConst.ClusterDefinition,
		ResourceName:         engineConst.ClusterDefinitionName + "-" + request.Spec.Version,
		GroupVersionResource: kbtypes.ClusterDefGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateCmpdObject creates a custom resource definition object for the SurrealDB component definition.
func (s *Surreal) CreateCmpdObject(ctx *gin.Context, request *entity.Request) (*entity.CustomResourceDefinition, error) {
	componentDefinition := kbv1.ComponentDefinition{
		TypeMeta: metav1.TypeMeta{
			APIVersion: commonConst.ApiVersion,
			Kind:       commonConst.ComponentDefinition,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name: engineConst.ComponentDefinitionName + "-" + request.Spec.Version,
		},
		Spec: kbv1.ComponentDefinitionSpec{
			ServiceVersion: request.Spec.Version,
			ServiceKind:    engineConst.ServiceKind,
			Runtime: corev1.PodSpec{
				SecurityContext: &corev1.PodSecurityContext{
					FSGroup:    entity.IntToInt64Ptr(999),
					RunAsGroup: entity.IntToInt64Ptr(999),
					RunAsUser:  entity.IntToInt64Ptr(999),
				},
				Containers: []corev1.Container{
					{
						Name: engineConst.ContainerName,
						//Image:           Image,
						ImagePullPolicy: corev1.PullIfNotPresent,
						Args: []string{
							"start",
							engineConst.SurrealPath,
						},
						Env: []corev1.EnvVar{
							{
								Name:  "SURREAL_NO_BANNER",
								Value: "true",
							},
							{
								Name:  "SURREAL_PATH",
								Value: engineConst.SurrealPath,
							},
							{
								Name:  "SURREAL_LOG",
								Value: "info",
							},
							{
								Name:  "SURREAL_BIND",
								Value: "0.0.0.0:8000",
							},
							{
								Name:  "SURREAL_AUTH",
								Value: "true",
							},
							{
								Name:  "SURREAL_UNAUTHENTICATED",
								Value: "false",
							},
						},
						// 卷挂载
						VolumeMounts: []corev1.VolumeMount{
							{
								Name:      engineConst.VolumeName,
								MountPath: engineConst.MountPath,
							},
						},
						Ports: []corev1.ContainerPort{
							{
								ContainerPort: 8000,
								Name:          "http",
								Protocol:      corev1.ProtocolTCP,
							},
						},
						// 就绪探针
						ReadinessProbe: &corev1.Probe{
							ProbeHandler: corev1.ProbeHandler{
								HTTPGet: &corev1.HTTPGetAction{
									Path: "/health",
									Port: intstr.IntOrString{IntVal: 8000},
								},
							},
						},
						// 存活探针
						LivenessProbe: &corev1.Probe{
							ProbeHandler: corev1.ProbeHandler{
								HTTPGet: &corev1.HTTPGetAction{
									Path: "/health",
									Port: intstr.IntOrString{IntVal: 8000},
								},
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
		ResourceName:         engineConst.ComponentDefinitionName + "-" + request.Spec.Version,
		GroupVersionResource: kbtypes.CompDefGVR(),
		ResourceObject:       Obj,
	}
	return crd, err
}

// CreateCmpvObject creates a custom resource definition object for the SurrealDB component version.
func (s *Surreal) CreateCmpvObject(ctx *gin.Context, request *entity.Request) (*entity.CustomResourceDefinition, error) {
	componentVersion := kbv1.ComponentVersion{
		TypeMeta: metav1.TypeMeta{
			APIVersion: commonConst.ApiVersion,
			Kind:       commonConst.ComponentVersion,
		},
		ObjectMeta: metav1.ObjectMeta{
			Name: engineConst.ComponentVersionName + "-" + request.Spec.Version,
		},
		Spec: kbv1.ComponentVersionSpec{
			CompatibilityRules: []kbv1.ComponentVersionCompatibilityRule{
				{
					Releases: []string{
						engineConst.ReleasesName + "-" + request.Spec.Version,
					},
					CompDefs: []string{
						engineConst.ComponentDefinitionName + "-" + request.Spec.Version,
					},
				},
			},
			Releases: []kbv1.ComponentVersionRelease{
				{
					Name:           engineConst.ReleasesName + "-" + request.Spec.Version,
					ServiceVersion: request.Spec.Version,
					Images: map[string]string{
						engineConst.ContainerName: "docker.io/surrealdb/surrealdb:v" + request.Spec.Version,
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
