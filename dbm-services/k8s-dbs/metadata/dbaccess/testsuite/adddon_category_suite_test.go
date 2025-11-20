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

var categorySample = &model.AddonCategoryModel{
	CategoryName:  "test-category",
	CategoryAlias: "test-alias",
}

var batchCategorySamples = []*model.AddonCategoryModel{
	{
		CategoryName:  "test-category-1",
		CategoryAlias: "test-alias-1",
	},
	{
		CategoryName:  "test-category-2",
		CategoryAlias: "test-alias-2",
	},
}

type AddonCategoryDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.AddonCategoryDbAccess
	ctx            context.Context
}

func (suite *AddonCategoryDbAccessTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewAddonCategoryDbAccess(db)
	suite.dbAccess = dbAccess
}

func (suite *AddonCategoryDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonCategoryDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonCategory, &model.AddonCategoryModel{})
}

func (suite *AddonCategoryDbAccessTestSuite) TestCreateAddonCategory() {
	t := suite.T()
	category, err := suite.dbAccess.Create(categorySample)
	assert.NoError(t, err)
	assert.NotZero(t, category.ID)
	assert.Equal(t, categorySample.CategoryName, category.CategoryName)
	assert.Equal(t, categorySample.CategoryAlias, category.CategoryAlias)
}

func (suite *AddonCategoryDbAccessTestSuite) TestGetAddonCategory() {
	t := suite.T()
	category, err := suite.dbAccess.Create(categorySample)
	assert.NoError(t, err)
	assert.NotZero(t, category.ID)

	foundCategory, err := suite.dbAccess.FindByID(category.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundCategory)
	assert.Equal(t, category.ID, foundCategory.ID)
	assert.Equal(t, category.CategoryName, foundCategory.CategoryName)
	assert.Equal(t, category.CategoryAlias, foundCategory.CategoryAlias)
}

func (suite *AddonCategoryDbAccessTestSuite) TestListAddonCategoryByLimit() {
	t := suite.T()
	for _, sample := range batchCategorySamples {
		_, err := suite.dbAccess.Create(sample)
		assert.NoError(t, err)
	}

	categories, err := suite.dbAccess.ListByLimit(10)
	assert.NoError(t, err)
	assert.Equal(t, len(batchCategorySamples), len(categories))

	categoryMap := make(map[string]model.AddonCategoryModel)
	for _, category := range categories {
		categoryMap[category.CategoryName] = *category
	}

	for _, sample := range batchCategorySamples {
		foundCategory, ok := categoryMap[sample.CategoryName]
		assert.True(t, ok, "Category with name %s not found", sample.CategoryName)
		assert.Equal(t, sample.CategoryAlias, foundCategory.CategoryAlias)
	}
}

func TestAddonCategoryDbAccess(t *testing.T) {
	suite.Run(t, new(AddonCategoryDbAccessTestSuite))
}
