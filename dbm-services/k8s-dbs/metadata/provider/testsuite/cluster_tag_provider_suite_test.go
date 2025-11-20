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
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	metaenitty "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var k8sCrdClusterTagEntity = &metaenitty.K8sCrdClusterTagEntity{
	CrdClusterID: uint64(1),
	ClusterTag:   "tag_01",
	Active:       true,
}

var k8sCrdClusterTagEntityList = []*metaenitty.K8sCrdClusterTagEntity{
	{
		CrdClusterID: uint64(2),
		ClusterTag:   "tag_02",
		Active:       true,
	},
	{
		CrdClusterID: uint64(2),
		ClusterTag:   "tag_02",
		Active:       true,
	},
}

type ClusterTagProviderTestSuite struct {
	suite.Suite
	mySqlContainer  *testhelper.MySQLContainerWrapper
	clusterProvider provider.K8sCrdClusterTagProvider
	ctx             context.Context
}

func (suite *ClusterTagProviderTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewK8sCrdClusterTagDbAccess(db)
	clusterProvider := provider.NewK8sCrdClusterTagProvider(dbAccess)
	suite.clusterProvider = clusterProvider
}

func (suite *ClusterTagProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ClusterTagProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sCrdClusterTag, &model.K8sCrdClusterTagModel{})
}

func TestClusterTagProvider(t *testing.T) {
	suite.Run(t, new(ClusterTagProviderTestSuite))
}

func (suite *ClusterTagProviderTestSuite) TestCreate() {
	t := suite.T()
	entity, err := suite.clusterProvider.Create(addonDbsContext, k8sCrdClusterTagEntity)
	assert.NoError(t, err)
	assert.Equal(t, k8sCrdClusterTagEntity.CrdClusterID, entity.CrdClusterID)
	assert.Equal(t, k8sCrdClusterTagEntity.ClusterTag, entity.ClusterTag)
	assert.Equal(t, k8sCrdClusterTagEntity.Active, entity.Active)
}

func (suite *ClusterTagProviderTestSuite) TestBatchCreate() {
	t := suite.T()
	rows, err := suite.clusterProvider.BatchCreate(addonDbsContext, k8sCrdClusterTagEntityList)
	assert.NoError(t, err)
	assert.Equal(t, uint64(2), rows)

}

func (suite *ClusterTagProviderTestSuite) TestDeleteByClusterID() {
	t := suite.T()
	entity, err := suite.clusterProvider.Create(addonDbsContext, k8sCrdClusterTagEntity)
	assert.NoError(t, err)
	assert.NotZero(t, entity.ID)

	rows, err := suite.clusterProvider.DeleteByClusterID(addonDbsContext, entity.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ClusterTagProviderTestSuite) TestFindByClusterID() {
	t := suite.T()
	entity, err := suite.clusterProvider.Create(addonDbsContext, k8sCrdClusterTagEntity)
	assert.NoError(t, err)
	assert.NotZero(t, entity.ID)

	entities, err := suite.clusterProvider.FindByClusterID(addonDbsContext, entity.CrdClusterID)
	assert.NoError(t, err)
	assert.Equal(t, entity.CrdClusterID, entities[0].CrdClusterID)
	assert.Equal(t, entity.ClusterTag, entities[0].ClusterTag)
	assert.Equal(t, entity.Active, entities[0].Active)
}
