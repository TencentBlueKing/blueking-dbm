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
	metaenitty "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var addonClusterVersionEntity = &metaenitty.AddonClusterVersionEntity{
	AddonID:          uint64(1),
	Version:          "version_01",
	AddonClusterName: "test_addon_cluster_01",
	Active:           true,
	Description:      "description_01",
}

var addonClusterVersionEntityList = []*metaenitty.AddonClusterVersionEntity{
	{
		AddonID:          uint64(1),
		Version:          "version_01",
		AddonClusterName: "test_addon_cluster_01",
		Active:           true,
		Description:      "description_01",
	},
	{
		AddonID:          uint64(2),
		Version:          "version_02",
		AddonClusterName: "test_addon_cluster_02",
		Active:           true,
		Description:      "description_02",
	},
}

type AddonClusterVersionProviderTestSuite struct {
	suite.Suite
	mySqlContainer              *testhelper.MySQLContainerWrapper
	addonClusterVersionProvider provider.AddonClusterVersionProvider
	ctx                         context.Context
}

func (suite *AddonClusterVersionProviderTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewAddonClusterVersionDbAccess(db)
	suite.addonClusterVersionProvider = provider.NewAddonClusterVersionProvider(dbAccess)
}

func (suite *AddonClusterVersionProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonClusterVersionProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonClusterVersion, &model.AddonClusterVersionModel{})
}

func TestAddonClusterVersionProvider(t *testing.T) {
	suite.Run(t, new(AddonClusterVersionProviderTestSuite))
}

func (suite *AddonClusterVersionProviderTestSuite) TestCreateAcVersion() {
	t := suite.T()
	addedEntity, err := suite.addonClusterVersionProvider.CreateAcVersion(addonClusterVersionEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addedEntity.ID)

	// Verify the created entity
	createdEntity, err := suite.addonClusterVersionProvider.FindAcVersionByID(addedEntity.ID)
	assert.NoError(t, err)
	assert.Equal(t, addonClusterVersionEntity.AddonID, createdEntity.AddonID)
	assert.Equal(t, addonClusterVersionEntity.Version, createdEntity.Version)
	assert.Equal(t, addonClusterVersionEntity.AddonClusterName, createdEntity.AddonClusterName)
	assert.Equal(t, addonClusterVersionEntity.Active, createdEntity.Active)
	assert.Equal(t, addonClusterVersionEntity.Description, createdEntity.Description)
}

func (suite *AddonClusterVersionProviderTestSuite) TestDeleteAcVersionByID() {
	t := suite.T()
	addedEntity, err := suite.addonClusterVersionProvider.CreateAcVersion(addonClusterVersionEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addedEntity.ID)

	deletedRows, err := suite.addonClusterVersionProvider.DeleteAcVersionByID(addedEntity.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), deletedRows)
}

func (suite *AddonClusterVersionProviderTestSuite) TestFindAcVersionByID() {
	t := suite.T()
	addedEntity, err := suite.addonClusterVersionProvider.CreateAcVersion(addonClusterVersionEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addedEntity.ID)

	entity, err := suite.addonClusterVersionProvider.FindAcVersionByID(addedEntity.ID)
	assert.NoError(t, err)
	assert.Equal(t, addonClusterVersionEntity.AddonID, entity.AddonID)
	assert.Equal(t, addonClusterVersionEntity.Version, entity.Version)
	assert.Equal(t, addonClusterVersionEntity.AddonClusterName, entity.AddonClusterName)
	assert.Equal(t, addonClusterVersionEntity.Active, entity.Active)
	assert.Equal(t, addonClusterVersionEntity.Description, entity.Description)

}
func (suite *AddonClusterVersionProviderTestSuite) TestFindAcVersionByParams() {
	t := suite.T()
	addedEntity, err := suite.addonClusterVersionProvider.CreateAcVersion(addonClusterVersionEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addedEntity.ID)

	params := make(map[string]interface{})
	params["addon_id"] = addedEntity.AddonID
	entities, err := suite.addonClusterVersionProvider.FindAcVersionByParams(params)
	assert.NoError(t, err)
	assert.Equal(t, addonClusterVersionEntity.AddonID, entities[0].AddonID)
	assert.Equal(t, addonClusterVersionEntity.Version, entities[0].Version)
	assert.Equal(t, addonClusterVersionEntity.AddonClusterName, entities[0].AddonClusterName)
	assert.Equal(t, addonClusterVersionEntity.Active, entities[0].Active)
	assert.Equal(t, addonClusterVersionEntity.Description, entities[0].Description)
}

func (suite *AddonClusterVersionProviderTestSuite) TestUpdatedAcVersion() {
	t := suite.T()
	addedEntity, err := suite.addonClusterVersionProvider.CreateAcVersion(addonClusterVersionEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addedEntity.ID)

	addedEntity.Version = "v1.0.0"
	rows, err := suite.addonClusterVersionProvider.UpdateAcVersion(addedEntity)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonClusterVersionProviderTestSuite) TestListAcVersion() {
	t := suite.T()
	for _, entity := range addonClusterVersionEntityList {
		addedEntity, err := suite.addonClusterVersionProvider.CreateAcVersion(entity)
		assert.NoError(t, err)
		assert.NotZero(t, addedEntity.ID)
	}

	pagin := commentity.Pagination{
		Page:  0,
		Limit: 10,
	}

	entities, err := suite.addonClusterVersionProvider.ListAcVersion(pagin)
	assert.NoError(t, err)

	addonNames := make(map[string]bool)
	for _, addon := range entities {
		addonNames[addon.AddonClusterName] = true
	}

	for _, addon := range addonClusterVersionEntityList {
		assert.True(t, addonNames[addon.AddonClusterName], addon.AddonClusterName)
	}

}
