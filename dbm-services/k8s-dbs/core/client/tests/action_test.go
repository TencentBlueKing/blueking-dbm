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

package tests

import (
	"fmt"
	client2 "k8s-dbs/core/client"
	"k8s-dbs/core/client/constants"
	"k8s-dbs/core/entity"
	"testing"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	kbv1 "github.com/apecloud/kubeblocks/apis/apps/v1alpha1"
	"github.com/stretchr/testify/assert"
	v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	dynamicfake "k8s.io/client-go/dynamic/fake"
	clienttesting "k8s.io/client-go/testing"
)

func TestCreateCRD(t *testing.T) {
	// 准备 fake 动态客户端
	gvr := kbtypes.CompDefGVR()
	scheme := runtime.NewScheme()
	fakeClient := dynamicfake.NewSimpleDynamicClient(scheme)
	k8sClient := &client2.K8sClient{}
	origClient := k8sClient.DynamicClient
	k8sClient.DynamicClient = fakeClient
	defer func() { k8sClient.DynamicClient = origClient }()

	crd := &entity.CustomResourceDefinition{
		ResourceType:         constants.ComponentDefinition,
		ResourceName:         "ComponentDefinitionName",
		GroupVersionResource: gvr,
		ResourceObject:       &unstructured.Unstructured{},
	}

	err := client2.CreateCRD(k8sClient, crd)
	assert.NoError(t, err)

	actions := fakeClient.Actions()
	assert.Len(t, actions, 1)

	createAction, ok := actions[0].(clienttesting.CreateAction)
	assert.True(t, ok, "Expected CreateAction")
	assert.Equal(t, gvr, createAction.GetResource(), "Resource mismatch")
	assert.Empty(t, createAction.GetNamespace(), "Namespace should be empty for global resource")
}

func TestCreateCRDErr(t *testing.T) {
	gvr := kbtypes.CompDefGVR()
	scheme := runtime.NewScheme()
	fakeClient := dynamicfake.NewSimpleDynamicClient(scheme)

	// 注入错误响应
	fakeClient.PrependReactor("create", "componentdefinitions", func(action clienttesting.Action) (bool, runtime.Object, error) {
		return true, nil, fmt.Errorf("模拟 API 错误")
	})

	k8sClient := &client2.K8sClient{}
	origClient := k8sClient.DynamicClient
	k8sClient.DynamicClient = fakeClient
	defer func() { k8sClient.DynamicClient = origClient }()

	crd := &entity.CustomResourceDefinition{
		ResourceType:         constants.ComponentDefinition,
		ResourceName:         "test-componentDefinitionName",
		GroupVersionResource: gvr,
		ResourceObject:       &unstructured.Unstructured{},
	}

	err := client2.CreateCRD(k8sClient, crd)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "模拟 API 错误")
}

func TestCreateCRDWithNs(t *testing.T) {
	gvr := kbtypes.ClusterGVR()
	scheme := runtime.NewScheme()
	fakeClient := dynamicfake.NewSimpleDynamicClient(scheme)
	k8sClient := &client2.K8sClient{}
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

	err := client2.CreateCRD(k8sClient, crd)
	assert.NoError(t, err)

	actions := fakeClient.Actions()
	assert.Len(t, actions, 1)

	createAction := actions[0].(clienttesting.CreateAction)
	assert.Equal(t, gvr, createAction.GetResource())
	assert.Equal(t, "test-ns", createAction.GetNamespace())
}

func TestCreateCRDWithNsErr(t *testing.T) {
	gvr := kbtypes.ClusterGVR()
	scheme := runtime.NewScheme()
	fakeClient := dynamicfake.NewSimpleDynamicClient(scheme)

	// 注入错误响应
	fakeClient.PrependReactor("create", "clusters", func(action clienttesting.Action) (bool, runtime.Object, error) {
		return true, nil, fmt.Errorf("模拟 API 错误")
	})
	k8sClient := &client2.K8sClient{}
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

	err := client2.CreateCRD(k8sClient, crd)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "模拟 API 错误")
}

func TestDeleteCRD(t *testing.T) {
	gvr := kbtypes.CompDefGVR()
	scheme := runtime.NewScheme()
	fakeClient := dynamicfake.NewSimpleDynamicClient(scheme)

	k8sClient := &client2.K8sClient{}
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
	err = client2.DeleteCRD(k8sClient, crd)
	assert.NoError(t, err)

	// 验证行为
	actions := fakeClient.Actions()
	assert.Len(t, actions, 2)

	deleteAction := actions[1].(clienttesting.DeleteAction)
	assert.Equal(t, gvr, deleteAction.GetResource())
	assert.Empty(t, deleteAction.GetNamespace())
}

func TestDeleteCRDErr(t *testing.T) {
	gvr := kbtypes.CompDefGVR()
	scheme := runtime.NewScheme()
	fakeClient := dynamicfake.NewSimpleDynamicClient(scheme)

	// 注入错误响应
	fakeClient.PrependReactor("delete", "componentdefinitions", func(action clienttesting.Action) (bool, runtime.Object, error) {
		return true, nil, fmt.Errorf("模拟 API 错误")
	})

	k8sClient := &client2.K8sClient{}
	origClient := k8sClient.DynamicClient
	k8sClient.DynamicClient = fakeClient
	defer func() { k8sClient.DynamicClient = origClient }()

	crd := &entity.CustomResourceDefinition{
		ResourceType:         constants.ComponentDefinition,
		ResourceName:         "test-componentDefinitionName",
		GroupVersionResource: gvr,
		ResourceObject:       &unstructured.Unstructured{},
	}

	err := client2.DeleteCRD(k8sClient, crd)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "模拟 API 错误")
}

func TestDeleteCRDWithNs(t *testing.T) {
	gvr := kbtypes.ClusterGVR()
	scheme := runtime.NewScheme()
	fakeClient := dynamicfake.NewSimpleDynamicClient(scheme)

	k8sClient := &client2.K8sClient{}
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

	err = client2.DeleteCRD(k8sClient, crd)
	assert.NoError(t, err)

	actions := fakeClient.Actions()
	assert.Len(t, actions, 2)

	deleteAction := actions[1].(clienttesting.DeleteAction)
	assert.Equal(t, gvr, deleteAction.GetResource())
	assert.Equal(t, "test-ns", deleteAction.GetNamespace())
}

func TestDeleteCRDWithNsErr(t *testing.T) {
	gvr := kbtypes.ClusterGVR()
	scheme := runtime.NewScheme()
	fakeClient := dynamicfake.NewSimpleDynamicClient(scheme)

	// 注入错误响应
	fakeClient.PrependReactor("delete", "clusters", func(action clienttesting.Action) (bool, runtime.Object, error) {
		return true, nil, fmt.Errorf("模拟 API 错误")
	})

	k8sClient := &client2.K8sClient{}
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

	err := client2.DeleteCRD(k8sClient, crd)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "模拟 API 错误")
}
