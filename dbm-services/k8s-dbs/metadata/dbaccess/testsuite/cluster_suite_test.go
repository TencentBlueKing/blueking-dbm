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
	"k8s-dbs/common/entity"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	entitys "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	models "k8s-dbs/metadata/model"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var clusterSample = &models.K8sCrdClusterModel{
	AddonID:            1,
	K8sClusterConfigID: 1,
	RequestID:          "req-12345",
	ClusterName:        "test-cluster",
	ClusterAlias:       "Test Cluster",
	Namespace:          "default",
}

var batchClusterSamples = []*models.K8sCrdClusterModel{
	{
		AddonID:            1,
		K8sClusterConfigID: 1,
		RequestID:          "req-11111",
		ClusterName:        "redis-cluster",
		ClusterAlias:       "Redis Cluster",
		Namespace:          "redis-ns",
	},
	{
		AddonID:            2,
		K8sClusterConfigID: 2,
		RequestID:          "req-22222",
		ClusterName:        "mongodb-cluster",
		ClusterAlias:       "MongoDB Cluster",
		Namespace:          "mongodb-ns",
	},
}

type ClusterDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.K8sCrdClusterDbAccess
	ctx            context.Context
}

func (suite *ClusterDbAccessTestSuite) SetupSuite() {
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
	suite.dbAccess = dbaccess.NewCrdClusterDbAccess(db)
}

func (suite *ClusterDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ClusterDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sCrdCluster, &models.K8sCrdClusterModel{})
}

func (suite *ClusterDbAccessTestSuite) TestCreateCluster() {
	t := suite.T()
	cluster, err := suite.dbAccess.Create(clusterSample)
	assert.NoError(t, err)
	assert.NotZero(t, cluster.ID)
	assert.Equal(t, clusterSample.AddonID, cluster.AddonID)
	assert.Equal(t, clusterSample.ClusterName, cluster.ClusterName)
	assert.Equal(t, clusterSample.ClusterAlias, cluster.ClusterAlias)
	assert.Equal(t, clusterSample.Namespace, cluster.Namespace)
	assert.Equal(t, clusterSample.K8sClusterConfigID, cluster.K8sClusterConfigID)
	assert.Equal(t, clusterSample.RequestID, cluster.RequestID)
}

func (suite *ClusterDbAccessTestSuite) TestGetCluster() {
	t := suite.T()
	cluster, err := suite.dbAccess.Create(clusterSample)
	assert.NoError(t, err)

	fetched, err := suite.dbAccess.FindByID(cluster.ID)
	assert.NoError(t, err)
	assert.NotNil(t, fetched)
	assert.Equal(t, cluster.ID, fetched.ID)
	assert.Equal(t, cluster.ClusterName, fetched.ClusterName)
	assert.Equal(t, cluster.ClusterAlias, fetched.ClusterAlias)
	assert.Equal(t, cluster.Namespace, fetched.Namespace)
	assert.Equal(t, cluster.AddonID, fetched.AddonID)
	assert.Equal(t, cluster.K8sClusterConfigID, fetched.K8sClusterConfigID)
	assert.Equal(t, cluster.RequestID, fetched.RequestID)
}

func (suite *ClusterDbAccessTestSuite) TestFindClusterByParams() {
	t := suite.T()
	cluster, err := suite.dbAccess.Create(clusterSample)
	assert.NoError(t, err)

	params := &entitys.ClusterQueryParams{
		ClusterName: clusterSample.ClusterName,
		Namespace:   clusterSample.Namespace,
	}
	fetched, err := suite.dbAccess.FindByParams(params)
	assert.NoError(t, err)
	assert.NotNil(t, fetched)
	assert.Equal(t, fetched.ID, cluster.ID)
	assert.Equal(t, fetched.ClusterName, clusterSample.ClusterName)
	assert.Equal(t, fetched.Namespace, clusterSample.Namespace)
}

func (suite *ClusterDbAccessTestSuite) TestUpdateCluster() {
	t := suite.T()
	cluster, err := suite.dbAccess.Create(clusterSample)
	assert.NoError(t, err)
	assert.NotZero(t, cluster.ID)

	newCluster := &models.K8sCrdClusterModel{
		ID:                 cluster.ID,
		AddonID:            2,
		K8sClusterConfigID: 2,
		RequestID:          "req-updated",
		ClusterName:        "updated-cluster",
		ClusterAlias:       "Updated Cluster",
		Namespace:          "updated-ns",
	}
	rows, err := suite.dbAccess.Update(newCluster)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ClusterDbAccessTestSuite) TestDeleteCluster() {
	t := suite.T()
	cluster, err := suite.dbAccess.Create(clusterSample)
	assert.NoError(t, err)
	assert.NotZero(t, cluster.ID)

	rows, err := suite.dbAccess.DeleteByID(cluster.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ClusterDbAccessTestSuite) TestListClustersByPage() {
	t := suite.T()
	for _, sample := range batchClusterSamples {
		_, err := suite.dbAccess.Create(sample)
		assert.NoError(t, err)
	}

	params := &entitys.ClusterQueryParams{}
	pagination := &entity.Pagination{
		Page:  0,
		Limit: 10,
	}
	clusters, total, err := suite.dbAccess.ListByPage(params, pagination)
	assert.NoError(t, err)
	assert.Equal(t, uint64(len(batchClusterSamples)), total)
	assert.Equal(t, len(batchClusterSamples), len(clusters))

	clusterMap := make(map[string]models.K8sCrdClusterModel)
	for _, cluster := range clusters {
		clusterMap[cluster.ClusterName] = *cluster
	}

	for _, sample := range batchClusterSamples {
		fetchedCluster, ok := clusterMap[sample.ClusterName]
		assert.True(t, ok, "Cluster with name %s not found", sample.ClusterName)
		assert.Equal(t, sample.ClusterAlias, fetchedCluster.ClusterAlias)
		assert.Equal(t, sample.Namespace, fetchedCluster.Namespace)
		assert.Equal(t, sample.AddonID, fetchedCluster.AddonID)
		assert.Equal(t, sample.K8sClusterConfigID, fetchedCluster.K8sClusterConfigID)
	}
}

func TestClusterDbAccess(t *testing.T) {
	suite.Run(t, new(ClusterDbAccessTestSuite))
}
