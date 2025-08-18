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
	"k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var topologySample = &model.AddonTopologyModel{
	AddonName:     "test-addon",
	AddonCategory: "database",
	AddonType:     "mysql",
	AddonVersion:  "8.0",
	TopologyName:  "test-topology",
	TopologyAlias: "test-alias",
	Components:    `[]`,
	Relations:     `[]`,
}

var batchTopologySamples = []*model.AddonTopologyModel{
	{
		AddonName:     "test-addon-1",
		AddonCategory: "database",
		AddonType:     "mysql",
		AddonVersion:  "8.0",
		TopologyName:  "test-topology-1",
		TopologyAlias: "test-alias-1",
		Components:    `[]`,
		Relations:     `[]`,
	},
	{
		AddonName:     "test-addon-2",
		AddonCategory: "database",
		AddonType:     "redis",
		AddonVersion:  "6.0",
		TopologyName:  "test-topology-2",
		TopologyAlias: "test-alias-2",
		Components:    `[]`,
		Relations:     `[]`,
	},
}

var addonTopologyQueryParamsSample = &entity.AddonTopologyQueryParams{
	AddonCategory: "database",
	AddonType:     "mysql",
	AddonVersion:  "8.0",
	TopologyName:  "test-topology",
}

type AddonTopologyDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.AddonTopologyDbAccess
	ctx            context.Context
}

func (suite *AddonTopologyDbAccessTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewAddonTopologyDbAccess(db)
	suite.dbAccess = dbAccess
}

func (suite *AddonTopologyDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonTopologyDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonTopology, &model.AddonTopologyModel{})
}

func (suite *AddonTopologyDbAccessTestSuite) TestCreateAddonTopology() {
	t := suite.T()
	topology, err := suite.dbAccess.Create(topologySample)
	assert.NoError(t, err)
	assert.NotZero(t, topology.ID)
	assert.Equal(t, topologySample.AddonName, topology.AddonName)
	assert.Equal(t, topologySample.AddonCategory, topology.AddonCategory)
	assert.Equal(t, topologySample.AddonType, topology.AddonType)
	assert.Equal(t, topologySample.AddonVersion, topology.AddonVersion)
	assert.Equal(t, topologySample.TopologyName, topology.TopologyName)
	assert.Equal(t, topologySample.TopologyAlias, topology.TopologyAlias)
	assert.Equal(t, topologySample.Components, topology.Components)
	assert.Equal(t, topologySample.Relations, topology.Relations)
}

func (suite *AddonTopologyDbAccessTestSuite) TestGetAddonTopology() {
	t := suite.T()
	topology, err := suite.dbAccess.Create(topologySample)
	assert.NoError(t, err)
	assert.NotZero(t, topology.ID)

	foundTopology, err := suite.dbAccess.FindByID(topology.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundTopology)
	assert.Equal(t, topology.ID, foundTopology.ID)
	assert.Equal(t, topology.AddonName, foundTopology.AddonName)
	assert.Equal(t, topology.AddonCategory, foundTopology.AddonCategory)
	assert.Equal(t, topology.AddonType, foundTopology.AddonType)
	assert.Equal(t, topology.AddonVersion, foundTopology.AddonVersion)
	assert.Equal(t, topology.TopologyName, foundTopology.TopologyName)
	assert.Equal(t, topology.TopologyAlias, foundTopology.TopologyAlias)
	assert.Equal(t, topology.Components, foundTopology.Components)
	assert.Equal(t, topology.Relations, foundTopology.Relations)
}

func (suite *AddonTopologyDbAccessTestSuite) TestFindAddonTopologyByParams() {
	t := suite.T()
	topology, err := suite.dbAccess.Create(topologySample)
	assert.NoError(t, err)

	results, err := suite.dbAccess.FindByParams(addonTopologyQueryParamsSample)
	assert.NoError(t, err)
	assert.Len(t, results, 1)
	assert.Equal(t, topology.ID, results[0].ID)
	assert.Equal(t, topology.AddonName, results[0].AddonName)
}

func (suite *AddonTopologyDbAccessTestSuite) TestListAddonTopologyByLimit() {
	t := suite.T()
	for _, sample := range batchTopologySamples {
		_, err := suite.dbAccess.Create(sample)
		assert.NoError(t, err)
	}

	topologies, err := suite.dbAccess.ListByLimit(10)
	assert.NoError(t, err)
	assert.Equal(t, len(batchTopologySamples), len(topologies))

	topologyMap := make(map[string]model.AddonTopologyModel)
	for _, topology := range topologies {
		topologyMap[topology.TopologyName] = *topology
	}

	for _, sample := range batchTopologySamples {
		foundTopology, ok := topologyMap[sample.TopologyName]
		assert.True(t, ok, "Topology with name %s not found", sample.TopologyName)
		assert.Equal(t, sample.AddonName, foundTopology.AddonName)
		assert.Equal(t, sample.AddonCategory, foundTopology.AddonCategory)
		assert.Equal(t, sample.AddonType, foundTopology.AddonType)
		assert.Equal(t, sample.AddonVersion, foundTopology.AddonVersion)
		assert.Equal(t, sample.TopologyName, foundTopology.TopologyName)
		assert.Equal(t, sample.TopologyAlias, foundTopology.TopologyAlias)
		assert.Equal(t, sample.Components, foundTopology.Components)
		assert.Equal(t, sample.Relations, foundTopology.Relations)
	}
}

func TestAddonTopologyDbAccessTestSuite(t *testing.T) {
	suite.Run(t, new(AddonTopologyDbAccessTestSuite))
}
