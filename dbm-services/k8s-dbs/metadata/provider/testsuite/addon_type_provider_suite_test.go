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

var addonTypeEntity = &metaenitty.AddonTypeEntity{
	CategoryID:  1,
	TypeName:    "addon_type_01",
	TypeAlias:   "addon_type_alias_01",
	Active:      true,
	Description: "addon_type_description_01",
}

var addonTypeEntityList = []metaenitty.AddonTypeEntity{
	{
		CategoryID:  1,
		TypeName:    "type_name_01",
		TypeAlias:   "type_alias_01",
		Active:      true,
		Description: "description_01",
	},
	{
		CategoryID:  2,
		TypeName:    "type_name_02",
		TypeAlias:   "type_alias_02",
		Active:      true,
		Description: "description_02",
	},
}

type AddonTypeProviderTestSuite struct {
	suite.Suite
	mySqlContainer        *testhelper.MySQLContainerWrapper
	addonTypeProvider     provider.AddonTypeProvider
	addonCategoryProvider provider.AddonCategoryProvider
	ctx                   context.Context
}

func (suite *AddonTypeProviderTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewAddonTypeDbAccess(db)
	categoryDbAccess := dbaccess.NewAddonCategoryDbAccess(db)
	suite.addonTypeProvider = provider.NewAddonTypeProvider(dbAccess, categoryDbAccess)
	suite.addonCategoryProvider = provider.NewAddonCategoryProvider(categoryDbAccess, dbAccess)
}

func (suite *AddonTypeProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonTypeProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonType, &model.AddonTypeModel{})
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonCategory, &model.AddonCategoryModel{})
}

func TestAddonTypeProvider(t *testing.T) {
	suite.Run(t, new(AddonTypeProviderTestSuite))
}

func (suite *AddonTypeProviderTestSuite) TestCreate() {
	t := suite.T()
	addonType, err := suite.addonTypeProvider.Create(addonTypeEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addonType.ID)
	assert.Equal(t, addonTypeEntity.CategoryID, addonType.CategoryID)
	assert.Equal(t, addonTypeEntity.TypeName, addonType.TypeName)
	assert.Equal(t, addonTypeEntity.TypeAlias, addonType.TypeAlias)
	assert.Equal(t, addonTypeEntity.Active, addonType.Active)
	assert.Equal(t, addonTypeEntity.Description, addonType.Description)
}

func (suite *AddonTypeProviderTestSuite) TestListByLimit() {
	t := suite.T()
	for _, entity := range addonTypeEntityList {
		result, err := suite.addonTypeProvider.Create(&entity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	for _, entity := range addonCategoryEntityList {
		result, err := suite.addonCategoryProvider.Create(&entity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	typeEntities, err := suite.addonTypeProvider.ListByLimit(10)
	assert.NoError(t, err)

	addonNames := make(map[string]bool)
	for _, addon := range typeEntities {
		addonNames[addon.TypeName] = true
	}

	for _, addon := range addonTypeEntityList {
		assert.True(t, addonNames[addon.TypeName], addon.TypeName)
	}
}
