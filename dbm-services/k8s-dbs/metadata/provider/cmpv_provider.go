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
	models "k8s-dbs/metadata/dbaccess/model"
	entitys "k8s-dbs/metadata/provider/entity"
	"log/slog"

	"github.com/jinzhu/copier"
)

// K8sCrdCmpvProvider 定义 cmpv 业务逻辑层访问接口
type K8sCrdCmpvProvider interface {
	CreateCmpv(entity *entitys.K8sCrdComponentVersionEntity) (*entitys.K8sCrdComponentVersionEntity, error)
	DeleteCmpvID(id uint64) (uint64, error)
	FindCmpvByID(id uint64) (*entitys.K8sCrdComponentVersionEntity, error)
	UpdateCmpv(entity *entitys.K8sCrdComponentVersionEntity) (uint64, error)
}

// K8sCrdComponentVersionProviderImpl K8sCrdCmpvProvider 具体实现
type K8sCrdComponentVersionProviderImpl struct {
	dbAccess dbaccess.K8sCrdCmpvDbAccess
}

// CreateCmpv 创建 cmpv
func (k *K8sCrdComponentVersionProviderImpl) CreateCmpv(entity *entitys.K8sCrdComponentVersionEntity) (
	*entitys.K8sCrdComponentVersionEntity, error,
) {
	cmpvModel := models.K8sCrdComponentVersionModel{}
	err := copier.Copy(&cmpvModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addedCmpvModel, err := k.dbAccess.Create(&cmpvModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	}
	cmpvEntity := entitys.K8sCrdComponentVersionEntity{}
	if err := copier.Copy(&cmpvEntity, addedCmpvModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &cmpvEntity, nil

}

// DeleteCmpvID 删除 cmpv
func (k *K8sCrdComponentVersionProviderImpl) DeleteCmpvID(id uint64) (uint64, error) {
	return k.dbAccess.DeleteByID(id)
}

// FindCmpvByID 查找 cmpv
func (k *K8sCrdComponentVersionProviderImpl) FindCmpvByID(id uint64) (
	*entitys.K8sCrdComponentVersionEntity, error,
) {
	cmpvModel, err := k.dbAccess.FindByID(id)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	}
	cmpvEntity := entitys.K8sCrdComponentVersionEntity{}
	if err := copier.Copy(&cmpvEntity, cmpvModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &cmpvEntity, nil
}

// UpdateCmpv 更新 cmpv
func (k *K8sCrdComponentVersionProviderImpl) UpdateCmpv(entity *entitys.K8sCrdComponentVersionEntity) (
	uint64, error,
) {
	cmpvModel := models.K8sCrdComponentVersionModel{}
	err := copier.Copy(&cmpvModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&cmpvModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	}
	return rows, nil
}

// NewK8sCrdCmpvProvider 创建 K8sCrdCmpvProvider 接口实现实例
func NewK8sCrdCmpvProvider(
	dbAccess dbaccess.K8sCrdCmpvDbAccess) K8sCrdCmpvProvider {
	return &K8sCrdComponentVersionProviderImpl{dbAccess}
}
