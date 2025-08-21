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

var addonCategoryEntity = &metaenitty.AddonCategoryEntity{
	CategoryName:  "category_name_01",
	CategoryAlias: "category_alias_01",
	Active:        true,
	Description:   "description_01",
}

var addonCategoryEntityList = []metaenitty.AddonCategoryEntity{
	{
		CategoryName:  "category_name_01",
		CategoryAlias: "category_alias_01",
		Active:        true,
		Description:   "description_01",
	},
	{
		CategoryName:  "category_name_02",
		CategoryAlias: "category_alias_02",
		Active:        true,
		Description:   "description_02",
	},
}

type AddonCategoryProviderTestSuite struct {
	suite.Suite
	mySqlContainer        *testhelper.MySQLContainerWrapper
	addonCategoryProvider provider.AddonCategoryProvider
	addonTypeProvider     provider.AddonTypeProvider
	ctx                   context.Context
}

func (suite *AddonCategoryProviderTestSuite) SetupSuite() {
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
	addonCategoryDbAccess := dbaccess.NewAddonCategoryDbAccess(db)
	addonTypeDbAccess := dbaccess.NewAddonTypeDbAccess(db)
	categoryProvider := provider.NewAddonCategoryProvider(addonCategoryDbAccess, addonTypeDbAccess)
	typeProvider := provider.NewAddonTypeProvider(addonTypeDbAccess, addonCategoryDbAccess)
	suite.addonCategoryProvider = categoryProvider
	suite.addonTypeProvider = typeProvider
}

func (suite *AddonCategoryProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonCategoryProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonCategory, &model.AddonCategoryModel{})
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonType, &model.AddonTypeModel{})
}

func TestAddonCategoryProvider(t *testing.T) {
	suite.Run(t, new(AddonCategoryProviderTestSuite))
}

func (suite *AddonCategoryProviderTestSuite) TestCreate() {
	t := suite.T()
	result, err := suite.addonCategoryProvider.Create(addonCategoryEntity)
	assert.NoError(t, err)
	assert.NotNil(t, result.ID)
	assert.Equal(t, addonCategoryEntity.CategoryName, result.CategoryName)
	assert.Equal(t, addonCategoryEntity.CategoryAlias, result.CategoryAlias)
	assert.Equal(t, addonCategoryEntity.Active, result.Active)
	assert.Equal(t, addonCategoryEntity.Description, result.Description)
}

func (suite *AddonCategoryProviderTestSuite) TestFindByID() {
	t := suite.T()
	result, err := suite.addonCategoryProvider.Create(addonCategoryEntity)
	assert.NoError(t, err)
	assert.NotZero(t, result.ID)

	foundResult, err := suite.addonCategoryProvider.FindByID(result.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundResult)
	assert.Equal(t, foundResult.CategoryName, result.CategoryName)
	assert.Equal(t, foundResult.CategoryAlias, result.CategoryAlias)
	assert.Equal(t, foundResult.Active, result.Active)
	assert.Equal(t, foundResult.Description, result.Description)
}

func (suite *AddonCategoryProviderTestSuite) TestFindByList() {
	t := suite.T()
	for _, addon := range addonCategoryEntityList {
		result, err := suite.addonCategoryProvider.Create(&addon)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)

	}

	for _, typeEntity := range addonTypeEntityList {
		result, err := suite.addonTypeProvider.Create(&typeEntity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	addonCategoryTypesEntities, err := suite.addonCategoryProvider.ListByLimit(10)
	assert.NoError(t, err)
	assert.Equal(t, len(addonCategoryEntityList), len(addonCategoryTypesEntities))

	addonCategoryNames := make(map[string]bool)
	for _, addon := range addonCategoryTypesEntities {
		addonCategoryNames[addon.CategoryName] = true
	}

	for _, addon := range addonCategoryEntityList {
		assert.True(t, addonCategoryNames[addon.CategoryName], addon.CategoryName)
	}
}
