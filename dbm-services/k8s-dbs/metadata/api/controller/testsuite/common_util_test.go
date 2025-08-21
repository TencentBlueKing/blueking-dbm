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

	var removeTimeFields func(obj interface{})
	removeTimeFields = func(obj interface{}) {
		switch v := obj.(type) {
		case map[string]interface{}:
			delete(v, "createdAt")
			delete(v, "updatedAt")
			for _, value := range v {
				removeTimeFields(value)
			}
		case []interface{}:
			for _, item := range v {
				removeTimeFields(item)
			}
		}
	}

	if data, ok := resp["data"]; ok {
		removeTimeFields(data)
		resp["data"] = data
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

func createMoreComponent(mySQLContainer *testhelper.MySQLContainerWrapper, count int) {
	for i := 0; i < count; i++ {
		opsTime, _ := time.Parse(time.DateTime, "2025-01-01 12:00:00")
		db, _ := testhelper.InitDBConnection(mySQLContainer.ConnStr)
		dbAccess := dbaccess.NewK8sCrdComponentAccess(db)
		component := &model.K8sCrdComponentModel{
			ComponentName: "test1",
			CrdClusterID:  1,
			Status:        "CREATED",
			Description:   "just for test",
			CreatedBy:     "admin",
			CreatedAt:     types.JSONDatetime(opsTime),
			UpdatedBy:     "admin",
			UpdatedAt:     types.JSONDatetime(opsTime),
		}
		addedComponent, err := dbAccess.Create(component)
		if err != nil {
			log.Fatal(err)
		}
		log.Printf("Add Sample component %v\n", addedComponent)
	}
}

func createMoreOpsRequest(mySQLContainer *testhelper.MySQLContainerWrapper, count int) {
	for i := 0; i < count; i++ {
		opsTime, _ := time.Parse(time.DateTime, "2025-01-01 12:00:00")
		db, _ := testhelper.InitDBConnection(mySQLContainer.ConnStr)
		dbAccess := dbaccess.NewK8sCrdOpsRequestDbAccess(db)
		opsRequest := &model.K8sCrdOpsRequestModel{
			CrdClusterID:       1,
			K8sClusterConfigID: 1,
			RequestID:          "test-request-001",
			OpsRequestName:     "test-opsrequest",
			OpsRequestType:     "backup",
			Metadata:           `{"labels":{"app":"test"}}`,
			Spec:               `{"backup":{"schedule":"0 2 * * *"}}`,
			Status:             "pending",
			Description:        "Test opsrequest",
			CreatedBy:          "admin",
			CreatedAt:          types.JSONDatetime(opsTime),
			UpdatedBy:          "admin",
			UpdatedAt:          types.JSONDatetime(opsTime),
		}
		addedOpsRequest, err := dbAccess.Create(opsRequest)
		if err != nil {
			log.Fatal(err)
		}
		log.Printf("Add Sample opsrequest %v\n", addedOpsRequest)
	}
}

func createMoreClusterOperation(mySQLContainer *testhelper.MySQLContainerWrapper, count int) {
	for i := 0; i < count; i++ {
		db, _ := testhelper.InitDBConnection(mySQLContainer.ConnStr)
		clusterOpDbAccess := dbaccess.NewClusterOperationDbAccess(db)
		opDefDbAccess := dbaccess.NewOperationDefinitionDbAccess(db)
		opTime, _ := time.Parse(time.DateTime, "2025-01-01 12:00:00")

		operationDefinition := &model.OperationDefinitionModel{
			OperationName:   "test-operation",
			OperationTarget: "cluster",
			Active:          true,
			Description:     "测试操作定义",
			CreatedBy:       "admin",
			UpdatedBy:       "admin",
			CreatedAt:       types.JSONDatetime(opTime),
			UpdatedAt:       types.JSONDatetime(opTime),
		}
		addedOperationDefinition, err := opDefDbAccess.Create(operationDefinition)
		if err != nil {
			log.Fatal(err)
		}

		clusterOperation := &model.ClusterOperationModel{
			AddonType:    "mysql",
			AddonVersion: "8.0",
			OperationID:  addedOperationDefinition.ID,
			Description:  "创建测试集群",
			CreatedBy:    "admin",
			CreatedAt:    types.JSONDatetime(opTime),
			UpdatedBy:    "admin",
			UpdatedAt:    types.JSONDatetime(opTime),
		}
		addedClusterOperation, err := clusterOpDbAccess.Create(clusterOperation)
		if err != nil {
			log.Fatal(err)
		}
		log.Printf("Add Sample cluster operation %v\n", addedClusterOperation)
	}
}

func createMoreClusterRequest(mySQLContainer *testhelper.MySQLContainerWrapper, count int) {
	for i := 0; i < count; i++ {
		db, _ := testhelper.InitDBConnection(mySQLContainer.ConnStr)
		dbAccess := dbaccess.NewClusterRequestRecordDbAccess(db)
		opTime, _ := time.Parse(time.DateTime, "2025-01-01 12:00:00")

		clusterRequest := &model.ClusterRequestRecordModel{
			RequestID:      "req-123456",
			K8sClusterName: "test-k8s-cluster",
			ClusterName:    "test-cluster",
			NameSpace:      "default",
			RequestType:    "CREATE",
			RequestParams:  "{\"param1\":\"value1\",\"param2\":\"value2\"}",
			Status:         "SUCCESS",
			Description:    "创建测试集群",
			CreatedBy:      "admin",
			CreatedAt:      types.JSONDatetime(opTime),
			UpdatedBy:      "admin",
			UpdatedAt:      types.JSONDatetime(opTime),
		}
		addedClusterRequest, err := dbAccess.Create(clusterRequest)
		if err != nil {
			log.Fatal(err)
		}
		log.Printf("Add Sample cluster request %v\n", addedClusterRequest)
	}
}

func createMoreCluster(mySQLContainer *testhelper.MySQLContainerWrapper, count int) {
	for i := 0; i < count; i++ {
		db, _ := testhelper.InitDBConnection(mySQLContainer.ConnStr)
		clusterDbAccess := dbaccess.NewCrdClusterDbAccess(db)
		addonDbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)
		k8sClusterConfigDbAccess := dbaccess.NewK8sClusterConfigDbAccess(db)
		opTime, _ := time.Parse(time.DateTime, "2025-01-01 12:00:00")

		k8sClusterConfig := &model.K8sClusterConfigModel{
			ClusterName:  "test-k8s-cluster",
			APIServerURL: "https://www.example.com",
			CACert:       "test-ca-cert",
			ClientCert:   "test-client-cert",
			ClientKey:    "test-client-key",
			Token:        "test-token",
			Username:     "test-user",
			Password:     "test-password",
			IsPublic:     true,
			RegionName:   "test-region",
			RegionCode:   "test-region-code",
			Provider:     "test-provider",
			Active:       true,
			Description:  "测试K8s集群配置",
			CreatedBy:    "admin",
			CreatedAt:    types.JSONDatetime(opTime),
			UpdatedBy:    "admin",
			UpdatedAt:    types.JSONDatetime(opTime),
		}
		addedK8sConfig, err := k8sClusterConfigDbAccess.Create(k8sClusterConfig)
		if err != nil {
			log.Fatal(err)
		}
		log.Printf("Add Sample k8s cluster config %v\n", addedK8sConfig)

		storageAddon := &model.K8sCrdStorageAddonModel{
			AddonName:          "test-storage-addon",
			AddonVersion:       "1.0.0",
			AddonType:          "storage",
			AddonCategory:      "storage",
			RecommendedVersion: "1.0.0",
			SupportedVersions:  "1.0.0",
			Topologies:         `[{"name":"cluster","isDefault":true,"description":"集群拓扑","components":[]}]`,
			Active:             true,
			Description:        "测试存储插件",
			CreatedBy:          "admin",
			CreatedAt:          types.JSONDatetime(opTime),
			UpdatedBy:          "admin",
			UpdatedAt:          types.JSONDatetime(opTime),
		}
		addedAddon, err := addonDbAccess.Create(storageAddon)
		if err != nil {
			log.Fatal(err)
		}
		log.Printf("Add Sample storage addon %v\n", addedAddon)

		cluster := &model.K8sCrdClusterModel{
			ClusterName:        "test-cluster",
			ClusterAlias:       "Test Cluster",
			BkBizID:            1,
			BkBizName:          "测试业务",
			AddonID:            addedAddon.ID,
			K8sClusterConfigID: addedK8sConfig.ID,
			Namespace:          "default",
			TopoName:           "cluster",
			Status:             "CREATED",
			Description:        "just for test",
			CreatedBy:          "admin",
			CreatedAt:          types.JSONDatetime(opTime),
			UpdatedBy:          "admin",
			UpdatedAt:          types.JSONDatetime(opTime),
		}
		addedCluster, err := clusterDbAccess.Create(cluster)
		if err != nil {
			log.Fatal(err)
		}
		log.Printf("Add Sample cluster %v\n", addedCluster)
	}
}

