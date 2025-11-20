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
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var clusterTagSample = &model.K8sCrdClusterTagModel{
	CrdClusterID: 1,
	ClusterTag:   "production",
}

var batchClusterTagSamples = []*model.K8sCrdClusterTagModel{
	{
		CrdClusterID: 1,
		ClusterTag:   "development",
	},
	{
		CrdClusterID: 2,
		ClusterTag:   "testing",
	},
}

type ClusterTagDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.K8sCrdClusterTagDbAccess
	ctx            context.Context
}

func (suite *ClusterTagDbAccessTestSuite) SetupSuite() {
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
	suite.dbAccess = dbAccess
}

func (suite *ClusterTagDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ClusterTagDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sCrdClusterTag, &model.K8sCrdClusterTagModel{})
}

func (suite *ClusterTagDbAccessTestSuite) TestCreateClusterTag() {
	t := suite.T()
	clusterTag, err := suite.dbAccess.Create(clusterTagSample)
	assert.NoError(t, err)
	assert.NotZero(t, clusterTag.ID)
	assert.Equal(t, clusterTagSample.CrdClusterID, clusterTag.CrdClusterID)
	assert.Equal(t, clusterTagSample.ClusterTag, clusterTag.ClusterTag)
}

func (suite *ClusterTagDbAccessTestSuite) TestDeleteClusterTagByClusterID() {
	t := suite.T()
	clusterTag, err := suite.dbAccess.Create(clusterTagSample)
	assert.NoError(t, err)
	assert.NotZero(t, clusterTag.ID)

	rows, err := suite.dbAccess.DeleteByClusterID(clusterTag.CrdClusterID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ClusterTagDbAccessTestSuite) TestFindClusterTagByClusterID() {
	t := suite.T()
	clusterTag, err := suite.dbAccess.Create(clusterTagSample)
	assert.NoError(t, err)
	assert.NotZero(t, clusterTag.ID)

	foundClusterTags, err := suite.dbAccess.FindByClusterID(clusterTag.CrdClusterID)
	assert.NoError(t, err)
	assert.NotEmpty(t, foundClusterTags)
	assert.Equal(t, clusterTag.CrdClusterID, foundClusterTags[0].CrdClusterID)
	assert.Equal(t, clusterTag.ClusterTag, foundClusterTags[0].ClusterTag)
}

func (suite *ClusterTagDbAccessTestSuite) TestBatchCreateClusterTag() {
	t := suite.T()
	rows, err := suite.dbAccess.BatchCreate(batchClusterTagSamples)
	assert.NoError(t, err)
	assert.Equal(t, uint64(2), rows)

	foundClusterTags, err := suite.dbAccess.FindByClusterID(batchClusterTagSamples[0].CrdClusterID)
	assert.NoError(t, err)
	assert.NotEmpty(t, foundClusterTags)
	assert.Equal(t, batchClusterTagSamples[0].ClusterTag, foundClusterTags[0].ClusterTag)
}

func TestClusterTagDbAccess(t *testing.T) {
	suite.Run(t, new(ClusterTagDbAccessTestSuite))
}
