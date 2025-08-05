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
	metaentity "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/model"
	testutil "k8s-dbs/metadata/util"
	"testing"

	"github.com/stretchr/testify/assert"
)

var sampleAddonTopology = &model.AddonTopologyModel{
	ID:            1,
	AddonName:     "test-addon",
	AddonCategory: "test-category",
	AddonType:     "test-type",
	AddonVersion:  "1.0.0",
	TopologyName:  "test-topology",
	TopologyAlias: "test-alias",
	Components:    "test-components",
	Relations:     "test-relations",
}

var batchSampleAddonTopologies = []*model.AddonTopologyModel{
	{
		ID:            1,
		AddonName:     "test-addon-1",
		AddonCategory: "test-category-1",
		AddonType:     "test-type-1",
		AddonVersion:  "1.0.0",
		TopologyName:  "test-topology-1",
		TopologyAlias: "test-alias-1",
		Components:    "test-components-1",
		Relations:     "test-relations-1",
	},
	{
		ID:            2,
		AddonName:     "test-addon-2",
		AddonCategory: "test-category-2",
		AddonType:     "test-type-2",
		AddonVersion:  "2.0.0",
		TopologyName:  "test-topology-2",
		TopologyAlias: "test-alias-2",
		Components:    "test-components-2",
		Relations:     "test-relations-2",
	},
}

var sampleAddonTopologyQueryParams = &metaentity.AddonTopologyQueryParams{
	AddonCategory: "test-category",
	AddonType:     "test-type",
	AddonVersion:  "1.0.0",
	TopologyName:  "test-topology",
}

func TestCreateAddonTopology(t *testing.T) {
	dbAccess := testutil.GetAddonTopologyTestDbAccess()
	added, err := dbAccess.Create(sampleAddonTopology)
	assert.NoError(t, err)
	assert.Equal(t, sampleAddonTopology.ID, added.ID)
	assert.Equal(t, sampleAddonTopology.AddonName, added.AddonName)
	assert.Equal(t, sampleAddonTopology.AddonCategory, added.AddonCategory)
	assert.Equal(t, sampleAddonTopology.AddonType, added.AddonType)
	assert.Equal(t, sampleAddonTopology.AddonVersion, added.AddonVersion)
	assert.Equal(t, sampleAddonTopology.TopologyName, added.TopologyName)
	assert.Equal(t, sampleAddonTopology.TopologyAlias, added.TopologyAlias)
	assert.Equal(t, sampleAddonTopology.Components, added.Components)
	assert.Equal(t, sampleAddonTopology.Relations, added.Relations)
}

func TestGetAddonTopologyByID(t *testing.T) {
	dbAccess := testutil.GetAddonTopologyTestDbAccess()
	_, err := dbAccess.Create(sampleAddonTopology)
	assert.NoError(t, err)

	result, err := dbAccess.FindByID(1)
	assert.NoError(t, err)
	assert.Equal(t, sampleAddonTopology.ID, result.ID)
	assert.Equal(t, sampleAddonTopology.AddonName, result.AddonName)
	assert.Equal(t, sampleAddonTopology.AddonCategory, result.AddonCategory)
	assert.Equal(t, sampleAddonTopology.AddonType, result.AddonType)
	assert.Equal(t, sampleAddonTopology.AddonVersion, result.AddonVersion)
	assert.Equal(t, sampleAddonTopology.TopologyName, result.TopologyName)
	assert.Equal(t, sampleAddonTopology.TopologyAlias, result.TopologyAlias)
	assert.Equal(t, sampleAddonTopology.Components, result.Components)
	assert.Equal(t, sampleAddonTopology.Relations, result.Relations)
}

func TestGetAddonTopologyByParams(t *testing.T) {
	dbAccess := testutil.GetAddonTopologyTestDbAccess()
	_, err := dbAccess.Create(sampleAddonTopology)
	assert.NoError(t, err)

	result, err := dbAccess.FindByParams(sampleAddonTopologyQueryParams)
	assert.NoError(t, err)
	assert.Len(t, result, 1)
	assert.Equal(t, sampleAddonTopology.ID, result[0].ID)
	assert.Equal(t, sampleAddonTopology.AddonName, result[0].AddonName)
	assert.Equal(t, sampleAddonTopology.AddonCategory, result[0].AddonCategory)
	assert.Equal(t, sampleAddonTopology.AddonType, result[0].AddonType)
	assert.Equal(t, sampleAddonTopology.AddonVersion, result[0].AddonVersion)
	assert.Equal(t, sampleAddonTopology.TopologyName, result[0].TopologyName)
	assert.Equal(t, sampleAddonTopology.TopologyAlias, result[0].TopologyAlias)
	assert.Equal(t, sampleAddonTopology.Components, result[0].Components)
	assert.Equal(t, sampleAddonTopology.Relations, result[0].Relations)
}

func TestListAddonTopologies(t *testing.T) {
	dbAccess := testutil.GetAddonTopologyTestDbAccess()
	for _, topology := range batchSampleAddonTopologies {
		_, err := dbAccess.Create(topology)
		assert.NoError(t, err)
	}

	result, err := dbAccess.ListByLimit(10)
	assert.NoError(t, err)
	assert.Equal(t, len(batchSampleAddonTopologies), len(result))

	topologyMap := make(map[uint64]*model.AddonTopologyModel)
	for _, t := range result {
		topologyMap[t.ID] = t
	}

	for _, sample := range batchSampleAddonTopologies {
		fetchedTopology, ok := topologyMap[sample.ID]
		assert.True(t, ok)
		assert.Equal(t, sample.AddonName, fetchedTopology.AddonName)
		assert.Equal(t, sample.AddonCategory, fetchedTopology.AddonCategory)
		assert.Equal(t, sample.AddonType, fetchedTopology.AddonType)
		assert.Equal(t, sample.AddonVersion, fetchedTopology.AddonVersion)
		assert.Equal(t, sample.TopologyName, fetchedTopology.TopologyName)
		assert.Equal(t, sample.TopologyAlias, fetchedTopology.TopologyAlias)
		assert.Equal(t, sample.Components, fetchedTopology.Components)
		assert.Equal(t, sample.Relations, fetchedTopology.Relations)
	}
}