func createMoreComponentOperation(mySQLContainer *testhelper.MySQLContainerWrapper, count int) {
	for i := 0; i < count; i++ {
		db, _ := testhelper.InitDBConnection(mySQLContainer.ConnStr)
		componentOpDbAccess := dbaccess.NewComponentOperationDbAccess(db)
		opDefDbAccess := dbaccess.NewOperationDefinitionDbAccess(db)
		opTime, _ := time.Parse(time.DateTime, "2025-01-01 12:00:00")

		operationDefinition := &model.OperationDefinitionModel{
			OperationName:   "test-component-operation",
			OperationTarget: "component",
			Active:          true,
			Description:     "测试组件操作定义",
			CreatedBy:       "admin",
			UpdatedBy:       "admin",
			CreatedAt:       types.JSONDatetime(opTime),
			UpdatedAt:       types.JSONDatetime(opTime),
		}
		addedOpDef, err := opDefDbAccess.Create(operationDefinition)
		if err != nil {
			log.Fatal(err)
		}
		log.Printf("Add Sample operation definition %v\n", addedOpDef)

		componentOperation := &model.ComponentOperationModel{
			AddonType:        "mysql",
			AddonVersion:     "8.0",
			ComponentName:    "mysql-server",
			ComponentVersion: "8.0",
			OperationID:      addedOpDef.ID,
			Active:           true,
			Description:      "创建测试组件",
			CreatedBy:        "admin",
			CreatedAt:        types.JSONDatetime(opTime),
			UpdatedBy:        "admin",
			UpdatedAt:        types.JSONDatetime(opTime),
		}
		addedComponentOperation, err := componentOpDbAccess.Create(componentOperation)
		if err != nil {
			log.Fatal(err)
		}
		log.Printf("Add Sample component operation %v\n", addedComponentOperation)
	}
}

