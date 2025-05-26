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
	"k8s-dbs/metadata/provider"
	entitys "k8s-dbs/metadata/provider/entity"
	"k8s-dbs/metadata/utils"
	"testing"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func InitClusterReleaseTb() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_addoncluster_release;").Error; err != nil {
		fmt.Println("Failed to drop tb_addoncluster_release table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.AddonClusterReleaseModel{}); err != nil {
		fmt.Println("Failed to migrate tb_addoncluster_release table")
		return nil, err
	}
	return db, nil
}

func TestClusterRelease(t *testing.T) {
	db, err := InitClusterReleaseTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterReleaseDbAccess(db)
	releaseProvider := provider.NewAddonClusterReleaseProvider(dbAccess)
	release := &entitys.AddonClusterReleaseEntity{
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

	addedRelease, err := releaseProvider.CreateClusterRelease(release)
	assert.NoError(t, err, "Failed to create")
	assert.Equal(t, addedRelease.ReleaseName, release.ReleaseName)
	assert.Equal(t, addedRelease.Namespace, release.Namespace)
	assert.Equal(t, addedRelease.K8sClusterConfigID, release.K8sClusterConfigID)
}

func TestDeleteClusterRelease(t *testing.T) {
	db, err := InitClusterReleaseTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterReleaseDbAccess(db)
	releaseProvider := provider.NewAddonClusterReleaseProvider(dbAccess)
	release := &entitys.AddonClusterReleaseEntity{
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

	_, err = releaseProvider.CreateClusterRelease(release)
	assert.NoError(t, err, "Failed to create")

	rows, err := releaseProvider.DeleteClusterReleaseByID(1)
	assert.NoError(t, err, "Failed to delete")
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateClusterRelease(t *testing.T) {
	db, err := InitClusterReleaseTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterReleaseDbAccess(db)
	releaseProvider := provider.NewAddonClusterReleaseProvider(dbAccess)
	release := &entitys.AddonClusterReleaseEntity{
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

	_, err = releaseProvider.CreateClusterRelease(release)
	assert.NoError(t, err, "Failed to create")

	updatedRelease := &entitys.AddonClusterReleaseEntity{
		ID:                 1,
		RepoName:           "test-reponame2",
		RepoRepository:     "test-repository2",
		ChartVersion:       "test-chartversion2",
		ChartName:          "test-chartname2",
		Namespace:          "test-namespace2",
		K8sClusterConfigID: 1,
		ReleaseName:        "test-release2",
		ChartValues:        "test-chart-values2",
		CreatedBy:          "alex",
	}
	rows, err := releaseProvider.UpdateClusterRelease(updatedRelease)
	assert.NoError(t, err, "Failed to update")
	assert.Equal(t, uint64(1), rows)
}

func TestListClusterRelease(t *testing.T) {
	db, err := InitClusterReleaseTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterReleaseDbAccess(db)
	releaseProvider := provider.NewAddonClusterReleaseProvider(dbAccess)
	releases := []entitys.AddonClusterReleaseEntity{
		{
			RepoName:           "test-reponame",
			RepoRepository:     "test-repository",
			ChartVersion:       "test-chartversion",
			ChartName:          "test-chartname",
			Namespace:          "test-namespace",
			K8sClusterConfigID: 1,
			ReleaseName:        "test-release",
			ChartValues:        "test-chart-values",
			CreatedBy:          "alex",
		},
		{
			RepoName:           "test-reponame2",
			RepoRepository:     "test-repository2",
			ChartVersion:       "test-chartversion2",
			ChartName:          "test-chartname2",
			Namespace:          "test-namespace2",
			K8sClusterConfigID: 1,
			ReleaseName:        "test-release2",
			ChartValues:        "test-chart-values2",
			CreatedBy:          "alex2",
		},
	}

	for _, release := range releases {
		_, err := releaseProvider.CreateClusterRelease(&release)
		assert.NoError(t, err)
	}

	pagination := utils.Pagination{
		Page:  0,
		Limit: 10,
	}

	releaseList, err := releaseProvider.ListClusterReleases(pagination)
	assert.NoError(t, err, "Failed to list storage addons")
	assert.Equal(t, len(releases), len(releaseList))

	releaseNames := make(map[string]bool)
	for _, r := range releaseList {
		releaseNames[r.ReleaseName] = true
	}

	for _, expected := range releases {
		assert.True(t, releaseNames[expected.ReleaseName], "Expected %s not found in the result", expected.ReleaseName)
	}
}

func TestGetClusterReleaseByParams(t *testing.T) {
	db, err := initClusterTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewAddonClusterReleaseDbAccess(db)
	releaseProvider := provider.NewAddonClusterReleaseProvider(dbAccess)

	release := &entitys.AddonClusterReleaseEntity{
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

	addedCluster, err := releaseProvider.CreateClusterRelease(release)
	assert.NoError(t, err, "Failed to create addon cluster release")
	fmt.Printf("Created addon cluster release %+v\n", addedCluster)

	params := map[string]interface{}{
		"release_name": "test-release",
		"namespace":    "test-namespace",
	}
	foundClusterRelease, err := dbAccess.FindByParams(params)
	assert.NoError(t, err, "Failed to find addon cluster release")
	assert.Equal(t, release.RepoName, foundClusterRelease.RepoName)
	assert.Equal(t, release.RepoRepository, foundClusterRelease.RepoRepository)
	assert.Equal(t, release.ChartVersion, foundClusterRelease.ChartVersion)
	assert.Equal(t, release.Namespace, foundClusterRelease.Namespace)
	assert.Equal(t, release.K8sClusterConfigID, foundClusterRelease.K8sClusterConfigID)
	assert.Equal(t, release.ReleaseName, foundClusterRelease.ReleaseName)
	assert.Equal(t, release.ChartValues, foundClusterRelease.ChartValues)
	assert.Equal(t, release.CreatedBy, foundClusterRelease.CreatedBy)
}
