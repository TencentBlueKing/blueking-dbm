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
	testhelper "k8s-dbs/metadata/helper"
	"k8s-dbs/metadata/model"
	"testing"

	"github.com/stretchr/testify/assert"
)

var sampleTag = &model.K8sCrdClusterTagModel{
	CrdClusterID: 1,
	ClusterTag:   "test",
}

var batchSampleTags = []*model.K8sCrdClusterTagModel{
	{
		CrdClusterID: 1,
		ClusterTag:   "test",
	},
	{
		CrdClusterID: 1,
		ClusterTag:   "test2",
	},
}

func TestCreateTag(t *testing.T) {
	dbAccess := testhelper.GetClusterTagTestDbAccess()
	added, err := dbAccess.Create(sampleTag)
	assert.NoError(t, err)
	assert.Equal(t, sampleTag.CrdClusterID, added.CrdClusterID)
	assert.Equal(t, sampleTag.ClusterTag, added.ClusterTag)
}

func TestBatchCreateTags(t *testing.T) {
	dbAccess := testhelper.GetClusterTagTestDbAccess()
	rows, err := dbAccess.BatchCreate(batchSampleTags)
	assert.NoError(t, err)
	assert.Equal(t, uint64(2), rows)
}

func TestDeleteTagByClusterID(t *testing.T) {
	dbAccess := testhelper.GetClusterTagTestDbAccess()
	_, err := dbAccess.Create(sampleTag)
	assert.NoError(t, err)

	rows, err := dbAccess.DeleteByClusterID(2)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestGetTagByClusterID(t *testing.T) {
	dbAccess := testhelper.GetClusterTagTestDbAccess()
	_, err := dbAccess.Create(sampleTag)
	assert.NoError(t, err)

	result, err := dbAccess.FindByClusterID(1)
	assert.NoError(t, err)
	assert.Equal(t, 1, len(result))
	assert.Equal(t, sampleTag.CrdClusterID, result[0].CrdClusterID)
	assert.Equal(t, sampleTag.ClusterTag, result[0].ClusterTag)
}
