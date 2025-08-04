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
	"k8s-dbs/metadata/model"
	"testing"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

var repo = &model.AddonTypeModel{
	CategoryID:  10086,
	TypeName:    "test-typename",
	TypeAlias:   "test-typealias",
	Active:      true,
	Description: "test-description",
}

var repos = []model.AddonTypeModel{
	{
		CategoryID:  10086,
		TypeName:    "test-typename",
		TypeAlias:   "test-typealias",
		Active:      true,
		Description: "test-description",
	},
	{
		CategoryID:  10086,
		TypeName:    "test-tpyename2",
		TypeAlias:   "test-typealias2",
		Active:      true,
		Description: "test-description2",
	},
}

func InitAddonTypeTb() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_addon_type;").Error; err != nil {
		fmt.Println("Failed to drop tb_addon_type table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.AddonTypeModel{}); err != nil {
		fmt.Println("Failed to migrate tb_addon_type table")
		return nil, err
	}
	return db, nil
}

func TestCreateAddonTypeRepo(t *testing.T) {
	db, err := InitAddonTypeTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonTypeDbAccess(db)
	addedRepo, err := dbAccess.Create(repo)
	assert.NoError(t, err)
	assert.Equal(t, repo.CategoryID, addedRepo.CategoryID)
	assert.Equal(t, repo.TypeName, addedRepo.TypeName)
	assert.Equal(t, repo.TypeAlias, addedRepo.TypeAlias)
	assert.Equal(t, repo.Active, addedRepo.Active)
	assert.Equal(t, repo.Description, addedRepo.Description)

}

func TestFindByIdAddonTypeRepo(t *testing.T) {
	db, err := InitAddonTypeTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonTypeDbAccess(db)
	_, err = dbAccess.Create(repo)
	assert.NoError(t, err)

	foundRepo, err := dbAccess.FindByID(1)
	assert.Equal(t, repo.CategoryID, foundRepo.CategoryID)
	assert.Equal(t, repo.TypeName, foundRepo.TypeName)
	assert.Equal(t, repo.TypeAlias, foundRepo.TypeAlias)
	assert.Equal(t, repo.Active, foundRepo.Active)
	assert.Equal(t, repo.Description, foundRepo.Description)

}

func TestFindByCategoryIdAddonTypeRepo(t *testing.T) {
	db, err := InitAddonTypeTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonTypeDbAccess(db)
	for _, repo := range repos {
		_, err = dbAccess.Create(&repo)
		assert.NoError(t, err)
	}

	repoList, err := dbAccess.FindByCategoryID(10086)
	assert.NoError(t, err)
	assert.Equal(t, len(repoList), len(repos))

	repoNames := make(map[string]bool)
	for _, repo := range repoList {
		repoNames[repo.TypeName] = true
	}
	for _, expected := range repos {
		assert.True(t, repoNames[expected.TypeName], expected.TypeName)
	}
}

func TestListAddonTypeRepo(t *testing.T) {
	db, err := InitAddonTypeTb()
	assert.NoError(t, err)
	dbAccess := dbaccess.NewAddonTypeDbAccess(db)
	for _, repo := range repos {
		_, err = dbAccess.Create(&repo)
		assert.NoError(t, err)
	}

	repoList, err := dbAccess.ListByLimit(2)
	assert.NoError(t, err)
	assert.Equal(t, len(repoList), len(repos))

	repoNames := make(map[string]bool)
	for _, repo := range repoList {
		repoNames[repo.TypeName] = true
	}
	for _, expected := range repos {
		assert.True(t, repoNames[expected.TypeName], expected.TypeName)
	}

}
