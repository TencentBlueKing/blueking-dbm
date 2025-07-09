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
	entitys "k8s-dbs/metadata/entity"
	testhelper "k8s-dbs/metadata/helper"
	"k8s-dbs/metadata/provider"
	"testing"

	"github.com/stretchr/testify/assert"
)

var sampleAcEntity = &entitys.AddonClusterVersionEntity{
	AddonID:          1,
	AddonClusterName: "victoriametrics-1.0.0",
	Version:          "1.0.0",
	Description:      "desc",
}

func TestCreateAcVersion(t *testing.T) {
	dbAccess := testhelper.GetAcVersionTestDbAccess()
	acVersionProvider := provider.NewAddonClusterVersionProvider(dbAccess)
	added, err := acVersionProvider.CreateAcVersion(sampleAcEntity)
	assert.NoError(t, err)
	assert.Equal(t, sampleAcEntity.AddonID, added.AddonID)
	assert.Equal(t, sampleAcEntity.Version, added.Version)
	assert.Equal(t, sampleAcEntity.AddonClusterName, added.AddonClusterName)
	assert.Equal(t, sampleAcEntity.Description, added.Description)
}

func TestDeleteAcVersion(t *testing.T) {
	dbAccess := testhelper.GetAcVersionTestDbAccess()
	acVersionProvider := provider.NewAddonClusterVersionProvider(dbAccess)
	_, err := acVersionProvider.CreateAcVersion(sampleAcEntity)
	assert.NoError(t, err)

	rows, err := acVersionProvider.DeleteAcVersionByID(1)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateAcVersion(t *testing.T) {
	dbAccess := testhelper.GetAcVersionTestDbAccess()
	acVersionProvider := provider.NewAddonClusterVersionProvider(dbAccess)
	_, err := acVersionProvider.CreateAcVersion(sampleAcEntity)
	assert.NoError(t, err)

	newAcVersion := &entitys.AddonClusterVersionEntity{
		ID:               1,
		AddonID:          1,
		AddonClusterName: "victoriametrics-2.0.0",
		Version:          "2.0.0",
		Description:      "desc",
	}
	rows, err := acVersionProvider.UpdateAcVersion(newAcVersion)
	assert.Equal(t, uint64(1), rows)
}
