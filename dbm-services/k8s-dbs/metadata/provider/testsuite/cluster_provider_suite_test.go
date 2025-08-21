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

package testsuite

import (
	"context"
	commentity "k8s-dbs/common/entity"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	metaenitty "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	metaprovider "k8s-dbs/metadata/provider"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var K8sCrdClusterEntity = &metaenitty.K8sCrdClusterEntity{
	AddonID:             uint64(1),
	AddonClusterVersion: "addon_cluster_version_01",
	ServiceVersion:      "service_version_01",
	TopoName:            "topo_name_01",
	TerminationPolicy:   "termination_policy_01",
	K8sClusterConfigID:  uint64(1),
	RequestID:           "request_id_01",
	ClusterName:         "cluster_name_01",
	ClusterAlias:        "cluster_alias_01",
	Namespace:           "namespace_01",
	BkBizID:             uint64(1),
	BkBizName:           "bk_biz_name_01",
	BkAppAbbr:           "bk_app_abbr_01",
	BkAppCode:           "bk_app_code_01",
	Status:              "status_01",
	Description:         "description_01",
}

var K8sCrdClusterEntityList = []*metaenitty.K8sCrdClusterEntity{
	{
		AddonID:             uint64(1),
		AddonClusterVersion: "addon_cluster_version_01",
		ServiceVersion:      "service_version_01",
		TopoName:            "topo_name_01",
		TerminationPolicy:   "termination_policy_01",
		K8sClusterConfigID:  uint64(1),
		RequestID:           "request_id_01",
		ClusterName:         "cluster_name_01",
		ClusterAlias:        "cluster_alias_01",
		Namespace:           "namespace_01",
		BkBizID:             uint64(1),
		BkBizName:           "bk_biz_name_01",
		BkAppAbbr:           "bk_app_abbr_01",
		BkAppCode:           "bk_app_code_01",
		Status:              "status_01",
		Description:         "description_01",
	},
	{
		AddonID:             uint64(2),
		AddonClusterVersion: "addon_cluster_version_02",
		ServiceVersion:      "service_version_02",
		TopoName:            "topo_name_02",
		TerminationPolicy:   "termination_policy_02",
		K8sClusterConfigID:  uint64(2),
		RequestID:           "request_id_02",
		ClusterName:         "cluster_name_02",
		ClusterAlias:        "cluster_alias_02",
		Namespace:           "namespace_02",
		BkBizID:             uint64(2),
		BkBizName:           "bk_biz_name_02",
		BkAppAbbr:           "bk_app_abbr_02",
		BkAppCode:           "bk_app_code_02",
		Status:              "status_02",
		Description:         "description_02",
	},
}

type ClusterProviderTestSuite struct {
	suite.Suite
	mySqlContainer        *testhelper.MySQLContainerWrapper
	clusterProvider       provider.K8sCrdClusterProvider
	addonTopologyProvider provider.AddonTopologyProvider
	addonStorageProvider  provider.K8sCrdStorageAddonProvider
	clusterConfigProvider provider.K8sClusterConfigProvider
	ctx                   context.Context
}

func (suite *ClusterProviderTestSuite) SetupSuite() {
	suite.ctx = context.Background()
	mySqlContainer, err := testhelper.NewMySQLContainerWrapper(suite.ctx)
	if err != nil {
		log.Fatal(err)
	}
	suite.mySqlContainer = mySqlContainer
	db, err := testhelper.InitDBConnection(mySqlContainer.ConnStr)
	if err != nil {
		log.Fatal(err)
	}
	clusterDbAccess := dbaccess.NewCrdClusterDbAccess(db)
	addonMetaDbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)
	clusterTagDbAccess := dbaccess.NewK8sCrdClusterTagDbAccess(db)
	k8sClusterConfigDbAccess := dbaccess.NewK8sClusterConfigDbAccess(db)
	clusterTopologyDbAccess := dbaccess.NewAddonTopologyDbAccess(db)
	clusterProviderBuilder := metaprovider.K8sCrdClusterProviderBuilder{}
	suite.clusterProvider, err = provider.NewK8sCrdClusterProvider(
		clusterProviderBuilder.WithClusterDbAccess(clusterDbAccess),
		clusterProviderBuilder.WithAddonDbAccess(addonMetaDbAccess),
		clusterProviderBuilder.WithK8sClusterConfigDbAccess(k8sClusterConfigDbAccess),
		clusterProviderBuilder.WithClusterTagDbAccess(clusterTagDbAccess),
		clusterProviderBuilder.WithAddonTopologyDbAccess(clusterTopologyDbAccess),
	)
	suite.addonStorageProvider = provider.NewK8sCrdStorageAddonProvider(addonMetaDbAccess)
	suite.clusterConfigProvider = provider.NewK8sClusterConfigProvider(k8sClusterConfigDbAccess)
	if err != nil {
		log.Fatal(err)
	}
}

