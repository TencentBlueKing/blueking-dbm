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

var addonTopologyEntity = &metaenitty.AddonTopologyEntity{
	AddonName:     "addon_name_01",
	AddonCategory: "addon_category_01",
	AddonType:     "addon_type_01",
	AddonVersion:  "addon_version_01",
	TopologyName:  "topology_name_01",
	TopologyAlias: "topology_alias_01",
	IsDefault:     true,
	Components:    "components_01",
	Relations:     "relations_01",
	Active:        true,
	Description:   "description_01",
}

var addonTopologyEntityList = []*metaenitty.AddonTopologyEntity{
	{
		AddonName:     "addon_name_01",
		AddonCategory: "addon_category_01",
		AddonType:     "addon_type",
		AddonVersion:  "addon_version_01",
		TopologyName:  "topology_name_01",
		TopologyAlias: "topology_alias_01",
		IsDefault:     true,
		Components:    "components_01",
		Relations:     "relations_01",
		Active:        true,
		Description:   "description_01",
	},
	{
		AddonName:     "addon_name_02",
		AddonCategory: "addon_category_02",
		AddonType:     "addon_type",
		AddonVersion:  "addon_version_02",
		TopologyName:  "topology_name_02",
		TopologyAlias: "topology_alias_02",
		IsDefault:     true,
		Components:    "components_02",
		Relations:     "relations_02",
		Active:        true,
		Description:   "description_02",
	},
}

type AddonTopologyProviderTestSuite struct {
	suite.Suite
	mySqlContainer        *testhelper.MySQLContainerWrapper
	addonTopologyProvider provider.AddonTopologyProvider
	ctx                   context.Context
}

func (suite *AddonTopologyProviderTestSuite) SetupSuite() {
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
	suite.addonTopologyProvider = provider.NewAddonTopologyProvider(dbAccess)
}

func (suite *AddonTopologyProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonTopologyProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonTopology, &model.AddonTopologyModel{})
}

func TestAddonTopologyProvider(t *testing.T) {
	suite.Run(t, new(AddonTopologyProviderTestSuite))
}

func (suite *AddonTopologyProviderTestSuite) TestCreate() {
	t := suite.T()
	entity, err := suite.addonTopologyProvider.Create(addonTopologyEntity)
	assert.NoError(t, err)
	assert.NotZero(t, entity.ID)
	assert.Equal(t, addonTopologyEntity.AddonName, entity.AddonName)
	assert.Equal(t, addonTopologyEntity.AddonCategory, entity.AddonCategory)
	assert.Equal(t, addonTopologyEntity.AddonType, entity.AddonType)
	assert.Equal(t, addonTopologyEntity.AddonVersion, entity.AddonVersion)
	assert.Equal(t, addonTopologyEntity.TopologyName, entity.TopologyName)
	assert.Equal(t, addonTopologyEntity.TopologyAlias, entity.TopologyAlias)
	assert.Equal(t, addonTopologyEntity.IsDefault, entity.IsDefault)
	assert.Equal(t, addonTopologyEntity.Components, entity.Components)
	assert.Equal(t, addonTopologyEntity.Relations, entity.Relations)
	assert.Equal(t, addonTopologyEntity.Active, entity.Active)
	assert.Equal(t, addonTopologyEntity.Description, entity.Description)
}

func (suite *AddonTopologyProviderTestSuite) TestFindByID() {
	t := suite.T()
	createdEntity, err := suite.addonTopologyProvider.Create(addonTopologyEntity)
	assert.NoError(t, err)
	assert.NotZero(t, createdEntity.ID)

	foundEntity, err := suite.addonTopologyProvider.FindByID(createdEntity.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundEntity)
	assert.Equal(t, createdEntity.ID, foundEntity.ID)
	assert.Equal(t, createdEntity.AddonName, foundEntity.AddonName)
	assert.Equal(t, createdEntity.AddonCategory, foundEntity.AddonCategory)
	assert.Equal(t, createdEntity.AddonType, foundEntity.AddonType)
	assert.Equal(t, createdEntity.AddonVersion, foundEntity.AddonVersion)
	assert.Equal(t, createdEntity.TopologyName, foundEntity.TopologyName)
	assert.Equal(t, createdEntity.TopologyAlias, foundEntity.TopologyAlias)
	assert.Equal(t, createdEntity.IsDefault, foundEntity.IsDefault)
	assert.Equal(t, createdEntity.Components, foundEntity.Components)
	assert.Equal(t, createdEntity.Relations, foundEntity.Relations)
	assert.Equal(t, createdEntity.Active, foundEntity.Active)
	assert.Equal(t, createdEntity.Description, foundEntity.Description)
}

func (suite *AddonTopologyProviderTestSuite) TestFindByParams() {
	t := suite.T()
	for _, entity := range addonTopologyEntityList {
		result, err := suite.addonTopologyProvider.Create(entity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	params := &metaenitty.AddonTopologyQueryParams{
		AddonType: "addon_type",
	}

	foundEntities, err := suite.addonTopologyProvider.FindByParams(params)
	assert.NoError(t, err)
	assert.Equal(t, 2, len(foundEntities))

	addonNames := make(map[string]bool)
	for _, addon := range foundEntities {
		addonNames[addon.AddonName] = true
	}

	for _, addon := range addonTopologyEntityList {
		assert.True(t, addonNames[addon.AddonName], addon.AddonName)
	}

}
