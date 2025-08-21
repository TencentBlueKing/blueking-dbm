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

package provider

import (
	"k8s-dbs/metadata/dbaccess"
	metaenitty "k8s-dbs/metadata/entity"
	models "k8s-dbs/metadata/model"
	"log/slog"

	"github.com/jinzhu/copier"
)

// AddonTopologyProvider 定义 operation definition 业务逻辑层访问接口
type AddonTopologyProvider interface {
	Create(entity *metaenitty.AddonTopologyEntity) (*metaenitty.AddonTopologyEntity, error)
	FindByID(id uint64) (*metaenitty.AddonTopologyEntity, error)
	FindByParams(params *metaenitty.AddonTopologyQueryParams) ([]*metaenitty.AddonTopologyEntity, error)
}

// AddonTopologyProviderImpl AddonTopologyProvider 具体实现
type AddonTopologyProviderImpl struct {
	dbAccess dbaccess.AddonTopologyDbAccess
}

// FindByParams 按照 参数查找接口实现
func (a *AddonTopologyProviderImpl) FindByParams(params *metaenitty.AddonTopologyQueryParams) (
	[]*metaenitty.AddonTopologyEntity,
	error,
) {
	topoModels, err := a.dbAccess.FindByParams(params)
	if err != nil {
		return nil, err
	}
	var topoEntities []*metaenitty.AddonTopologyEntity
	if err := copier.Copy(&topoEntities, topoModels); err != nil {
		return nil, err
	}
	return topoEntities, nil
}

// FindByID 按照 ID 查找接口实现
func (a *AddonTopologyProviderImpl) FindByID(id uint64) (*metaenitty.AddonTopologyEntity, error) {
	model, err := a.dbAccess.FindByID(id)
	if err != nil {
		slog.Error("Failed to find entity")
		return nil, err
	}
	topoEntity := &metaenitty.AddonTopologyEntity{}
	if err := copier.Copy(topoEntity, model); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return topoEntity, nil
}

// Create 创建 addon topology
func (a *AddonTopologyProviderImpl) Create(entity *metaenitty.AddonTopologyEntity) (
	*metaenitty.AddonTopologyEntity, error,
) {
	model := models.AddonTopologyModel{}
	err := copier.Copy(&model, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addedModel, err := a.dbAccess.Create(&model)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	}
	addedEntity := metaenitty.AddonTopologyEntity{}
	if err := copier.Copy(&addedEntity, addedModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &addedEntity, nil
}

// NewAddonTopologyProvider 创建 AddonTopologyProvider 接口实现实例
func NewAddonTopologyProvider(
	dbAccess dbaccess.AddonTopologyDbAccess,
) AddonTopologyProvider {
	return &AddonTopologyProviderImpl{dbAccess}
}
