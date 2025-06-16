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

func TestCreateRepo(t *testing.T) {
	db, err := InitAddonClusterHelmRepoTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterHelmRepoDbAccess(db)
	repo := &model.AddonClusterHelmRepoModel{
		RepoName:       "test-reponame",
		RepoRepository: "test-repository",
		RepoUsername:   "test-username",
		RepoPassword:   "test-password",
		ChartVersion:   "test-chartversion",
		ChartName:      "test-chartname",
	}

	addedRepo, err := dbAccess.Create(repo)
	assert.NoError(t, err)
	assert.Equal(t, repo.RepoName, addedRepo.RepoName)
	assert.Equal(t, repo.RepoRepository, addedRepo.RepoRepository)
	assert.Equal(t, repo.RepoUsername, addedRepo.RepoUsername)
	assert.Equal(t, repo.RepoPassword, addedRepo.RepoPassword)
	assert.Equal(t, repo.ChartVersion, addedRepo.ChartVersion)
	assert.Equal(t, repo.ChartName, addedRepo.ChartName)
}

func TestDeleteRepo(t *testing.T) {
	db, err := InitAddonClusterHelmRepoTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterHelmRepoDbAccess(db)
	repo := &model.AddonClusterHelmRepoModel{
		RepoName:       "test-reponame",
		RepoRepository: "test-repository",
		RepoUsername:   "test-username",
		RepoPassword:   "test-password",
		ChartVersion:   "test-chartversion",
		ChartName:      "test-chartname",
	}

	_, err = dbAccess.Create(repo)
	assert.NoError(t, err)

	rows, err := dbAccess.DeleteByID(1)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateRepo(t *testing.T) {
	db, err := InitAddonClusterHelmRepoTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterHelmRepoDbAccess(db)
	repo := &model.AddonClusterHelmRepoModel{
		ID:             1,
		RepoName:       "test-reponame",
		RepoRepository: "test-repository",
		RepoUsername:   "test-username",
		RepoPassword:   "test-password",
		ChartVersion:   "test-chartversion",
		ChartName:      "test-chartname",
		CreatedBy:      "test-createdby",
	}

	_, err = dbAccess.Create(repo)
	assert.NoError(t, err)

	updateRepo := &model.AddonClusterHelmRepoModel{
		ID:             1,
		RepoName:       "test-reponame2",
		RepoRepository: "test-repository2",
		RepoUsername:   "test-username2",
		RepoPassword:   "test-password2",
		ChartVersion:   "test-chartversion2",
		ChartName:      "test-chartname2",
	}
	rows, err := dbAccess.Update(updateRepo)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestGetRepo(t *testing.T) {
	db, err := InitAddonClusterHelmRepoTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterHelmRepoDbAccess(db)
	repo := &model.AddonClusterHelmRepoModel{
		RepoName:       "test-reponame",
		RepoRepository: "test-repository",
		RepoUsername:   "test-username",
		RepoPassword:   "test-password",
		ChartVersion:   "test-chartversion",
		ChartName:      "test-chartname",
	}

	_, err = dbAccess.Create(repo)
	assert.NoError(t, err)

	foundRepo, err := dbAccess.FindByID(1)
	assert.NoError(t, err)
	assert.Equal(t, repo.RepoName, foundRepo.RepoName)
	assert.Equal(t, repo.RepoRepository, foundRepo.RepoRepository)
	assert.Equal(t, repo.RepoUsername, foundRepo.RepoUsername)
	assert.Equal(t, repo.RepoPassword, foundRepo.RepoPassword)
	assert.Equal(t, repo.ChartVersion, foundRepo.ChartVersion)
	assert.Equal(t, repo.ChartName, foundRepo.ChartName)
}

func TestListRepo(t *testing.T) {
	db, err := InitAddonClusterHelmRepoTb()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewAddonClusterHelmRepoDbAccess(db)

	repos := []model.AddonClusterHelmRepoModel{
		{
			RepoName:       "test-reponame",
			RepoRepository: "test-repository",
			RepoUsername:   "test-username",
			RepoPassword:   "test-password",
			ChartVersion:   "test-chartversion",
			ChartName:      "test-chartname",
		},
		{
			RepoName:       "test-reponame2",
			RepoRepository: "test-repository2",
			RepoUsername:   "test-username2",
			RepoPassword:   "test-password2",
			ChartVersion:   "test-chartversion2",
			ChartName:      "test-chartname2",
		},
	}

	for _, repo := range repos {
		createdRepo, err := dbAccess.Create(&repo)
		assert.NotNil(t, createdRepo, err)
	}

	pagination := utils.Pagination{
		Page:  0,
		Limit: 10,
	}

	repoList, rows, err := dbAccess.ListByPage(pagination)
	assert.NoError(t, err)
	assert.Equal(t, int64(2), rows)
	assert.Equal(t, len(repoList), len(repos))

	repoNames := make(map[string]bool)
	for _, repo := range repoList {
		repoNames[repo.ChartName] = true
	}
	for _, expected := range repos {
		assert.True(t, repoNames[expected.ChartName], "Expected repo %s not found in the result", expected.ChartName)
	}
}

func TestGetRepoByParams(t *testing.T) {
	db, err := InitAddonClusterHelmRepoTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonClusterHelmRepoDbAccess(db)
	repo := &model.AddonClusterHelmRepoModel{
		RepoName:       "test-reponame",
		RepoRepository: "test-repository",
		RepoUsername:   "test-username",
		RepoPassword:   "test-password",
		ChartVersion:   "test-chartversion",
		ChartName:      "test-chartname",
	}

	_, err = dbAccess.Create(repo)
	assert.NoError(t, err)

	params := map[string]interface{}{
		"chart_name":    "test-chartname",
		"chart_version": "test-chartversion",
		"repo_name":     "test-reponame",
	}
	foundRepo, err := dbAccess.FindByParams(params)
	assert.NoError(t, err)
	assert.Equal(t, repo.RepoName, foundRepo.RepoName)
	assert.Equal(t, repo.RepoRepository, foundRepo.RepoRepository)
	assert.Equal(t, repo.RepoUsername, foundRepo.RepoUsername)
	assert.Equal(t, repo.RepoPassword, foundRepo.RepoPassword)
	assert.Equal(t, repo.ChartVersion, foundRepo.ChartVersion)
	assert.Equal(t, repo.ChartName, foundRepo.ChartName)
}
