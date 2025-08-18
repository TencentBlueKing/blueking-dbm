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
	"log/slog"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var storageAddonSample = &model.K8sCrdStorageAddonModel{
	AddonName:            "test-addon",
	AddonCategory:        "storage",
	AddonType:            "mysql",
	AddonVersion:         "1.0.0",
	RecommendedVersion:   "1.0.0",
	SupportedVersions:    "1.0.0,1.1.0",
	RecommendedAcVersion: "1.0.0",
	SupportedAcVersions:  "1.0.0,1.1.0",
}

var batchStorageAddonSamples = []*model.K8sCrdStorageAddonModel{
	{
		AddonName:            "test-addon-1",
		AddonCategory:        "storage",
		AddonType:            "mysql",
		AddonVersion:         "1.0.0",
		RecommendedVersion:   "1.0.0",
		SupportedVersions:    "1.0.0,1.1.0",
		RecommendedAcVersion: "1.0.0",
		SupportedAcVersions:  "1.0.0,1.1.0",
	},
	{
		AddonName:            "test-addon-2",
		AddonCategory:        "storage",
		AddonType:            "postgresql",
		AddonVersion:         "2.0.0",
		RecommendedVersion:   "2.0.0",
		SupportedVersions:    "2.0.0,2.1.0",
		RecommendedAcVersion: "2.0.0",
		SupportedAcVersions:  "2.0.0,2.1.0",
	},
}

var addonQueryParamsSample = &entitys.AddonQueryParams{
	AddonName:     "test-addon",
	AddonCategory: "storage",
	AddonType:     "mysql",
	Active:        true,
}

var addonVersionQueryParamsSample = &entitys.AddonVersionQueryParams{
	AddonCategory: "storage",
	AddonType:     "mysql",
}

var paginationSample = entity.Pagination{
	Page:  0,
	Limit: 10,
}

type AddonDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.K8sCrdStorageAddonDbAccess
	ctx            context.Context
}

func (suite *AddonDbAccessTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)
	suite.dbAccess = dbAccess
}

func (suite *AddonDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sCrdStorageAddon, &model.K8sCrdStorageAddonModel{})
}

func (suite *AddonDbAccessTestSuite) TestCreateStorageAddon() {
	t := suite.T()
	addon, err := suite.dbAccess.Create(storageAddonSample)
	assert.NoError(t, err)
	assert.NotZero(t, addon.ID)
	assert.Equal(t, storageAddonSample.AddonName, addon.AddonName)
	assert.Equal(t, storageAddonSample.AddonCategory, addon.AddonCategory)
	assert.Equal(t, storageAddonSample.AddonType, addon.AddonType)
	assert.Equal(t, storageAddonSample.AddonVersion, addon.AddonVersion)
}

func (suite *AddonDbAccessTestSuite) TestDeleteStorageAddon() {
	t := suite.T()
	addon, err := suite.dbAccess.Create(storageAddonSample)
	assert.NoError(t, err)
	assert.NotZero(t, addon.ID)

	rows, err := suite.dbAccess.DeleteByID(addon.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonDbAccessTestSuite) TestGetStorageAddon() {
	t := suite.T()
	addon, err := suite.dbAccess.Create(storageAddonSample)
	assert.NoError(t, err)
	assert.NotZero(t, addon.ID)

	foundAddon, err := suite.dbAccess.FindByID(addon.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundAddon)
	slog.Info("Print addon", "Addon", foundAddon)

	assert.Equal(t, addon.AddonName, foundAddon.AddonName)
	assert.Equal(t, addon.AddonCategory, foundAddon.AddonCategory)
	assert.Equal(t, addon.AddonType, foundAddon.AddonType)
	assert.Equal(t, addon.AddonVersion, foundAddon.AddonVersion)
}

func (suite *AddonDbAccessTestSuite) TestFindStorageAddonByParams() {
	t := suite.T()
	addon, err := suite.dbAccess.Create(storageAddonSample)
	assert.NoError(t, err)
	assert.NotZero(t, addon.ID)

	addons, err := suite.dbAccess.FindByParams(addonQueryParamsSample)
	assert.NoError(t, err)
	assert.NotEmpty(t, addons)
	assert.Equal(t, addon.AddonName, addons[0].AddonName)
	assert.Equal(t, addon.AddonCategory, addons[0].AddonCategory)
	assert.Equal(t, addon.AddonType, addons[0].AddonType)
}

func (suite *AddonDbAccessTestSuite) TestUpdateStorageAddon() {
	t := suite.T()
	addon, err := suite.dbAccess.Create(storageAddonSample)
	assert.NoError(t, err)
	assert.NotZero(t, addon.ID)

	newAddon := &model.K8sCrdStorageAddonModel{
		ID:                   addon.ID,
		AddonName:            "updated-addon",
		AddonCategory:        "Database",
		AddonType:            "mysql",
		AddonVersion:         "2.0.0",
		RecommendedVersion:   "2.0.0",
		SupportedVersions:    "2.0.0,2.1.0",
		RecommendedAcVersion: "2.0.0",
		SupportedAcVersions:  "2.0.0,2.1.0",
	}
	rows, err := suite.dbAccess.Update(newAddon)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonDbAccessTestSuite) TestListStorageAddonByPage() {
	t := suite.T()
	for _, addon := range batchStorageAddonSamples {
		_, err := suite.dbAccess.Create(addon)
		assert.NoError(t, err)
	}

	addons, count, err := suite.dbAccess.ListByPage(paginationSample)
	assert.NoError(t, err)
	assert.Equal(t, len(batchStorageAddonSamples), len(addons))
	assert.Equal(t, int64(len(batchStorageAddonSamples)), count)

	addonMap := make(map[string]model.K8sCrdStorageAddonModel)
	for _, addon := range addons {
		addonMap[addon.AddonName] = addon
	}

	for _, sample := range batchStorageAddonSamples {
		fetchedAddon, ok := addonMap[sample.AddonName]
		assert.True(t, ok, "Addon with name %s not found", sample.AddonName)
		assert.Equal(t, sample.AddonName, fetchedAddon.AddonName)
		assert.Equal(t, sample.AddonCategory, fetchedAddon.AddonCategory)
		assert.Equal(t, sample.AddonType, fetchedAddon.AddonType)
		assert.Equal(t, sample.AddonVersion, fetchedAddon.AddonVersion)
		assert.Equal(t, sample.RecommendedVersion, fetchedAddon.RecommendedVersion)
		assert.Equal(t, sample.SupportedVersions, fetchedAddon.SupportedVersions)
		assert.Equal(t, sample.RecommendedAcVersion, fetchedAddon.RecommendedAcVersion)
		assert.Equal(t, sample.SupportedAcVersions, fetchedAddon.SupportedAcVersions)
	}
}

func (suite *AddonDbAccessTestSuite) TestFindStorageAddonVersByParams() {
	t := suite.T()
	addon, err := suite.dbAccess.Create(storageAddonSample)
	assert.NoError(t, err)
	assert.NotZero(t, addon.ID)

	versions, err := suite.dbAccess.FindVersionsByParams(addonVersionQueryParamsSample)
	assert.NoError(t, err)
	assert.NotEmpty(t, versions)
	assert.Equal(t, addon.AddonVersion, versions[0].AddonVersion)
	assert.Equal(t, addon.SupportedVersions, versions[0].SupportedVersions)
}

func TestStorageAddonDbAccessTestSuite(t *testing.T) {
	suite.Run(t, new(AddonDbAccessTestSuite))
}
