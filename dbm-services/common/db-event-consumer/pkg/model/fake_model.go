// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package model

type FakeModelForNoStrictSchema struct {
	BaseModel
	tableName  string
	omitFields []string
}

// TableName Tabler
func (m *FakeModelForNoStrictSchema) TableName() string {
	return m.tableName
}

func (m *FakeModelForNoStrictSchema) SetTableName(tableName string) {
	m.tableName = tableName
}

func (m *FakeModelForNoStrictSchema) StrictSchema() bool {
	return false
}

func (m *FakeModelForNoStrictSchema) OmitFields() []string {
	return []string{"event_cluster_type", "event_type", "cluster_type", "event_uuid"}
}

func (m *FakeModelForNoStrictSchema) SetOmitFields(omitFields *[]string) {
	if omitFields == nil {
		// use default OmitFields()
		return
	}
	m.omitFields = *omitFields
}
