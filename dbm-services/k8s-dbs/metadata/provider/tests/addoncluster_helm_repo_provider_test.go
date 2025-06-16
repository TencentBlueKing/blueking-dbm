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

func InitAddonClusterHelmRepoTb() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_addoncluster_helm_repository;").Error; err != nil {
		fmt.Println("Failed to drop tb_addoncluster_helm_repository table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.AddonClusterHelmRepoModel{}); err != nil {
		fmt.Println("Failed to migrate tb_addoncluster_helm_repository table")
		return nil, err
	}
	return db, nil
}

func TestCreateClusterHelmRepo(t *testing.T) {
	db, err := InitAddonClusterHelmRepoTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterHelmRepoDbAccess(db)
	repoProvider := provider.NewAddonClusterHelmRepoProvider(dbAccess)
	repo := &entitys.AddonClusterHelmRepoEntity{
		RepoName:       "test-reponame",
		RepoRepository: "test-repository",
		RepoUsername:   "test-username",
		RepoPassword:   "test-password",
		ChartVersion:   "test-chartversion",
		ChartName:      "test-chartname",
	}

	added, err := repoProvider.CreateHelmRepo(repo)
	assert.NoError(t, err)
	assert.Equal(t, added.RepoName, repo.RepoName)
	assert.Equal(t, added.RepoRepository, repo.RepoRepository)
	assert.Equal(t, added.RepoUsername, repo.RepoUsername)
	assert.Equal(t, added.RepoPassword, repo.RepoPassword)
	assert.Equal(t, added.ChartVersion, repo.ChartVersion)
	assert.Equal(t, added.ChartName, repo.ChartName)
}

func TestDeleteClusterHelmRepo(t *testing.T) {
	db, err := InitAddonClusterHelmRepoTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterHelmRepoDbAccess(db)
	repoProvider := provider.NewAddonClusterHelmRepoProvider(dbAccess)
	repo := &entitys.AddonClusterHelmRepoEntity{
		RepoName:       "test-reponame",
		RepoRepository: "test-repository",
		RepoUsername:   "test-username",
		RepoPassword:   "test-password",
		ChartVersion:   "test-chartversion",
		ChartName:      "test-chartname",
	}

	_, err = repoProvider.CreateHelmRepo(repo)
	assert.NoError(t, err)

	rows, err := repoProvider.DeleteHelmRepoByID(1)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateClusterHelmRepo(t *testing.T) {
	db, err := InitAddonClusterHelmRepoTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterHelmRepoDbAccess(db)
	repoProvider := provider.NewAddonClusterHelmRepoProvider(dbAccess)
	repo := &entitys.AddonClusterHelmRepoEntity{
		RepoName:       "test-reponame",
		RepoRepository: "test-repository",
		RepoUsername:   "test-username",
		RepoPassword:   "test-password",
		ChartVersion:   "test-chartversion",
		ChartName:      "test-chartname",
	}

	_, err = repoProvider.CreateHelmRepo(repo)
	assert.NoError(t, err)

	updateRepo := &entitys.AddonClusterHelmRepoEntity{
		ID:             1,
		RepoName:       "test-reponame",
		RepoRepository: "test-repository",
		RepoUsername:   "test-username",
		RepoPassword:   "test-password",
		ChartVersion:   "test-chartversion",
		ChartName:      "test-chartname",
	}
	rows, err := repoProvider.UpdateHelmRepo(updateRepo)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestListClusterHelmRepo(t *testing.T) {
	db, err := InitAddonClusterHelmRepoTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterHelmRepoDbAccess(db)
	repoProvider := provider.NewAddonClusterHelmRepoProvider(dbAccess)
	repos := []entitys.AddonClusterHelmRepoEntity{
		{
			RepoName:       "test-reponame",
			RepoRepository: "test-repository",
			ChartVersion:   "test-chartversion",
			ChartName:      "test-chartname",
			CreatedBy:      "test-user",
		},
		{
			RepoName:       "test-reponame2",
			RepoRepository: "test-repository2",
			ChartVersion:   "test-chartversion2",
			ChartName:      "test-chartname2",
			CreatedBy:      "test-user",
		},
	}

	for _, repo := range repos {
		_, err := repoProvider.CreateHelmRepo(&repo)
		assert.NoError(t, err)
	}

	pagination := utils.Pagination{
		Page:  0,
		Limit: 10,
	}

	foundRepos, err := repoProvider.ListHelmRepos(pagination)
	assert.NoError(t, err)
	assert.Equal(t, len(repos), len(foundRepos))

	repoNames := make(map[string]bool)

	for _, r := range foundRepos {
		repoNames[r.RepoName] = true
	}

	for _, expected := range repos {
		assert.True(t, repoNames[expected.RepoName], "Expected %s not found in the result", expected.RepoName)
	}
}

func TestGetClusterHelmRepo(t *testing.T) {
	db, err := InitAddonClusterHelmRepoTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterHelmRepoDbAccess(db)
	repoProvider := provider.NewAddonClusterHelmRepoProvider(dbAccess)
	repo := &entitys.AddonClusterHelmRepoEntity{
		RepoName:       "test-reponame",
		RepoRepository: "test-repository",
		RepoUsername:   "test-username",
		RepoPassword:   "test-password",
		ChartVersion:   "test-chartversion",
		ChartName:      "test-chartname",
	}

	_, err = repoProvider.CreateHelmRepo(repo)
	assert.NoError(t, err)

	params := map[string]interface{}{
		"chart_name":    "test-chartname",
		"chart_version": "test-chartversion",
		"repo_name":     "test-reponame",
	}
	foundRepo, err := repoProvider.FindByParams(params)
	assert.NoError(t, err)
	assert.Equal(t, repo.RepoName, foundRepo.RepoName)
	assert.Equal(t, repo.RepoRepository, foundRepo.RepoRepository)
	assert.Equal(t, repo.RepoUsername, foundRepo.RepoUsername)
	assert.Equal(t, repo.RepoPassword, foundRepo.RepoPassword)
	assert.Equal(t, repo.ChartVersion, foundRepo.ChartVersion)
	assert.Equal(t, repo.ChartName, foundRepo.ChartName)
}
