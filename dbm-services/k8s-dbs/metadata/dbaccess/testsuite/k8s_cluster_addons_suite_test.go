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
	"k8s-dbs/metadata/model"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var k8sClusterAddonsSample = &model.K8sClusterAddonsModel{
	AddonID:        1,
	K8sClusterName: "test-cluster",
}

var batchK8sClusterAddonsSamples = []*model.K8sClusterAddonsModel{
	{
		AddonID:        1,
		K8sClusterName: "dev-cluster",
	},
	{
		AddonID:        2,
		K8sClusterName: "prod-cluster",
	},
}

var k8sClusterAddonQueryParamsSample = &entitys.K8sClusterAddonQueryParams{
	AddonID:        1,
	K8sClusterName: "test-cluster",
}

type K8sClusterAddonsDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.K8sClusterAddonsDbAccess
	ctx            context.Context
}

func (suite *K8sClusterAddonsDbAccessTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewK8sClusterAddonsDbAccess(db)
	suite.dbAccess = dbAccess
}

func (suite *K8sClusterAddonsDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *K8sClusterAddonsDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sClusterAddons, &model.K8sClusterAddonsModel{})
}

func (suite *K8sClusterAddonsDbAccessTestSuite) TestCreateK8sClusterAddons() {
	t := suite.T()
	k8sClusterAddons, err := suite.dbAccess.Create(k8sClusterAddonsSample)
	assert.NoError(t, err)
	assert.NotZero(t, k8sClusterAddons.ID)
	assert.Equal(t, k8sClusterAddonsSample.AddonID, k8sClusterAddons.AddonID)
	assert.Equal(t, k8sClusterAddonsSample.K8sClusterName, k8sClusterAddons.K8sClusterName)
}

func (suite *K8sClusterAddonsDbAccessTestSuite) TestDeleteK8sClusterAddons() {
	t := suite.T()
	k8sClusterAddons, err := suite.dbAccess.Create(k8sClusterAddonsSample)
	assert.NoError(t, err)
	assert.NotZero(t, k8sClusterAddons.ID)

	rows, err := suite.dbAccess.DeleteByID(k8sClusterAddons.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *K8sClusterAddonsDbAccessTestSuite) TestUpdateK8sClusterAddons() {
	t := suite.T()
	k8sClusterAddons, err := suite.dbAccess.Create(k8sClusterAddonsSample)
	assert.NoError(t, err)
	assert.NotZero(t, k8sClusterAddons.ID)

	newK8sClusterAddons := &model.K8sClusterAddonsModel{
		ID:             k8sClusterAddons.ID,
		AddonID:        2,
		K8sClusterName: "updated-cluster",
	}
	rows, err := suite.dbAccess.Update(newK8sClusterAddons)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *K8sClusterAddonsDbAccessTestSuite) TestGetK8sClusterAddons() {
	t := suite.T()
	k8sClusterAddons, err := suite.dbAccess.Create(k8sClusterAddonsSample)
	assert.NoError(t, err)
	assert.NotZero(t, k8sClusterAddons.ID)

	foundK8sClusterAddons, err := suite.dbAccess.FindByID(k8sClusterAddons.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundK8sClusterAddons)

	assert.Equal(t, k8sClusterAddons.AddonID, foundK8sClusterAddons.AddonID)
	assert.Equal(t, k8sClusterAddons.K8sClusterName, foundK8sClusterAddons.K8sClusterName)
}

func (suite *K8sClusterAddonsDbAccessTestSuite) TestListK8sClusterAddonsByPage() {
	t := suite.T()
	for _, sample := range batchK8sClusterAddonsSamples {
		_, err := suite.dbAccess.Create(sample)
		assert.NoError(t, err)
	}

	pagination := entity.Pagination{
		Page:  0,
		Limit: 10,
	}

	k8sClusterAddons, total, err := suite.dbAccess.ListByPage(pagination)
	assert.NoError(t, err)
	assert.Equal(t, int64(len(batchK8sClusterAddonsSamples)), total)
	assert.Equal(t, len(batchK8sClusterAddonsSamples), len(k8sClusterAddons))

	addonMap := make(map[string]model.K8sClusterAddonsModel)
	for _, addon := range k8sClusterAddons {
		addonMap[addon.K8sClusterName] = addon
	}

	for _, sample := range batchK8sClusterAddonsSamples {
		fetchedAddon, ok := addonMap[sample.K8sClusterName]
		assert.True(t, ok, "K8sClusterAddons with name %s not found", sample.K8sClusterName)
		assert.Equal(t, sample.AddonID, fetchedAddon.AddonID)
	}
}

func (suite *K8sClusterAddonsDbAccessTestSuite) TestFindK8sClusterAddonsByParams() {
	t := suite.T()
	k8sClusterAddons, err := suite.dbAccess.Create(k8sClusterAddonsSample)
	assert.NoError(t, err)
	assert.NotZero(t, k8sClusterAddons.ID)

	foundK8sClusterAddons, err := suite.dbAccess.FindByParams(k8sClusterAddonQueryParamsSample)
	assert.NoError(t, err)
	assert.NotEmpty(t, foundK8sClusterAddons)
	assert.Equal(t, k8sClusterAddons.AddonID, foundK8sClusterAddons[0].AddonID)
	assert.Equal(t, k8sClusterAddons.K8sClusterName, foundK8sClusterAddons[0].K8sClusterName)
}

func TestK8sClusterAddonsDbAccessTestSt(t *testing.T) {
	suite.Run(t, new(K8sClusterAddonsDbAccessTestSuite))
}