func (suite *ClusterProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ClusterProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sCrdCluster, &model.K8sCrdClusterModel{})
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sCrdStorageAddon, &model.K8sCrdStorageAddonModel{})
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sCrdClusterTag, &model.K8sCrdClusterTagModel{}) // todo
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sClusterConfig, &model.K8sClusterConfigModel{}) // todo
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonTopology, &model.AddonTopologyModel{})
}

func TestClusterProvider(t *testing.T) {
	suite.Run(t, new(ClusterProviderTestSuite))
}

func (suite *ClusterProviderTestSuite) TestCreateCluster() {
	t := suite.T()
	result, err := suite.clusterProvider.CreateCluster(K8sCrdClusterEntity)
	assert.NoError(t, err)
	assert.NotZero(t, result.ID)
	assert.Equal(t, K8sCrdClusterEntity.AddonID, result.AddonID)
	assert.Equal(t, K8sCrdClusterEntity.AddonClusterVersion, result.AddonClusterVersion)
	assert.Equal(t, K8sCrdClusterEntity.ServiceVersion, result.ServiceVersion)
	assert.Equal(t, K8sCrdClusterEntity.TopoName, result.TopoName)
	assert.Equal(t, K8sCrdClusterEntity.TerminationPolicy, result.TerminationPolicy)
	assert.Equal(t, K8sCrdClusterEntity.K8sClusterConfigID, result.K8sClusterConfigID)
	assert.Equal(t, K8sCrdClusterEntity.RequestID, result.RequestID)
	assert.Equal(t, K8sCrdClusterEntity.ClusterName, result.ClusterName)
	assert.Equal(t, K8sCrdClusterEntity.ClusterAlias, result.ClusterAlias)
	assert.Equal(t, K8sCrdClusterEntity.Namespace, result.Namespace)
	assert.Equal(t, K8sCrdClusterEntity.BkBizID, result.BkBizID)
	assert.Equal(t, K8sCrdClusterEntity.BkBizName, result.BkBizName)
	assert.Equal(t, K8sCrdClusterEntity.BkAppAbbr, result.BkAppAbbr)
	assert.Equal(t, K8sCrdClusterEntity.BkAppCode, result.BkAppCode)
	assert.Equal(t, K8sCrdClusterEntity.Status, result.Status)
	assert.Equal(t, K8sCrdClusterEntity.Description, result.Description)
}

