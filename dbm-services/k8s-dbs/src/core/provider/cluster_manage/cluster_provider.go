package cluster_manage

import (
	"context"
	"fmt"
	"k8s-dbs/src/core/client"
	"k8s-dbs/src/core/entity"
	"k8s-dbs/src/metadata/provider"
	entitys "k8s-dbs/src/metadata/provider/entity"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

type ClusterProvider struct {
	clusterMetaProvider          provider.K8sCrdClusterProvider
	componentMetaProvider        provider.K8sCrdComponentProvider
	cdMetaProvider               provider.K8sCrdClusterDefinitionProvider
	cmpdMetaProvider             provider.K8sCrdComponentDefinitionProvider
	cmpvMetaProvider             provider.K8sCrdComponentVersionProvider
	k8sClusterConfigMetaProvider provider.K8sClusterConfigProvider
}

func NewClusterService(
	clusterMetaProvider provider.K8sCrdClusterProvider,
	componentMetaProvider provider.K8sCrdComponentProvider,
	cdMetaProvider provider.K8sCrdClusterDefinitionProvider,
	cmpdMetaProvider provider.K8sCrdComponentDefinitionProvider,
	cmpvMetaProvider provider.K8sCrdComponentVersionProvider,
	k8sClusterConfigMetaProvider provider.K8sClusterConfigProvider,
) *ClusterProvider {
	return &ClusterProvider{
		clusterMetaProvider:          clusterMetaProvider,
		componentMetaProvider:        componentMetaProvider,
		cdMetaProvider:               cdMetaProvider,
		cmpdMetaProvider:             cmpdMetaProvider,
		cmpvMetaProvider:             cmpvMetaProvider,
		k8sClusterConfigMetaProvider: k8sClusterConfigMetaProvider,
	}
}

func (c *ClusterProvider) CreateCluster(request *entity.Request) error {
	k8sClusterConfig, err := c.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}

	k8sClient, err := client.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return fmt.Errorf("failed to create k8sClient: %w", err)
	}

	if err = verifyAddonExists(request, k8sClient); err != nil {
		return fmt.Errorf("failed to verify addon exists: %w", err)
	}

	clusterEntity, compEntityList, err := c.getEntityFromReq(request)
	if err != nil {
		return fmt.Errorf("failed to get cluster entity: %w", err)
	}

	clusterEntity.K8sClusterConfigId = k8sClusterConfig.ID
	addedClusterEntity, err := c.clusterMetaProvider.CreateCluster(clusterEntity)
	if err != nil {
		return fmt.Errorf("failed to create cluster: %w", err)
	}

	for _, compEntity := range compEntityList {
		compEntity.CrdClusterID = addedClusterEntity.ID
		_, err = c.componentMetaProvider.CreateComponent(compEntity)
		if err != nil {
			return fmt.Errorf("failed to create component: %w", err)
		}
	}

	if err = client.CreateStorageAddonCluster(k8sClient, request); err != nil {
		return fmt.Errorf("failed to create cluster: %w", err)
	}
	return nil
}

func (c *ClusterProvider) DeleteCluster(request *entity.Request) error {
	k8sClusterConfig, err := c.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := client.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return fmt.Errorf("failed to create k8sClient: %w", err)
	}
	params := map[string]interface{}{
		"cluster_name": request.ClusterName,
		"namespace":    request.Namespace,
	}
	clusterEntity, err := c.clusterMetaProvider.FindByParams(params)
	if err != nil {
		return err
	}
	_, err = c.clusterMetaProvider.DeleteClusterById(clusterEntity.ID)
	if err != nil {
		return err
	}
	err = client.DeleteStorageAddonCluster(k8sClient, request.ClusterName, request.Namespace)
	if err != nil {
		return err
	}
	return nil
}

func (c *ClusterProvider) DescribeCluster(request *entity.Request) (*entity.ClusterResponseData, error) {
	k8sClusterConfig, err := c.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := client.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}
	cluster, err := k8sClient.DynamicClient.
		Resource(kbtypes.ClusterGVR()).
		Namespace(request.Namespace).
		Get(context.TODO(), request.ClusterName, metav1.GetOptions{})
	if err != nil {
		return nil, err
	}
	dataResponse, err := entity.GetClusterResponseData(cluster)
	if err != nil {
		return nil, err
	}
	return dataResponse, nil
}

func (c *ClusterProvider) GetClusterStatus(request *entity.Request) (*entity.ClusterStatus, error) {
	k8sClusterConfig, err := c.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := client.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}

	cluster, err := k8sClient.DynamicClient.
		Resource(kbtypes.ClusterGVR()).
		Namespace(request.Namespace).
		Get(context.TODO(), request.ClusterName, metav1.GetOptions{})
	if err != nil {
		return nil, err
	}
	dataResponse, err := entity.GetClusterResponseData(cluster)
	if err != nil {
		return nil, err
	}
	return dataResponse.ClusterStatus, nil
}

func (c *ClusterProvider) getEntityFromReq(request *entity.Request) (*entitys.K8sCrdClusterEntity, []*entitys.K8sCrdComponentEntity, error) {
	/*	metaData := metav1.ObjectMeta{
		Name:        request.Metadata.ClusterName,
		Namespace:   request.Metadata.Namespace,
		Labels:      request.Metadata.Labels,
		Annotations: request.Metadata.Annotations,
	}*/

	/*metaDataJSON, err := json.Marshal(metaData)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to marshal metaData to JSON: %w", err)
	}

	specJson, err := json.Marshal(request.ComponentMap)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to marshal spec to JSON: %w", err)
	}*/

	clusterEntity := &entitys.K8sCrdClusterEntity{
		ClusterName: request.ClusterName,
		Namespace:   request.Namespace,
		//Metadata:    string(metaDataJSON),
		//Spec:        string(specJson),
	}

	var compEntityList []*entitys.K8sCrdComponentEntity
	for compTopoName := range request.ComponentMap {
		compName := request.Metadata.ClusterName + "-" + compTopoName
		/*metaData = metav1.ObjectMeta{
			Name:      compName,
			Namespace: request.Metadata.Namespace,
		}*/
		/*metaDataJSON, err = json.Marshal(metaData)
		if err != nil {
			return nil, nil, fmt.Errorf("failed to marshal metaData to JSON: %w", err)
		}
		specJson, err = json.Marshal(comp)
		if err != nil {
			return nil, nil, fmt.Errorf("failed to marshal spec to JSON: %w", err)
		}*/
		componentEntity := &entitys.K8sCrdComponentEntity{
			ComponentName: compName,
			//Metadata:      string(metaDataJSON),
			//Spec:          string(specJson),
		}
		compEntityList = append(compEntityList, componentEntity)
	}

	return clusterEntity, compEntityList, nil
}

func verifyAddonExists(request *entity.Request, k8sClient *client.K8sClient) error {
	targetChartFullName := request.StorageAddonType + "-" + request.StorageAddonVersion
	isCreated, err := client.StorageAddonIsCreated(k8sClient, targetChartFullName)
	if err != nil {
		return fmt.Errorf("failed to verify existence of storage addon chart %q: %w", targetChartFullName, err)
	}
	if !isCreated {
		return fmt.Errorf("storage addon chart %q does not exist", targetChartFullName)
	}
	return nil
}
