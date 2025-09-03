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
	"k8s-dbs/metadata/helper/testhelper"
	models "k8s-dbs/metadata/model"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var addonClusterVersionSample = &models.AddonClusterVersionModel{
	AddonID:          1,
	Version:          "1.0.0",
	AddonClusterName: "mysql-cluster",
}

var batchAddonClusterVersionSamples = []*models.AddonClusterVersionModel{
	{
		AddonID:          2,
		Version:          "2.0.0",
		AddonClusterName: "redis-cluster",
	},
	{
		AddonID:          3,
		Version:          "3.0.0",
		AddonClusterName: "mongodb-cluster",
	},
}

type AddonClusterVersionDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.AddonClusterVersionDbAccess
	ctx            context.Context
}

func (suite *AddonClusterVersionDbAccessTestSuite) SetupSuite() {
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
	suite.dbAccess = dbaccess.NewAddonClusterVersionDbAccess(db)
}

func (suite *AddonClusterVersionDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonClusterVersionDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonClusterVersion, &models.AddonClusterVersionModel{})
}

func (suite *AddonClusterVersionDbAccessTestSuite) TestCreateAddonClusterVersion() {
	t := suite.T()
	version, err := suite.dbAccess.Create(addonClusterVersionSample)
	assert.NoError(t, err)
	assert.Equal(t, addonClusterVersionSample.AddonID, version.AddonID)
	assert.Equal(t, addonClusterVersionSample.Version, version.Version)
	assert.Equal(t, addonClusterVersionSample.AddonClusterName, version.AddonClusterName)
	assert.Equal(t, addonClusterVersionSample.Active, version.Active)
	assert.Equal(t, addonClusterVersionSample.Description, version.Description)
	assert.Greater(t, version.ID, uint64(0))
}

func (suite *AddonClusterVersionDbAccessTestSuite) TestGetAddonClusterVersion() {
	t := suite.T()
	version, err := suite.dbAccess.Create(addonClusterVersionSample)
	assert.NoError(t, err)

	fetched, err := suite.dbAccess.FindByID(version.ID)
	assert.NoError(t, err)
	assert.NotNil(t, fetched)
	assert.Equal(t, version.ID, fetched.ID)
	assert.Equal(t, version.AddonID, fetched.AddonID)
	assert.Equal(t, version.Version, fetched.Version)
	assert.Equal(t, version.AddonClusterName, fetched.AddonClusterName)
	assert.Equal(t, version.Active, fetched.Active)
	assert.Equal(t, version.Description, fetched.Description)
}

func (suite *AddonClusterVersionDbAccessTestSuite) TestFindAddonClusterVersionByParams() {
	t := suite.T()
	version, err := suite.dbAccess.Create(addonClusterVersionSample)
	assert.NoError(t, err)

	params := map[string]interface{}{
		"addon_id":          1,
		"version":           "1.0.0",
		"addoncluster_name": "mysql-cluster",
	}
	versions, err := suite.dbAccess.FindByParams(params)
	assert.NoError(t, err)
	assert.NotNil(t, versions)
	assert.GreaterOrEqual(t, len(versions), 1)

	fetched := versions[0]
	assert.Equal(t, version.ID, fetched.ID)
	assert.Equal(t, uint64(1), fetched.AddonID)
	assert.Equal(t, "1.0.0", fetched.Version)
	assert.Equal(t, "mysql-cluster", fetched.AddonClusterName)
}

func (suite *AddonClusterVersionDbAccessTestSuite) TestUpdateAddonClusterVersion() {
	t := suite.T()
	version, err := suite.dbAccess.Create(addonClusterVersionSample)
	assert.NoError(t, err)
	assert.NotZero(t, version.ID)

	newVersion := &models.AddonClusterVersionModel{
		ID:               version.ID,
		AddonID:          2,
		Version:          "1.1.0",
		AddonClusterName: "mysql-cluster-updated",
		Description:      "update success",
	}
	rows, err := suite.dbAccess.Update(newVersion)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonClusterVersionDbAccessTestSuite) TestDeleteAddonClusterVersion() {
	t := suite.T()
	version, err := suite.dbAccess.Create(addonClusterVersionSample)
	assert.NoError(t, err)
	assert.NotZero(t, version.ID)

	rows, err := suite.dbAccess.DeleteByID(version.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonClusterVersionDbAccessTestSuite) TestListAddonClusterVersionsByPage() {
	t := suite.T()
	for _, sample := range batchAddonClusterVersionSamples {
		_, err := suite.dbAccess.Create(sample)
		assert.NoError(t, err)
	}

	pagination := entity.Pagination{
		Page:  0,
		Limit: 10,
	}
	versions, total, err := suite.dbAccess.ListByPage(pagination)
	assert.NoError(t, err)
	assert.Equal(t, len(batchAddonClusterVersionSamples), len(versions))
	assert.Equal(t, int64(len(batchAddonClusterVersionSamples)), total)

	versionMap := make(map[string]models.AddonClusterVersionModel)
	for _, version := range versions {
		versionMap[version.AddonClusterName] = *version
	}

	for _, sample := range batchAddonClusterVersionSamples {
		foundVersion, ok := versionMap[sample.AddonClusterName]
		assert.True(t, ok, "Version with cluster name %s not found", sample.AddonClusterName)
		assert.Equal(t, sample.AddonID, foundVersion.AddonID)
		assert.Equal(t, sample.Version, foundVersion.Version)
		assert.Equal(t, sample.AddonClusterName, foundVersion.AddonClusterName)
	}
}

func TestAddonClusterVersionDbAccess(t *testing.T) {
	suite.Run(t, new(AddonClusterVersionDbAccessTestSuite))
}
