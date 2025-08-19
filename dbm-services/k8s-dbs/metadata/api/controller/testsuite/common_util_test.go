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
	"encoding/json"
	"k8s-dbs/common/entity"
	"k8s-dbs/common/types"
	"k8s-dbs/metadata/dbaccess"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"log"
	"time"
)

var baseBKAuth = entity.BKAuth{
	BkAppCode:   "bk_app_code",
	BkAppSecret: "bk_app_secret",
	BkUserName:  "admin",
}

func deleteTimeColumn(body []byte) string {
	var resp map[string]interface{}
	_ = json.Unmarshal(body, &resp)
	if data, ok := resp["data"].(map[string]interface{}); ok {
		delete(data, "createdAt")
		delete(data, "updatedAt")
		resp["data"] = data
		result, _ := json.Marshal(resp)
		return string(result)
	}
	if list, ok := resp["data"].([]interface{}); ok {
		for _, item := range list {
			if m, ok := item.(map[string]interface{}); ok {
				delete(m, "createdAt")
				delete(m, "updatedAt")
			}
		}
		resp["data"] = list
		result, _ := json.Marshal(resp)
		return string(result)
	}
	return "{}"
}

func createMoreAddonCategory(mySQLContainer *testhelper.MySQLContainerWrapper, count int) {
	for i := 0; i < count; i++ {
		opsTime, _ := time.Parse(time.DateTime, "2025-01-01 12:00:00")
		db, _ := testhelper.InitDBConnection(mySQLContainer.ConnStr)
		dbAccess := dbaccess.NewAddonCategoryDbAccess(db)
		category := &model.AddonCategoryModel{
			CategoryName:  "category_name_01",
			CategoryAlias: "category_alias_01",
			Active:        true,
			Description:   "description_01",
			CreatedBy:     "admin",
			CreatedAt:     types.JSONDatetime(opsTime),
			UpdatedBy:     "admin",
			UpdatedAt:     types.JSONDatetime(opsTime),
		}
		addedCategory, err := dbAccess.Create(category)
		if err != nil {
			log.Fatal(err)
		}
		log.Println("Add Sample category ", addedCategory)
	}
}

func createMoreAddonType(mySQLContainer *testhelper.MySQLContainerWrapper, count int) {
	for i := 0; i < count; i++ {
		opsTime, _ := time.Parse(time.DateTime, "2025-01-01 12:00:00")
		db, _ := testhelper.InitDBConnection(mySQLContainer.ConnStr)
		dbAccess := dbaccess.NewAddonTypeDbAccess(db)
		addonType := &model.AddonTypeModel{
			CategoryID:  uint64(1),
			TypeName:    "addon_type_name_01",
			TypeAlias:   "addon_type_alias_01",
			Description: "addon_type_description_01",
			Active:      true,
			CreatedBy:   "admin",
			CreatedAt:   types.JSONDatetime(opsTime),
			UpdatedBy:   "admin",
			UpdatedAt:   types.JSONDatetime(opsTime),
		}
		addedType, err := dbAccess.Create(addonType)
		if err != nil {
			log.Fatal(err)
		}
		log.Println("Add Sample addon type ", addedType)
	}
}

func createMoreAddonHelmRepo(mySQLContainer *testhelper.MySQLContainerWrapper, count int) {
	for i := 0; i < count; i++ {
		opsTime, _ := time.Parse(time.DateTime, "2025-01-01 12:00:00")
		db, _ := testhelper.InitDBConnection(mySQLContainer.ConnStr)
		dbAccess := dbaccess.NewAddonHelmRepoDbAccess(db)
		addonHelmRepo := &model.AddonHelmRepoModel{
			RepoName:       "repo_name_01",
			RepoRepository: "repo_repository_01",
			RepoUsername:   "repo_username_01",
			RepoPassword:   "repo_password_01",
			ChartName:      "chart_name_01",
			ChartVersion:   "chart_version_01",
			CreatedBy:      "admin",
			CreatedAt:      types.JSONDatetime(opsTime),
			UpdatedBy:      "admin",
			UpdatedAt:      types.JSONDatetime(opsTime),
		}
		addedRepo, err := dbAccess.Create(addonHelmRepo)
		if err != nil {
			log.Fatal(err)
		}
		log.Println("Add Sample addon helm repo ", addedRepo)
	}
}

func createMoreAddon(mySQLContainer *testhelper.MySQLContainerWrapper, count int) {
	for i := 0; i < count; i++ {
		opsTime, _ := time.Parse(time.DateTime, "2025-01-01 12:00:00")
		db, _ := testhelper.InitDBConnection(mySQLContainer.ConnStr)
		dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)
		addonRequest := &model.K8sCrdStorageAddonModel{
			AddonName:            "addon_name_01",
			AddonCategory:        "addon_category_01",
			AddonType:            "addon_type_01",
			AddonVersion:         "addon_version_01",
			RecommendedVersion:   "recommended_version_01",
			SupportedVersions:    `["supported_versions_01", "supported_versions_02"]`,
			RecommendedAcVersion: "recommended_ac_version_01",
			SupportedAcVersions:  `["supported_ac_versions_01", "supported_ac_versions_02"]`,
			Topologies:           `[{"name": "topology_01"}]`,
			Releases:             `[{"version": "1.0"}]`,
			Description:          "description_01",
			CreatedBy:            "admin",
			CreatedAt:            types.JSONDatetime(opsTime),
			UpdatedBy:            "admin",
			UpdatedAt:            types.JSONDatetime(opsTime),
		}
		addedAddon, err := dbAccess.Create(addonRequest)
		if err != nil {
			log.Fatal(err)
		}
		log.Println("Add Sample addon ", addedAddon)
	}
}

