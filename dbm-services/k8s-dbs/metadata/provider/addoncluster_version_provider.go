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
	"k8s-dbs/common/entity"
	"k8s-dbs/metadata/dbaccess"
	models "k8s-dbs/metadata/dbaccess/model"
	entitys "k8s-dbs/metadata/provider/entity"
	"log/slog"

	"github.com/jinzhu/copier"
)

// AddonClusterVersionProvider 定义 addon 业务逻辑层访问接口
type AddonClusterVersionProvider interface {
	CreateAcVersion(entity *entitys.AddonClusterVersionEntity) (*entitys.AddonClusterVersionEntity, error)
	DeleteAcVersionByID(id uint64) (uint64, error)
	FindAcVersionByID(id uint64) (*entitys.AddonClusterVersionEntity, error)
	FindAcVersionByParams(params map[string]interface{}) ([]*entitys.AddonClusterVersionEntity, error)
	UpdateAcVersion(entity *entitys.AddonClusterVersionEntity) (uint64, error)
	ListAcVersion(pagination entity.Pagination) ([]*entitys.AddonClusterVersionEntity, error)
}

// AddonClusterVersionProviderImpl AddonClusterVersionProvider 具体实现
type AddonClusterVersionProviderImpl struct {
	dbAccess dbaccess.AddonClusterVersionDbAccess
}

// FindAcVersionByParams 按照参数进行查询
func (k *AddonClusterVersionProviderImpl) FindAcVersionByParams(
	params map[string]interface{},
) ([]*entitys.AddonClusterVersionEntity, error) {
	saModels, err := k.dbAccess.FindByParams(params)
	if err != nil {
		slog.Error("failed to find storage addon by params.", "params", params, "err", err)
		return nil, err
	}
	var saEntities []*entitys.AddonClusterVersionEntity
	if err := copier.Copy(&saEntities, saModels); err != nil {
		slog.Error("failed to copy models", "error", err)
		return nil, err
	}
	return saEntities, nil
}

// CreateAcVersion 创建
func (k *AddonClusterVersionProviderImpl) CreateAcVersion(entity *entitys.AddonClusterVersionEntity) (
	*entitys.AddonClusterVersionEntity, error,
) {
	acVersionModel := models.AddonClusterVersionModel{}
	err := copier.Copy(&acVersionModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addedAcVersionModel, err := k.dbAccess.Create(&acVersionModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	}
	addedAcVersionEntity := entitys.AddonClusterVersionEntity{}
	if err := copier.Copy(&addedAcVersionEntity, addedAcVersionModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &addedAcVersionEntity, nil
}

// DeleteAcVersionByID 删除
func (k *AddonClusterVersionProviderImpl) DeleteAcVersionByID(id uint64) (uint64, error) {
	return k.dbAccess.DeleteByID(id)
}

// FindAcVersionByID 按照 ID 进行查询
func (k *AddonClusterVersionProviderImpl) FindAcVersionByID(id uint64) (*entitys.AddonClusterVersionEntity, error) {
	acVersionModel, err := k.dbAccess.FindByID(id)
	if err != nil {
		slog.Error("Failed to find entity")
		return nil, err
	}
	acVersionEntity := entitys.AddonClusterVersionEntity{}
	if err := copier.Copy(&acVersionEntity, acVersionModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &acVersionEntity, nil
}

// UpdateAcVersion 更新 addon cluster version
func (k *AddonClusterVersionProviderImpl) UpdateAcVersion(entity *entitys.AddonClusterVersionEntity) (uint64, error) {
	adVersionModel := models.AddonClusterVersionModel{}
	err := copier.Copy(&adVersionModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&adVersionModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	}
	return rows, nil
}

// ListAcVersion 获取 addon cluster version 列表
func (k *AddonClusterVersionProviderImpl) ListAcVersion(pagination entity.Pagination) (
	[]*entitys.AddonClusterVersionEntity,
	error,
) {
	acVersionModels, _, err := k.dbAccess.ListByPage(pagination)
	if err != nil {
		slog.Error("Failed to find entity")
		return nil, err
	}
	var acVersionEntities []*entitys.AddonClusterVersionEntity
	if err := copier.Copy(&acVersionEntities, acVersionModels); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return acVersionEntities, nil
}

// NewAddonClusterVersionProvider 创建 AddonClusterVersionDbAccess 接口实现实例
func NewAddonClusterVersionProvider(dbAccess dbaccess.AddonClusterVersionDbAccess) AddonClusterVersionProvider {
	return &AddonClusterVersionProviderImpl{dbAccess: dbAccess}
}
