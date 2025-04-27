package client

import (
	"context"
	"fmt"
	"k8s-dbs/src/core/client/constants"
	entitys "k8s-dbs/src/metadata/provider/entity"
	"log"

	"helm.sh/helm/v3/pkg/action"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/cli-runtime/pkg/genericclioptions"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
)

type K8sClient struct {
	RestConfig    *rest.Config
	ClientSet     *kubernetes.Clientset
	DynamicClient dynamic.Interface
}

func NewK8sClient(k8sConfig *entitys.K8sClusterConfigEntity) (*K8sClient, error) {
	// 构建 Kubernetes 客户端配置
	config := &rest.Config{
		Host:        k8sConfig.APIServerURL,
		BearerToken: k8sConfig.Token,
		TLSClientConfig: rest.TLSClientConfig{
			Insecure: true,
		},
	}
	// create clientSet
	clientSet, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, err
	}
	dynamicClient, err := dynamic.NewForConfig(config)
	if err != nil {
		return nil, err
	}
	k8sClient := K8sClient{
		RestConfig:    config,
		ClientSet:     clientSet,
		DynamicClient: dynamicClient,
	}

	err = k8sClient.verifyConnection()
	if err != nil {
		return nil, err
	}
	return &k8sClient, nil
}

func (k *K8sClient) verifyConnection() error {
	// Try listing all namespaces in the cluster
	_, err := k.ClientSet.CoreV1().Namespaces().List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		return fmt.Errorf("failed to connect to the k8sClient: %v", err)
	}
	return nil
}

func (k *K8sClient) buildHelmConfig(namespace string) (*action.Configuration, error) {
	// Create ConfigFlags that conform to the RESTClientGetter interface
	configFlags := genericclioptions.NewConfigFlags(true)
	configFlags.WrapConfigFn = func(c *rest.Config) *rest.Config {
		return k.RestConfig // 复用已有的k8s配置
	}
	// Initialize Helm configuration
	helmActionConfig := new(action.Configuration)
	if err := helmActionConfig.Init(
		configFlags,
		namespace,
		constants.HelmDriver,
		func(format string, v ...interface{}) {
			log.Printf(format, v...)
		},
	); err != nil {
		return nil, fmt.Errorf("failed to initialize Helm Client: %v", err)
	}
	return helmActionConfig, nil
}
