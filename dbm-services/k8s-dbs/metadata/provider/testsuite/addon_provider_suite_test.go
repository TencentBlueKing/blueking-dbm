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

	"github.com/jinzhu/copier"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var k8sCrdStorageAddonEntity = &metaenitty.K8sCrdStorageAddonEntity{
	AddonName:            "addon_name_01",
	AddonCategory:        "addon_category_01",
	AddonType:            "addon_type_01",
	AddonVersion:         "addon_version_01",
	Topologies:           "topologies_01",
	RecommendedVersion:   "recommended_version_01",
	SupportedVersions:    "supported_versions_01",
	RecommendedAcVersion: "recommended_ac_version_01",
	SupportedAcVersions:  "supported_ac_versions_01",
	Releases:             "releases_01",
	Active:               true,
	Description:          "description_01",
}

var k8sCrdStorageAddonEntityList = []metaenitty.K8sCrdStorageAddonEntity{
	{
		AddonName:            "addon_name_01",
		AddonCategory:        "addon_category_01",
		AddonType:            "addon_type_01",
		AddonVersion:         "addon_version_01",
		Topologies:           "topologies_01",
		RecommendedVersion:   "recommended_version_01",
		SupportedVersions:    "supported_versions_01",
		RecommendedAcVersion: "recommended_ac_version_01",
		SupportedAcVersions:  "supported_ac_versions_01",
		Releases:             "releases_01",
		Active:               true,
		Description:          "description_01",
	},
	{
		AddonName:            "addon_name_02",
		AddonCategory:        "addon_category_02",
		AddonType:            "addon_type_02",
		AddonVersion:         "addon_version_02",
		Topologies:           "topologies_02",
		RecommendedVersion:   "recommended_version_02",
		SupportedVersions:    "supported_versions_02",
		RecommendedAcVersion: "recommended_ac_version_02",
		SupportedAcVersions:  "supported_ac_versions_02",
		Releases:             "releases_02",
		Active:               true,
		Description:          "description_02",
	},
}

var addonDbsContext = &commentity.DbsContext{
	BkAuth: &commentity.BKAuth{
		BkUserName:  "bkuser",
		BkAppCode:   "bkappcode",
		BkAppSecret: "bkappsecret",
	},
}

type AddonProviderTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	addonProvider  provider.K8sCrdStorageAddonProvider
	ctx            context.Context
}

func (suite *AddonProviderTestSuite) SetupSuite() {
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
	suite.addonProvider = provider.NewK8sCrdStorageAddonProvider(dbAccess)
}

func (suite *AddonProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sClusterAddons, &model.K8sCrdStorageAddonModel{})
}

func TestAddonProvider(t *testing.T) {
	suite.Run(t, new(AddonProviderTestSuite))
}

func (suite *AddonProviderTestSuite) TestCreateStorageAddon() {
	t := suite.T()
	storageAddon, err := suite.addonProvider.CreateStorageAddon(addonDbsContext, k8sCrdStorageAddonEntity)
	assert.NoError(t, err)
	assert.NotNil(t, storageAddon)
	assert.Equal(t, k8sCrdStorageAddonEntity.AddonName, storageAddon.AddonName)
	assert.Equal(t, k8sCrdStorageAddonEntity.AddonCategory, storageAddon.AddonCategory)
	assert.Equal(t, k8sCrdStorageAddonEntity.AddonType, storageAddon.AddonType)
	assert.Equal(t, k8sCrdStorageAddonEntity.AddonVersion, storageAddon.AddonVersion)
	assert.Equal(t, k8sCrdStorageAddonEntity.Topologies, storageAddon.Topologies)
	assert.Equal(t, k8sCrdStorageAddonEntity.RecommendedVersion, storageAddon.RecommendedVersion)
	assert.Equal(t, k8sCrdStorageAddonEntity.SupportedVersions, storageAddon.SupportedVersions)
	assert.Equal(t, k8sCrdStorageAddonEntity.RecommendedAcVersion, storageAddon.RecommendedAcVersion)
	assert.Equal(t, k8sCrdStorageAddonEntity.SupportedAcVersions, storageAddon.SupportedAcVersions)
	assert.Equal(t, k8sCrdStorageAddonEntity.Releases, storageAddon.Releases)
	assert.Equal(t, k8sCrdStorageAddonEntity.Active, storageAddon.Active)
	assert.Equal(t, k8sCrdStorageAddonEntity.Description, storageAddon.Description)
}