func createMoreOperationDefinition(mySQLContainer *testhelper.MySQLContainerWrapper, count int) {
	for i := 0; i < count; i++ {
		opTime, _ := time.Parse(time.DateTime, "2025-01-01 12:00:00")
		db, _ := testhelper.InitDBConnection(mySQLContainer.ConnStr)
		dbAccess := dbaccess.NewOperationDefinitionDbAccess(db)

		operationDefinition := &model.OperationDefinitionModel{
			OperationName:   "test-operation",
			OperationTarget: "cluster",
			Active:          true,
			Description:     "测试操作定义",
			CreatedBy:       "admin",
			UpdatedBy:       "admin",
			CreatedAt:       types.JSONDatetime(opTime),
			UpdatedAt:       types.JSONDatetime(opTime),
		}
		addedOpDef, err := dbAccess.Create(operationDefinition)
		if err != nil {
			log.Fatal(err)
		}
		log.Printf("Add Sample operation definition %v\n", addedOpDef)
	}
}

func createMoreK8sClusterAddons(mySQLContainer *testhelper.MySQLContainerWrapper, count int) {
	for i := 0; i < count; i++ {
		opsTime, _ := time.Parse(time.DateTime, "2025-01-01 12:00:00")
		db, _ := testhelper.InitDBConnection(mySQLContainer.ConnStr)
		saDbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)
		storageAddon := &model.K8sCrdStorageAddonModel{
			AddonName:            "test-addon",
			AddonVersion:         "1.0.0",
			AddonType:            "mysql",
			AddonCategory:        "storage",
			RecommendedVersion:   "1.0.0",
			SupportedVersions:    `["1.0.0"]`,
			RecommendedAcVersion: "1.0.0",
			SupportedAcVersions:  `["1.0.0"]`,
			Topologies:           `[{"name":"cluster","isDefault":true}]`,
			Releases:             `[{"version":"1.0.0"}]`,
			Active:               true,
			Description:          "Test addon",
			CreatedBy:            "admin",
			CreatedAt:            types.JSONDatetime(opsTime),
			UpdatedBy:            "admin",
			UpdatedAt:            types.JSONDatetime(opsTime),
		}
		addedAddon, err := saDbAccess.Create(storageAddon)
		if err != nil {
			log.Fatal(err)
		}

		kcaDbAccess := dbaccess.NewK8sClusterAddonsDbAccess(db)
		clusterAddon := &model.K8sClusterAddonsModel{
			AddonID:        addedAddon.ID,
			K8sClusterName: "test-cluster",
			CreatedBy:      "admin",
			CreatedAt:      types.JSONDatetime(opsTime),
			UpdatedBy:      "admin",
			UpdatedAt:      types.JSONDatetime(opsTime),
		}
		_, err = kcaDbAccess.Create(clusterAddon)
		if err != nil {
			log.Fatal(err)
		}
	}
}

func createMoreK8sClusterConfig(container *testhelper.MySQLContainerWrapper, count int) {
	db, _ := testhelper.InitDBConnection(container.ConnStr)
	dbAccess := dbaccess.NewK8sClusterConfigDbAccess(db)

	for i := 1; i <= count; i++ {
		config := &model.K8sClusterConfigModel{
			ClusterName:  "test-k8s-cluster",
			APIServerURL: "https://www.example.com",
			CACert:       "test-ca-cert",
			ClientCert:   "test-client-cert",
			ClientKey:    "test-client-key",
			Token:        "test-token",
			Username:     "test-user",
			Password:     "test-password",
			IsPublic:     true,
			RegionName:   "test-region",
			RegionCode:   "test-region-code",
			Provider:     "test-provider",
			Active:       true,
			Description:  "测试K8s集群配置",
			CreatedBy:    "admin",
			UpdatedBy:    "admin",
		}
		_, err := dbAccess.Create(config)
		if err != nil {
			log.Fatal(err)
		}
	}
}