func (suite *ClusterProviderTestSuite) TestDeleteClusterByID() {
	t := suite.T()
	addedEntity, err := suite.clusterProvider.CreateCluster(K8sCrdClusterEntity)
	assert.NoError(t, err)

	rows, err := suite.clusterProvider.DeleteClusterByID(addedEntity.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ClusterProviderTestSuite) TestFindClusterByID() {
	t := suite.T()
	addedEntity, err := suite.clusterProvider.CreateCluster(K8sCrdClusterEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addedEntity.ID)

	addon, err := suite.addonStorageProvider.CreateStorageAddon(addonDbsContext, k8sCrdStorageAddonEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addon.ID)

	config, err := suite.clusterConfigProvider.CreateConfig(k8sClusterConfigEntity)
	assert.NoError(t, err)
	assert.NotZero(t, config.ID)

	foundEntity, err := suite.clusterProvider.FindClusterByID(addedEntity.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundEntity)
	assert.Equal(t, addedEntity.ID, foundEntity.ID)
	assert.Equal(t, addedEntity.AddonID, foundEntity.AddonID)
	assert.Equal(t, addedEntity.AddonClusterVersion, foundEntity.AddonClusterVersion)
	assert.Equal(t, addedEntity.ServiceVersion, foundEntity.ServiceVersion)
	assert.Equal(t, addedEntity.TopoName, foundEntity.TopoName)
	assert.Equal(t, addedEntity.TerminationPolicy, foundEntity.TerminationPolicy)
	assert.Equal(t, addedEntity.K8sClusterConfigID, foundEntity.K8sClusterConfigID)
	assert.Equal(t, addedEntity.RequestID, foundEntity.RequestID)
	assert.Equal(t, addedEntity.ClusterName, foundEntity.ClusterName)
	assert.Equal(t, addedEntity.ClusterAlias, foundEntity.ClusterAlias)
	assert.Equal(t, addedEntity.Namespace, foundEntity.Namespace)
	assert.Equal(t, addedEntity.BkBizID, foundEntity.BkBizID)
	assert.Equal(t, addedEntity.BkBizName, foundEntity.BkBizName)
	assert.Equal(t, addedEntity.BkAppAbbr, foundEntity.BkAppAbbr)
	assert.Equal(t, addedEntity.BkAppCode, foundEntity.BkAppCode)
	assert.Equal(t, addedEntity.Status, foundEntity.Status)
	assert.Equal(t, addedEntity.Description, foundEntity.Description)
}

func (suite *ClusterProviderTestSuite) TestFindByParams() {
	t := suite.T()
	for _, entity := range K8sCrdClusterEntityList {
		result, err := suite.clusterProvider.CreateCluster(entity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	for _, entity := range k8sCrdStorageAddonEntityList {
		result, err := suite.addonStorageProvider.CreateStorageAddon(addonDbsContext, &entity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	params := &metaenitty.ClusterQueryParams{
		ClusterName: "cluster_name_01",
	}
	foundEntity, err := suite.clusterProvider.FindByParams(params)
	assert.NoError(t, err)
	assert.NotNil(t, foundEntity)
	assert.Equal(t, K8sCrdClusterEntityList[0].ClusterName, foundEntity.ClusterName)
	assert.Equal(t, K8sCrdClusterEntityList[0].AddonID, foundEntity.AddonID)
	assert.Equal(t, K8sCrdClusterEntityList[0].AddonClusterVersion, foundEntity.AddonClusterVersion)
	assert.Equal(t, K8sCrdClusterEntityList[0].ServiceVersion, foundEntity.ServiceVersion)
	assert.Equal(t, K8sCrdClusterEntityList[0].TopoName, foundEntity.TopoName)
	assert.Equal(t, K8sCrdClusterEntityList[0].TerminationPolicy, foundEntity.TerminationPolicy)
	assert.Equal(t, K8sCrdClusterEntityList[0].K8sClusterConfigID, foundEntity.K8sClusterConfigID)
	assert.Equal(t, K8sCrdClusterEntityList[0].RequestID, foundEntity.RequestID)
	assert.Equal(t, K8sCrdClusterEntityList[0].ClusterAlias, foundEntity.ClusterAlias)
	assert.Equal(t, K8sCrdClusterEntityList[0].Namespace, foundEntity.Namespace)
	assert.Equal(t, K8sCrdClusterEntityList[0].BkBizID, foundEntity.BkBizID)
	assert.Equal(t, K8sCrdClusterEntityList[0].BkBizName, foundEntity.BkBizName)
	assert.Equal(t, K8sCrdClusterEntityList[0].BkAppAbbr, foundEntity.BkAppAbbr)
	assert.Equal(t, K8sCrdClusterEntityList[0].BkAppCode, foundEntity.BkAppCode)
	assert.Equal(t, K8sCrdClusterEntityList[0].Status, foundEntity.Status)
	assert.Equal(t, K8sCrdClusterEntityList[0].Description, foundEntity.Description)
}

func (suite *ClusterProviderTestSuite) TestListClusters() {
	t := suite.T()
	for _, entity := range K8sCrdClusterEntityList {
		result, err := suite.clusterProvider.CreateCluster(entity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	for _, entity := range k8sCrdStorageAddonEntityList {
		addon, err := suite.addonStorageProvider.CreateStorageAddon(addonDbsContext, &entity)
		assert.NoError(t, err)
		assert.NotZero(t, addon.ID)
	}

	for _, entity := range k8sClusterConfigEntityList {
		config, err := suite.clusterConfigProvider.CreateConfig(entity)
		assert.NoError(t, err)
		assert.NotZero(t, config.ID)
	}

	params := &metaenitty.ClusterQueryParams{
		AddonClusterVersion: "addon_cluster_version_01",
	}
	pagin := commentity.Pagination{
		Page:  0,
		Limit: 10,
	}
	results, _, err := suite.clusterProvider.ListClusters(params, &pagin)
	assert.NoError(t, err)

	clusters := make(map[string]bool)
	for _, cluster := range results {
		clusters[cluster.AddonClusterVersion] = true
	}

	for _, cluster := range K8sCrdClusterEntityList {
		assert.True(t, clusters[cluster.AddonClusterVersion], cluster.AddonClusterVersion)
	}

}

func (suite *ClusterProviderTestSuite) TestUpdateCluster() {
	t := suite.T()
	addedEntity, err := suite.clusterProvider.CreateCluster(K8sCrdClusterEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addedEntity.ID)

	addedEntity.ClusterAlias = "updated_cluster_alias"
	rows, err := suite.clusterProvider.UpdateCluster(addedEntity)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ClusterProviderTestSuite) TestFindClusterTopology() {
	t := suite.T()
	addedEntity, err := suite.clusterProvider.CreateCluster(K8sCrdClusterEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addedEntity.ID)

	addon, err := suite.addonStorageProvider.CreateStorageAddon(addonDbsContext, k8sCrdStorageAddonEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addon.ID)

	config, err := suite.clusterConfigProvider.CreateConfig(k8sClusterConfigEntity)
	assert.NoError(t, err)
	assert.NotZero(t, config.ID)

	topology, err := suite.clusterProvider.FindClusterTopology(addedEntity.ID)
	assert.NoError(t, err)
	assert.NotNil(t, topology)
	assert.Equal(t, addedEntity.ClusterName, topology.ClusterName)
	assert.Equal(t, addedEntity.ClusterAlias, topology.ClusterAlias)
	assert.Equal(t, addedEntity.Namespace, topology.Namespace)
	assert.Equal(t, addedEntity.TopoName, topology.TopoName)
	assert.Equal(t, addedEntity.Status, topology.Status)
}
