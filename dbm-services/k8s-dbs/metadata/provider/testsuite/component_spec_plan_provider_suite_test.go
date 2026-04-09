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

var componentSpecPlanEntitySample = &metaentity.ComponentSpecPlanEntity{
	AddonSpecPlanID: 1,
	ComponentName:   "mysql",
	CPUCores:        entityIntPtr(4),
	MemoryGb:        entityIntPtr(8),
	DiskSizeGb:      entityIntPtr(100),
	Active:          true,
	Description:     "test component spec plan",
}

var componentSpecPlanDbsContext = &commentity.DbsContext{
	BkAdditional: &commentity.BKAdditional{
		BkUserName:  "admin",
		BkAppCode:   "bkappcode",
		BkAppSecret: "bkappsecret",
	},
}

func entityIntPtr(i int) *int {
	return &i
}

type ComponentSpecPlanProviderTestSuite struct {
	suite.Suite
	mySqlContainer            *testhelper.MySQLContainerWrapper
	componentSpecPlanProvider provider.ComponentSpecPlanProvider
	ctx                       context.Context
}

func (suite *ComponentSpecPlanProviderTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.GetComponentSpecPlanDbAccess(db)
	suite.componentSpecPlanProvider = provider.GetComponentSpecPlanProvider(dbAccess)
}

func (suite *ComponentSpecPlanProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ComponentSpecPlanProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbComponentSpecPlan, &model.ComponentSpecPlanModel{})
}

func TestComponentSpecPlanProvider(t *testing.T) {
	suite.Run(t, new(ComponentSpecPlanProviderTestSuite))
}

func (suite *ComponentSpecPlanProviderTestSuite) TestCreateAndFindByID() {
	t := suite.T()
	// Create
	created, err := suite.componentSpecPlanProvider.CreateSpecPlan(componentSpecPlanDbsContext, componentSpecPlanEntitySample)
	assert.NoError(t, err)
	assert.NotNil(t, created)
	assert.NotZero(t, created.ID)
	assert.Equal(t, componentSpecPlanEntitySample.ComponentName, created.ComponentName)
	assert.Equal(t, *componentSpecPlanEntitySample.CPUCores, *created.CPUCores)

	// FindByID
	found, err := suite.componentSpecPlanProvider.FindSpecPlanByID(created.ID)
	assert.NoError(t, err)
	assert.NotNil(t, found)
	assert.Equal(t, created.ID, found.ID)
	assert.Equal(t, componentSpecPlanEntitySample.AddonSpecPlanID, found.AddonSpecPlanID)
}

func (suite *ComponentSpecPlanProviderTestSuite) TestUpdate() {
	t := suite.T()
	created, err := suite.componentSpecPlanProvider.CreateSpecPlan(componentSpecPlanDbsContext, componentSpecPlanEntitySample)
	assert.NoError(t, err)

	// Update
	newCPU := 8
	created.CPUCores = &newCPU
	rows, err := suite.componentSpecPlanProvider.UpdateSpecPlan(componentSpecPlanDbsContext, created)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)

	// Verify
	found, err := suite.componentSpecPlanProvider.FindSpecPlanByID(created.ID)
	assert.NoError(t, err)
	assert.Equal(t, newCPU, *found.CPUCores)
}

func (suite *ComponentSpecPlanProviderTestSuite) TestDeleteByID() {
	t := suite.T()
	created, err := suite.componentSpecPlanProvider.CreateSpecPlan(componentSpecPlanDbsContext, componentSpecPlanEntitySample)
	assert.NoError(t, err)

	// Delete
	rows, err := suite.componentSpecPlanProvider.DeleteSpecPlanByID(created.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)

	// Verify deleted
	found, err := suite.componentSpecPlanProvider.FindSpecPlanByID(created.ID)
	assert.Error(t, err)
	assert.Nil(t, found)
}

func (suite *ComponentSpecPlanProviderTestSuite) TestFindByParams() {
	t := suite.T()
	created, err := suite.componentSpecPlanProvider.CreateSpecPlan(componentSpecPlanDbsContext, componentSpecPlanEntitySample)
	assert.NoError(t, err)

	// Find by params
	params := metaentity.ComponentSpecPlanQueryParams{
		AddonSpecPlanID: created.AddonSpecPlanID,
		ComponentName:   created.ComponentName,
	}
	results, err := suite.componentSpecPlanProvider.FindSpecPlanByParams(&params)
	assert.NoError(t, err)
	assert.NotEmpty(t, results)
	assert.Equal(t, created.ID, results[0].ID)
}
