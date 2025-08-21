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
	"context"
	"fmt"
	"k8s-dbs/core/constant"
	entitys "k8s-dbs/metadata/entity"
	"log"
	"math"

	"k8s.io/apimachinery/pkg/api/resource"

	metricsclientset "k8s.io/metrics/pkg/client/clientset/versioned"

	"helm.sh/helm/v3/pkg/action"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/cli-runtime/pkg/genericclioptions"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
)

// K8sClient 封装 k8s 客户端操作
type K8sClient struct {
	RestConfig    *rest.Config
	ClientSet     *kubernetes.Clientset
	DynamicClient dynamic.Interface
	MetricsClient *metricsclientset.Clientset
}

// NewK8sClient 创建 k8s 客户端实例
func NewK8sClient(k8sConfig *entitys.K8sClusterConfigEntity) (*K8sClient, error) {
	config := &rest.Config{
		Host:        k8sConfig.APIServerURL,
		BearerToken: k8sConfig.Token,
		TLSClientConfig: rest.TLSClientConfig{
			Insecure: true,
		},
	}
	clientSet, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, err
	}
	dynamicClient, err := dynamic.NewForConfig(config)
	if err != nil {
		return nil, err
	}
	metricsClientSet, err := metricsclientset.NewForConfig(config)
	if err != nil {
		return nil, err
	}
	k8sClient := K8sClient{
		RestConfig:    config,
		ClientSet:     clientSet,
		DynamicClient: dynamicClient,
		MetricsClient: metricsClientSet,
	}
	err = k8sClient.VerifyConnection()
	if err != nil {
		return nil, err
	}
	return &k8sClient, nil
}

// VerifyConnection 连通验证
func (k *K8sClient) VerifyConnection() error {
	_, err := k.ClientSet.CoreV1().Namespaces().List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		return fmt.Errorf("failed to connect to the k8sClient: %v", err)
	}
	return nil
}

// BuildHelmConfig 构建 helm Configuration
func (k *K8sClient) BuildHelmConfig(namespace string) (*action.Configuration, error) {
	configFlags := genericclioptions.NewConfigFlags(true)
	configFlags.WrapConfigFn = func(_ *rest.Config) *rest.Config {
		return k.RestConfig
	}

	helmActionConfig := new(action.Configuration)
	if err := helmActionConfig.Init(
		configFlags,
		namespace,
		constant.HelmDriver,
		func(format string, v ...interface{}) {
			log.Printf(format, v...)
		},
	); err != nil {
		return nil, fmt.Errorf("failed to initialize Helm Client: %v", err)
	}
	return helmActionConfig, nil
}

// ConvertCPUToCores 将资源量转换为以 core 为单位的 float64 值
func ConvertCPUToCores(cpu *resource.Quantity) float64 {
	return float64(cpu.MilliValue()) / 1000.0
}

// ConvertMemoryToGB 将资源量转换为以 GB 为单位的 float64 值
func ConvertMemoryToGB(memory *resource.Quantity) float64 {
	return float64(memory.Value()) / (1024.0 * 1024.0 * 1024.0)
}

// ConvertByteToGB 将字节转换为以 GB 为单位的 float64 值
func ConvertByteToGB(size float64) float64 {
	return size / (1024.0 * 1024.0 * 1024.0)
}

// RoundToDecimal 将浮点数四舍五入到指定小数位
func RoundToDecimal(val float64, decimalPlaces int) float64 {
	shift := math.Pow(10, float64(decimalPlaces))
	return math.Round(val*shift) / shift
}