func (suite *AddonProviderTestSuite) TestDeleteStorageAddonByID() {
	t := suite.T()
	storageAddon, err := suite.addonProvider.CreateStorageAddon(addonDbsContext, k8sCrdStorageAddonEntity)
	assert.NoError(t, err)
	assert.NotNil(t, storageAddon.ID)

	rows, err := suite.addonProvider.DeleteStorageAddonByID(storageAddon.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonProviderTestSuite) TestFindStorageAddonByID() {
	t := suite.T()
	storageAddon, err := suite.addonProvider.CreateStorageAddon(addonDbsContext, k8sCrdStorageAddonEntity)
	assert.NoError(t, err)
	assert.NotNil(t, storageAddon.ID)

	foundAddon, err := suite.addonProvider.FindStorageAddonByID(storageAddon.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundAddon)
	assert.Equal(t, storageAddon.AddonName, foundAddon.AddonName)
	assert.Equal(t, storageAddon.AddonCategory, foundAddon.AddonCategory)
	assert.Equal(t, storageAddon.AddonType, foundAddon.AddonType)
	assert.Equal(t, storageAddon.AddonVersion, foundAddon.AddonVersion)
	assert.Equal(t, storageAddon.Topologies, foundAddon.Topologies)
	assert.Equal(t, storageAddon.RecommendedVersion, foundAddon.RecommendedVersion)
	assert.Equal(t, storageAddon.SupportedVersions, foundAddon.SupportedVersions)
	assert.Equal(t, storageAddon.RecommendedAcVersion, foundAddon.RecommendedAcVersion)
	assert.Equal(t, storageAddon.SupportedAcVersions, foundAddon.SupportedAcVersions)
	assert.Equal(t, storageAddon.Releases, foundAddon.Releases)
	assert.Equal(t, storageAddon.Active, foundAddon.Active)
	assert.Equal(t, storageAddon.Description, foundAddon.Description)
}

func (suite *AddonProviderTestSuite) TestFindStorageAddonByParams() {
	t := suite.T()
	storageAddon, err := suite.addonProvider.CreateStorageAddon(addonDbsContext, k8sCrdStorageAddonEntity)
	assert.NoError(t, err)
	assert.NotZero(t, storageAddon.ID)

	var params = metaenitty.AddonQueryParams{}
	err = copier.Copy(&params, storageAddon)
	foundAddons, err := suite.addonProvider.FindStorageAddonByParams(&params)
	assert.NoError(t, err)
	assert.Equal(t, len(foundAddons), 1)
	foundAddon := foundAddons[0]
	assert.NotNil(t, storageAddon)
	assert.Equal(t, k8sCrdStorageAddonEntity.AddonName, foundAddon.AddonName)
	assert.Equal(t, k8sCrdStorageAddonEntity.AddonCategory, foundAddon.AddonCategory)
	assert.Equal(t, k8sCrdStorageAddonEntity.AddonType, foundAddon.AddonType)
	assert.Equal(t, k8sCrdStorageAddonEntity.AddonVersion, foundAddon.AddonVersion)
	assert.Equal(t, k8sCrdStorageAddonEntity.Topologies, foundAddon.Topologies)
	assert.Equal(t, k8sCrdStorageAddonEntity.RecommendedVersion, foundAddon.RecommendedVersion)
	assert.Equal(t, k8sCrdStorageAddonEntity.SupportedVersions, foundAddon.SupportedVersions)
	assert.Equal(t, k8sCrdStorageAddonEntity.RecommendedAcVersion, foundAddon.RecommendedAcVersion)
	assert.Equal(t, k8sCrdStorageAddonEntity.SupportedAcVersions, foundAddon.SupportedAcVersions)
	assert.Equal(t, k8sCrdStorageAddonEntity.Releases, foundAddon.Releases)
	assert.Equal(t, k8sCrdStorageAddonEntity.Active, foundAddon.Active)
	assert.Equal(t, k8sCrdStorageAddonEntity.Description, foundAddon.Description)
}

func (suite *AddonProviderTestSuite) TestUpdateStorageAddon() {
	t := suite.T()
	storageAddon, err := suite.addonProvider.CreateStorageAddon(addonDbsContext, k8sCrdStorageAddonEntity)
	assert.NoError(t, err)
	assert.NotNil(t, storageAddon.ID)

	storageAddon.AddonVersion = "updated_version"
	storageAddon.Active = false

	rows, err := suite.addonProvider.UpdateStorageAddon(addonDbsContext, storageAddon)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonProviderTestSuite) TestListStorageAddons() {
	t := suite.T()
	for _, addon := range k8sCrdStorageAddonEntityList {
		result, err := suite.addonProvider.CreateStorageAddon(addonDbsContext, &addon)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	pagin := commentity.Pagination{
		Page:  0,
		Limit: 10,
	}

	addons, err := suite.addonProvider.ListStorageAddons(pagin)
	assert.NoError(t, err)

	addonNames := make(map[string]bool)
	for _, addon := range addons {
		addonNames[addon.AddonName] = true
	}

	for _, addon := range k8sCrdStorageAddonEntityList {
		assert.True(t, addonNames[addon.AddonName], addon.AddonName)
	}
}
