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
	metaentity "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var addonSpecPlanEntitySample = &metaentity.AddonSpecPlanEntity{
	AddonID:        1,
	AddonTopology:  "standalone",
	SpecLevel:      "basic",
	SpecLevelAlias: "基础版",
	Active:         true,
	Description:    "test addon spec plan",
}

var addonSpecPlanDbsContext = &commentity.DbsContext{
	BkAdditional: &commentity.BKAdditional{
		BkUserName:  "admin",
		BkAppCode:   "bkappcode",
		BkAppSecret: "bkappsecret",
	},
}

type AddonSpecPlanProviderTestSuite struct {
	suite.Suite
	mySqlContainer        *testhelper.MySQLContainerWrapper
	addonSpecPlanProvider provider.AddonSpecPlanProvider
	ctx                   context.Context
}

func (suite *AddonSpecPlanProviderTestSuite) SetupSuite() {
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
	specPlanProviderBuilder := provider.AddonSpecPlanProviderBuilder{}
	suite.addonSpecPlanProvider = provider.GetAddonSpecPlanProvider(
		specPlanProviderBuilder.WithSpecPlanDbAccess(dbaccess.GetAddonSpecPlanDbAccess(db)),
		specPlanProviderBuilder.WithStorageAddonDbAccess(dbaccess.GetStorageAddonDbAccess(db)),
		specPlanProviderBuilder.WithComponentSpecPlanDbAccess(dbaccess.GetComponentSpecPlanDbAccess(db)),
	)
}

func (suite *AddonSpecPlanProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonSpecPlanProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonSpecPlan, &model.AddonSpecPlanModel{})
}

func TestAddonSpecPlanProvider(t *testing.T) {
	suite.Run(t, new(AddonSpecPlanProviderTestSuite))
}

func (suite *AddonSpecPlanProviderTestSuite) TestCreateAndFindByID() {
	t := suite.T()
	// Create
	created, err := suite.addonSpecPlanProvider.CreateSpecPlan(addonSpecPlanDbsContext, addonSpecPlanEntitySample)
	assert.NoError(t, err)
	assert.NotNil(t, created)
	assert.NotZero(t, created.ID)
	assert.Equal(t, addonSpecPlanEntitySample.AddonID, created.AddonID)
	assert.Equal(t, addonSpecPlanEntitySample.SpecLevel, created.SpecLevel)

	// FindByID
	found, err := suite.addonSpecPlanProvider.FindSpecPlanByID(created.ID)
	assert.NoError(t, err)
	assert.NotNil(t, found)
	assert.Equal(t, created.ID, found.ID)
	assert.Equal(t, addonSpecPlanEntitySample.AddonTopology, found.AddonTopology)
}

func (suite *AddonSpecPlanProviderTestSuite) TestUpdate() {
	t := suite.T()
	created, err := suite.addonSpecPlanProvider.CreateSpecPlan(addonSpecPlanDbsContext, addonSpecPlanEntitySample)
	assert.NoError(t, err)

	// Update
	created.SpecLevel = "premium"
	rows, err := suite.addonSpecPlanProvider.UpdateSpecPlan(addonSpecPlanDbsContext, created)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)

	// Verify
	found, err := suite.addonSpecPlanProvider.FindSpecPlanByID(created.ID)
	assert.NoError(t, err)
	assert.Equal(t, "premium", found.SpecLevel)
}

func (suite *AddonSpecPlanProviderTestSuite) TestDeleteByID() {
	t := suite.T()
	created, err := suite.addonSpecPlanProvider.CreateSpecPlan(addonSpecPlanDbsContext, addonSpecPlanEntitySample)
	assert.NoError(t, err)

	// Delete
	rows, err := suite.addonSpecPlanProvider.DeleteSpecPlanByID(created.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)

	// Verify deleted
	found, err := suite.addonSpecPlanProvider.FindSpecPlanByID(created.ID)
	assert.Error(t, err)
	assert.Nil(t, found)
}

func (suite *AddonSpecPlanProviderTestSuite) TestFindByParams() {
	t := suite.T()
	created, err := suite.addonSpecPlanProvider.CreateSpecPlan(addonSpecPlanDbsContext, addonSpecPlanEntitySample)
	assert.NoError(t, err)

	// Find by params
	params := metaentity.AddonSpecPlanQueryParams{
		AddonID:   created.AddonID,
		SpecLevel: created.SpecLevel,
	}
	results, err := suite.addonSpecPlanProvider.FindSpecPlanByParams(&params)
	assert.NoError(t, err)
	assert.NotEmpty(t, results)
	assert.Equal(t, created.ID, results[0].ID)
}
