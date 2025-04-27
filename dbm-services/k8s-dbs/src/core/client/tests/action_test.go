package tests

import (
	"fmt"
	"k8s-dbs/src/core/client"
	"k8s-dbs/src/core/client/constants"
	"k8s-dbs/src/core/entity"
	"testing"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	kbv1 "github.com/apecloud/kubeblocks/apis/apps/v1alpha1"
	v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/dynamic"

	"github.com/stretchr/testify/assert"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	dynamicfake "k8s.io/client-go/dynamic/fake"
	clienttesting "k8s.io/client-go/testing"
)

func TestCreateCRD_GlobalResource(t *testing.T) {
	// 准备 fake 动态客户端
	gvr := kbtypes.CompDefGVR()
	scheme := runtime.NewScheme()
	fakeClient := dynamicfake.NewSimpleDynamicClient(scheme)

	k8sClient := &client.K8sClient{}

	// 替换源客户端
	origClient := k8sClient.DynamicClient
	k8sClient.DynamicClient = dynamic.Interface(fakeClient)
	defer func() { k8sClient.DynamicClient = origClient }()

	// 构造测试用例
	crd := &entity.CustomResourceDefinition{
		ResourceType:         constants.ComponentDefinition,
		ResourceName:         "ComponentDefinitionName",
		GroupVersionResource: gvr,
		ResourceObject:       &unstructured.Unstructured{},
	}

	// 执行函数
	err := client.CreateCRD(k8sClient, crd)
	assert.NoError(t, err)

	// 验证行为
	actions := fakeClient.Actions()
	assert.Len(t, actions, 1)

	createAction, ok := actions[0].(clienttesting.CreateAction)
	assert.True(t, ok, "Expected CreateAction")
	assert.Equal(t, gvr, createAction.GetResource(), "Resource mismatch")
	assert.Empty(t, createAction.GetNamespace(), "Namespace should be empty for global resource")
}

func TestCreateCRD_NamespacedResource(t *testing.T) {
	gvr := kbtypes.ClusterGVR()
	scheme := runtime.NewScheme()
	fakeClient := dynamicfake.NewSimpleDynamicClient(scheme)
	k8sClient := &client.K8sClient{}
	origClient := k8sClient.DynamicClient
	k8sClient.DynamicClient = fakeClient
	defer func() { k8sClient.DynamicClient = origClient }()

	crd := &entity.CustomResourceDefinition{
		Namespace:            "test-ns",
		ResourceType:         "test-cluster",
		ResourceName:         "test-clusterName",
		GroupVersionResource: gvr,
		ResourceObject:       &unstructured.Unstructured{},
	}

	err := client.CreateCRD(k8sClient, crd)
	assert.NoError(t, err)

	actions := fakeClient.Actions()
	assert.Len(t, actions, 1)

	createAction := actions[0].(clienttesting.CreateAction)
	assert.Equal(t, gvr, createAction.GetResource())
	assert.Equal(t, "test-ns", createAction.GetNamespace())
}

func TestCreateCRD_NameSpace_ErrorHandling(t *testing.T) {
	gvr := kbtypes.ClusterGVR()
	scheme := runtime.NewScheme()
	fakeClient := dynamicfake.NewSimpleDynamicClient(scheme)

	// 注入错误响应
	fakeClient.PrependReactor("create", "clusters", func(action clienttesting.Action) (bool, runtime.Object, error) {
		return true, nil, fmt.Errorf("模拟 API 错误")
	})
	k8sClient := &client.K8sClient{}
	origClient := k8sClient.DynamicClient
	k8sClient.DynamicClient = fakeClient
	defer func() { k8sClient.DynamicClient = origClient }()

	crd := &entity.CustomResourceDefinition{
		Namespace:            "test-ns",
		ResourceType:         "test-cluster",
		ResourceName:         "test-clusterName",
		GroupVersionResource: gvr,
		ResourceObject:       &unstructured.Unstructured{},
	}

	err := client.CreateCRD(k8sClient, crd)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "模拟 API 错误")
}

func TestCreateCRD_ErrorHandling(t *testing.T) {
	gvr := kbtypes.CompDefGVR()
	scheme := runtime.NewScheme()
	fakeClient := dynamicfake.NewSimpleDynamicClient(scheme)

	// 注入错误响应
	fakeClient.PrependReactor("create", "componentdefinitions", func(action clienttesting.Action) (bool, runtime.Object, error) {
		return true, nil, fmt.Errorf("模拟 API 错误")
	})

	k8sClient := &client.K8sClient{}
	origClient := k8sClient.DynamicClient
	k8sClient.DynamicClient = fakeClient
	defer func() { k8sClient.DynamicClient = origClient }()

	crd := &entity.CustomResourceDefinition{
		ResourceType:         constants.ComponentDefinition,
		ResourceName:         "test-componentDefinitionName",
		GroupVersionResource: gvr,
		ResourceObject:       &unstructured.Unstructured{},
	}

	err := client.CreateCRD(k8sClient, crd)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "模拟 API 错误")
}

