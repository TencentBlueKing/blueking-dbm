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

package tests

import (
	"fmt"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	"k8s-dbs/metadata/dbaccess/model"
	"k8s-dbs/metadata/utils"
	"testing"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func InitAddonClusterReleaseTb() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_addoncluster_release;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_storageaddon table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.AddonClusterReleaseModel{}); err != nil {
		fmt.Println("Failed to migrate tb_addoncluster_release table")
		return nil, err
	}
	return db, nil
}

func TestCreateRelease(t *testing.T) {
	db, err := InitAddonClusterReleaseTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterReleaseDbAccess(db)
	release := &model.AddonClusterReleaseModel{
		RepoName:           "test-reponame",
		RepoRepository:     "test-repository",
		ChartVersion:       "test-chartversion",
		ChartName:          "test-chartname",
		Namespace:          "test-namespace",
		K8sClusterConfigID: 1,
		ReleaseName:        "test-release",
		ChartValues:        "test-chart-values",
	}

	addedRelease, err := dbAccess.Create(release)
	assert.NoError(t, err)
	assert.Equal(t, release.ReleaseName, addedRelease.ReleaseName)
	assert.Equal(t, release.Namespace, addedRelease.Namespace)
	assert.Equal(t, release.K8sClusterConfigID, addedRelease.K8sClusterConfigID)
	assert.Equal(t, release.ChartValues, addedRelease.ChartValues)
}

func TestDeleteRelease(t *testing.T) {
	db, err := InitAddonClusterReleaseTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterReleaseDbAccess(db)
	release := &model.AddonClusterReleaseModel{
		RepoName:           "test-reponame",
		RepoRepository:     "test-repository",
		ChartVersion:       "test-chartversion",
		ChartName:          "test-chartname",
		Namespace:          "test-namespace",
		K8sClusterConfigID: 1,
		ReleaseName:        "test-release",
		ChartValues:        "test-chart-values",
		CreatedBy:          "alex",
	}

	_, err = dbAccess.Create(release)
	assert.NoError(t, err)

	rows, err := dbAccess.DeleteByID(1)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateRelease(t *testing.T) {
	db, err := InitAddonClusterReleaseTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterReleaseDbAccess(db)
	release := &model.AddonClusterReleaseModel{
		ID:                 1,
		RepoName:           "test-reponame",
		RepoRepository:     "test-repository",
		ChartVersion:       "test-chartversion",
		ChartName:          "test-chartname",
		Namespace:          "test-namespace",
		K8sClusterConfigID: 1,
		ReleaseName:        "test-release",
		ChartValues:        "test-chart-values",
		CreatedBy:          "alex",
	}

	_, err = dbAccess.Create(release)
	assert.NoError(t, err)

	updateRelease := &model.AddonClusterReleaseModel{
		ID:                 1,
		RepoName:           "test-reponame2",
		RepoRepository:     "test-repository2",
		ChartVersion:       "test-chartversion2",
		ChartName:          "test-chartname2",
		Namespace:          "test-namespace2",
		K8sClusterConfigID: 1,
		ReleaseName:        "test-release2",
		ChartValues:        "test-chart-values2",
		UpdatedBy:          "alex",
	}
	rows, err := dbAccess.Update(updateRelease)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestGetRelease(t *testing.T) {
	db, err := InitAddonClusterReleaseTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterReleaseDbAccess(db)
	release := &model.AddonClusterReleaseModel{
		RepoName:           "test-reponame",
		RepoRepository:     "test-repository",
		ChartVersion:       "test-chartversion",
		ChartName:          "test-chartname",
		Namespace:          "test-namespace",
		K8sClusterConfigID: 1,
		ReleaseName:        "test-release",
		ChartValues:        "test-chart-values",
	}

	_, err = dbAccess.Create(release)
	assert.NoError(t, err)

	foundRelease, err := dbAccess.FindByID(1)
	assert.NoError(t, err)
	assert.Equal(t, release.ReleaseName, foundRelease.ReleaseName)
	assert.Equal(t, release.ChartValues, foundRelease.ChartValues)
	assert.Equal(t, release.Namespace, foundRelease.Namespace)
	assert.Equal(t, release.ChartName, foundRelease.ChartName)
	assert.Equal(t, release.ChartVersion, foundRelease.ChartVersion)
	assert.Equal(t, release.RepoRepository, foundRelease.RepoRepository)
}

func TestListRelease(t *testing.T) {
	db, err := InitAddonClusterReleaseTb()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewAddonClusterReleaseDbAccess(db)

	// 创建测试数据
	releases := []model.AddonClusterReleaseModel{
		{
			RepoName:           "test-reponame",
			RepoRepository:     "test-repository",
			ChartVersion:       "test-chartversion",
			ChartName:          "test-chartname",
			Namespace:          "test-namespace",
			K8sClusterConfigID: 1,
			ReleaseName:        "test-release",
			ChartValues:        "test-chart-values",
		},
		{
			RepoName:           "test-reponame2",
			RepoRepository:     "test-repository2",
			ChartVersion:       "test-chartversion2",
			ChartName:          "test-chartname2",
			Namespace:          "test-namespace2",
			K8sClusterConfigID: 2,
			ReleaseName:        "test-release2",
			ChartValues:        "test-chart-values2",
		},
	}

	for _, release := range releases {
		createdRelease, err := dbAccess.Create(&release)
		assert.NotNil(t, createdRelease, err)
	}

	pagination := utils.Pagination{
		Page:  0,
		Limit: 10,
	}

	releaseList, rows, err := dbAccess.ListByPage(pagination)
	assert.NoError(t, err)
	assert.Equal(t, int64(2), rows)
	assert.Equal(t, len(releaseList), len(releases), "Expected number of release to match")

	releaseNames := make(map[string]bool)
	for _, release := range releaseList {
		releaseNames[release.ReleaseName] = true
	}
	for _, expected := range releases {
		assert.True(t, releaseNames[expected.ReleaseName], "Expected release %s not found in the result", expected.ReleaseName)
	}
}

func TestGetClusterReleaseByParams(t *testing.T) {
	db, err := InitAddonClusterReleaseTb()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewAddonClusterReleaseDbAccess(db)
	release := &model.AddonClusterReleaseModel{
		RepoName:           "test-reponame",
		RepoRepository:     "test-repository",
		ChartVersion:       "test-chartversion",
		ChartName:          "test-chartname",
		Namespace:          "test-namespace",
		K8sClusterConfigID: 1,
		ReleaseName:        "test-release",
		ChartValues:        "test-chart-values",
	}
	_, err = dbAccess.Create(release)
	assert.NoError(t, err)

	params := map[string]interface{}{
		"k8s_cluster_config_id": 1,
		"release_name":          "test-release",
		"namespace":             "test-namespace",
	}
	findClusterRelease, err := dbAccess.FindByParams(params)
	assert.NoError(t, err)
	assert.Equal(t, release.RepoName, findClusterRelease.RepoName)
	assert.Equal(t, release.RepoRepository, findClusterRelease.RepoRepository)
	assert.Equal(t, release.ChartVersion, findClusterRelease.ChartVersion)
	assert.Equal(t, release.ChartName, findClusterRelease.ChartName)
	assert.Equal(t, release.Namespace, findClusterRelease.Namespace)
	assert.Equal(t, release.K8sClusterConfigID, findClusterRelease.K8sClusterConfigID)
	assert.Equal(t, release.ReleaseName, findClusterRelease.ReleaseName)
	assert.Equal(t, release.ChartValues, findClusterRelease.ChartValues)
}
