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
	"k8s-dbs/metadata/dbaccess/model"
	"testing"
	"time"

	testhelper "k8s-dbs/metadata/helper"

	"github.com/stretchr/testify/assert"
)

var sampleVersion = &model.AddonClusterVersionModel{
	AddonID:          1,
	AddonClusterName: "victoriametrics-1.0.0",
	Version:          "1.0.0",
	Description:      "desc",
}

func TestCreateAcVersion(t *testing.T) {
	dbAccess := testhelper.GetAcVersionTestDbAccess()
	added, err := dbAccess.Create(sampleVersion)
	assert.NoError(t, err)
	assert.Equal(t, sampleVersion.AddonID, added.AddonID)
	assert.Equal(t, sampleVersion.AddonClusterName, added.AddonClusterName)
	assert.Equal(t, sampleVersion.Version, added.Version)
	assert.Equal(t, sampleVersion.Description, added.Description)
}

func TestDeleteAcVersion(t *testing.T) {
	dbAccess := testhelper.GetAcVersionTestDbAccess()
	_, err := dbAccess.Create(sampleVersion)
	assert.NoError(t, err)

	rows, err := dbAccess.DeleteByID(1)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateAcVersion(t *testing.T) {
	dbAccess := testhelper.GetAcVersionTestDbAccess()
	_, err := dbAccess.Create(sampleVersion)
	assert.NoError(t, err)

	newVersion := &model.AddonClusterVersionModel{
		ID:               1,
		AddonID:          1,
		AddonClusterName: "victoriametrics-2.0.0",
		Version:          "2.0.0",
		Description:      "desc",
		UpdatedAt:        time.Now(),
	}
	rows, err := dbAccess.Update(newVersion)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestGetAcVersionByParams(t *testing.T) {
	dbAccess := testhelper.GetAcVersionTestDbAccess()
	_, err := dbAccess.Create(sampleVersion)
	assert.NoError(t, err)

	params := map[string]interface{}{
		"addon_id": 1,
	}
	foundVersions, err := dbAccess.FindByParams(params)
	assert.NoError(t, err)
	assert.Equal(t, 1, len(foundVersions))
}