func TestDeleteCRD_GlobalResource(t *testing.T) {
	gvr := kbtypes.CompDefGVR()
	scheme := runtime.NewScheme()
	fakeClient := dynamicfake.NewSimpleDynamicClient(scheme)

	k8sClient := &client.K8sClient{}
	origClient := k8sClient.DynamicClient
	k8sClient.DynamicClient = fakeClient
	defer func() { k8sClient.DynamicClient = origClient }()

	componentDefinition := kbv1.ComponentDefinition{
		TypeMeta: v1.TypeMeta{
			APIVersion: "apps.kubeblocks.io/v1alpha1",
			Kind:       "ComponentDefinition",
		},
		ObjectMeta: v1.ObjectMeta{
			Name: "ComponentDefinitionName",
		},
	}

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&componentDefinition)
	if err != nil {
		t.Fatalf("转换对象为Unstructured类型失败: %v", err)
	}

	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}

	crd := &entity.CustomResourceDefinition{
		ResourceType:         constants.ComponentDefinition,
		ResourceName:         "ComponentDefinitionName",
		GroupVersionResource: gvr,
		ResourceObject:       Obj, // 使用转换后的对象
	}

	// 先创建资源
	_, err = k8sClient.DynamicClient.Resource(gvr).Create(nil, crd.ResourceObject, v1.CreateOptions{})
	if err != nil {
		t.Fatalf("Failed to create resource: %v", err)
	}

	// 执行删除操作
	err = client.DeleteCRD(k8sClient, crd)
	assert.NoError(t, err)

	// 验证行为
	actions := fakeClient.Actions()
	assert.Len(t, actions, 2)

	deleteAction := actions[1].(clienttesting.DeleteAction)
	assert.Equal(t, gvr, deleteAction.GetResource())
	assert.Empty(t, deleteAction.GetNamespace())
}

func TestDeleteCRD_NamespacedResource(t *testing.T) {
	gvr := kbtypes.ClusterGVR()
	scheme := runtime.NewScheme()
	fakeClient := dynamicfake.NewSimpleDynamicClient(scheme)

	k8sClient := &client.K8sClient{}
	origClient := k8sClient.DynamicClient
	k8sClient.DynamicClient = fakeClient
	defer func() { k8sClient.DynamicClient = origClient }()

	cluster := kbv1.ComponentDefinition{
		TypeMeta: v1.TypeMeta{
			APIVersion: "apps.kubeblocks.io/v1alpha1",
			Kind:       "Cluster",
		},
		ObjectMeta: v1.ObjectMeta{
			Name:      "test-clusterName",
			Namespace: "test-ns",
		},
	}

	unstructuredClusterDef, err := runtime.DefaultUnstructuredConverter.ToUnstructured(&cluster)
	if err != nil {
		t.Fatalf("转换对象为Unstructured类型失败: %v", err)
	}

	Obj := &unstructured.Unstructured{
		Object: unstructuredClusterDef,
	}

	crd := &entity.CustomResourceDefinition{
		Namespace:            "test-ns",
		ResourceType:         "test-cluster",
		ResourceName:         "test-clusterName",
		GroupVersionResource: gvr,
		ResourceObject:       Obj,
	}

	// 先创建资源
	_, err = k8sClient.DynamicClient.Resource(gvr).Namespace(crd.Namespace).Create(nil, crd.ResourceObject, v1.CreateOptions{})
	if err != nil {
		t.Fatalf("Failed to create resource: %v", err)
	}

	err = client.DeleteCRD(k8sClient, crd)
	assert.NoError(t, err)

	actions := fakeClient.Actions()
	assert.Len(t, actions, 2)

	deleteAction := actions[1].(clienttesting.DeleteAction)
	assert.Equal(t, gvr, deleteAction.GetResource())
	assert.Equal(t, "test-ns", deleteAction.GetNamespace())
}

func TestDeleteCRD_Namespace_ErrorHandling(t *testing.T) {
	gvr := kbtypes.ClusterGVR()
	scheme := runtime.NewScheme()
	fakeClient := dynamicfake.NewSimpleDynamicClient(scheme)

	// 注入错误响应
	fakeClient.PrependReactor("delete", "clusters", func(action clienttesting.Action) (bool, runtime.Object, error) {
		return true, nil, fmt.Errorf("模拟 API 错误")
	})

	k8sClient := &client.K8sClient{}
	origClient := k8sClient.DynamicClient
	k8sClient.DynamicClient = fakeClient
	defer func() { k8sClient.DynamicClient = origClient }()

	crd := &entity.CustomResourceDefinition{
		Namespace:            "test-ns",
		ResourceType:         "test-cluster",
		ResourceName:         "test-clusterName",
		GroupVersionResource: gvr,
		ResourceObject:       &unstructured.Unstructured{},
	}

	err := client.DeleteCRD(k8sClient, crd)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "模拟 API 错误")
}

func TestDeleteCRD_ErrorHandling(t *testing.T) {
	gvr := kbtypes.CompDefGVR()
	scheme := runtime.NewScheme()
	fakeClient := dynamicfake.NewSimpleDynamicClient(scheme)

	// 注入错误响应
	fakeClient.PrependReactor("delete", "componentdefinitions", func(action clienttesting.Action) (bool, runtime.Object, error) {
		return true, nil, fmt.Errorf("模拟 API 错误")
	})

	k8sClient := &client.K8sClient{}
	origClient := k8sClient.DynamicClient
	k8sClient.DynamicClient = fakeClient
	defer func() { k8sClient.DynamicClient = origClient }()

	crd := &entity.CustomResourceDefinition{
		ResourceType:         constants.ComponentDefinition,
		ResourceName:         "test-componentDefinitionName",
		GroupVersionResource: gvr,
		ResourceObject:       &unstructured.Unstructured{},
	}

	err := client.DeleteCRD(k8sClient, crd)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "模拟 API 错误")
}

func TestCreateCRD_NilInput(t *testing.T) {
	err := client.CreateCRD(nil, nil)
	assert.Error(t, err)
}

func TestDeleteCRD_NilInput(t *testing.T) {
	err := client.DeleteCRD(nil, nil)
	assert.Error(t, err)
}
