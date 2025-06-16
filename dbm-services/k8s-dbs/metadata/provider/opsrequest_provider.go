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

// K8sCrdOpsRequestProvider 定义 ospRequest 业务逻辑层访问接口
type K8sCrdOpsRequestProvider interface {
	CreateOpsRequest(entity *entitys.K8sCrdOpsRequestEntity) (*entitys.K8sCrdOpsRequestEntity, error)
	DeleteOpsRequestByID(id uint64) (uint64, error)
	FindOpsRequestByID(id uint64) (*entitys.K8sCrdOpsRequestEntity, error)
	UpdateOpsRequest(entity *entitys.K8sCrdOpsRequestEntity) (uint64, error)
}

// K8sCrdOpsRequestProviderImpl K8sCrdOpsRequestDbAccess 具体实现
type K8sCrdOpsRequestProviderImpl struct {
	dbAccess dbaccess.K8sCrdOpsRequestDbAccess
}

// CreateOpsRequest 创建 opsRequest
func (k K8sCrdOpsRequestProviderImpl) CreateOpsRequest(entity *entitys.K8sCrdOpsRequestEntity) (
	*entitys.K8sCrdOpsRequestEntity, error,
) {
	k8sOpsRequestModel := models.K8sCrdOpsRequestModel{}
	err := copier.Copy(&k8sOpsRequestModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	opsModel, err := k.dbAccess.Create(&k8sOpsRequestModel)
	if err != nil {
		slog.Error("Failed to create entity", "error", err)
		return nil, err
	}
	opsEntity := entitys.K8sCrdOpsRequestEntity{}
	if err := copier.Copy(&opsEntity, opsModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &opsEntity, nil
}

// DeleteOpsRequestByID 删除 opsRequest
func (k K8sCrdOpsRequestProviderImpl) DeleteOpsRequestByID(id uint64) (uint64, error) {
	return k.dbAccess.DeleteByID(id)
}

// FindOpsRequestByID 查找 opsRequest
func (k K8sCrdOpsRequestProviderImpl) FindOpsRequestByID(id uint64) (*entitys.K8sCrdOpsRequestEntity, error) {
	opsModel, err := k.dbAccess.FindByID(id)
	if err != nil {
		slog.Error("Failed to delete entity", "error", err)
		return nil, err
	}
	opsEntity := entitys.K8sCrdOpsRequestEntity{}
	if err := copier.Copy(&opsEntity, opsModel); err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	return &opsEntity, nil
}

// UpdateOpsRequest 更新 opsRequest
func (k K8sCrdOpsRequestProviderImpl) UpdateOpsRequest(entity *entitys.K8sCrdOpsRequestEntity) (uint64, error) {
	opsRequestModel := models.K8sCrdOpsRequestModel{}
	err := copier.Copy(&opsRequestModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&opsRequestModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	}
	return rows, nil
}

// NewK8sCrdOpsRequestProvider 创建 K8sCrdOpsRequestDbAccess 接口实现实例
func NewK8sCrdOpsRequestProvider(dbAccess dbaccess.K8sCrdOpsRequestDbAccess) K8sCrdOpsRequestProvider {
	return &K8sCrdOpsRequestProviderImpl{dbAccess}
}