func createMoreAddonTopology(mySQLContainer *testhelper.MySQLContainerWrapper, count int) {
	for i := 0; i < count; i++ {
		opsTime, _ := time.Parse(time.DateTime, "2025-01-01 12:00:00")
		db, _ := testhelper.InitDBConnection(mySQLContainer.ConnStr)
		dbAccess := dbaccess.NewAddonTopologyDbAccess(db)
		addonTopology := &model.AddonTopologyModel{
			AddonName:     "addon_name_01",
			AddonCategory: "addon_category_01",
			AddonType:     "addon_type_01",
			AddonVersion:  "addon_version_01",
			TopologyName:  "topology_name_01",
			TopologyAlias: "topology_alias_01",
			IsDefault:     true,
			Components:    "{\"component1\": \"version1\", \"component2\": \"version2\"}",
			Relations:     "{\"relation1\": \"component1\", \"relation2\": \"component2\"}",
			Active:        true,
			Description:   "description_01",
			CreatedBy:     "admin",
			CreatedAt:     types.JSONDatetime(opsTime),
			UpdatedBy:     "admin",
			UpdatedAt:     types.JSONDatetime(opsTime),
		}
		addedTopology, err := dbAccess.Create(addonTopology)
		if err != nil {
			log.Fatal(err)
		}
		log.Println("Add Sample addon topology ", addedTopology)
	}
}

func createMoreAddonClusterHelmRepo(mySQLContainer *testhelper.MySQLContainerWrapper, count int) {
	for i := 0; i < count; i++ {
		opsTime, _ := time.Parse(time.DateTime, "2025-01-01 12:00:00")
		db, _ := testhelper.InitDBConnection(mySQLContainer.ConnStr)
		dbAccess := dbaccess.NewAddonClusterHelmRepoDbAccess(db)
		addonClusterHelmRepo := &model.AddonClusterHelmRepoModel{
			RepoName:       "repo_name_01",
			RepoRepository: "repo_repository_01",
			RepoUsername:   "repo_username_01",
			RepoPassword:   "repo_password_01",
			ChartName:      "chart_name_01",
			ChartVersion:   "chart_version_01",
			CreatedBy:      "admin",
			CreatedAt:      types.JSONDatetime(opsTime),
			UpdatedBy:      "admin",
			UpdatedAt:      types.JSONDatetime(opsTime),
		}
		addedRepo, err := dbAccess.Create(addonClusterHelmRepo)
		if err != nil {
			log.Fatal(err)
		}
		log.Println("Add Sample addon cluster helm repo ", addedRepo)
	}
}

func createMoreAddonClusterRelease(mySQLContainer *testhelper.MySQLContainerWrapper, count int) {
	for i := 0; i < count; i++ {
		opsTime, _ := time.Parse(time.DateTime, "2025-01-01 12:00:00")
		db, _ := testhelper.InitDBConnection(mySQLContainer.ConnStr)
		dbAccess := dbaccess.NewAddonClusterReleaseDbAccess(db)
		addonClusterRelease := &model.AddonClusterReleaseModel{
			RepoName:           "repo_name_01",
			RepoRepository:     "repo_repository_01",
			ChartVersion:       "chart_version_01",
			ChartName:          "chart_name_01",
			Namespace:          "namespace_01",
			K8sClusterConfigID: uint64(1),
			ReleaseName:        "release_name_01",
			ChartValues:        "{}",
			CreatedBy:          "admin",
			CreatedAt:          types.JSONDatetime(opsTime),
			UpdatedBy:          "admin",
			UpdatedAt:          types.JSONDatetime(opsTime),
		}
		addedRelease, err := dbAccess.Create(addonClusterRelease)
		if err != nil {
			log.Fatal(err)
		}
		log.Println("Add Sample addon cluster release ", addedRelease)
	}
}

func createMoreAddonClusterVersion(mySQLContainer *testhelper.MySQLContainerWrapper, count int) {
	for i := 0; i < count; i++ {
		opsTime, _ := time.Parse(time.DateTime, "2025-01-01 12:00:00")
		db, _ := testhelper.InitDBConnection(mySQLContainer.ConnStr)
		dbAccess := dbaccess.NewAddonClusterVersionDbAccess(db)
		addonClusterVersion := &model.AddonClusterVersionModel{
			AddonID:          uint64(1),
			Version:          "1.0.0",
			AddonClusterName: "addon_cluster_name_01",
			Active:           true,
			Description:      "addon_cluster_version_description_01",
			CreatedBy:        "admin",
			CreatedAt:        types.JSONDatetime(opsTime),
			UpdatedBy:        "admin",
			UpdatedAt:        types.JSONDatetime(opsTime),
		}
		addedVersion, err := dbAccess.Create(addonClusterVersion)
		if err != nil {
			log.Fatal(err)
		}
		log.Println("Add Sample addon cluster version ", addedVersion)
	}
}
