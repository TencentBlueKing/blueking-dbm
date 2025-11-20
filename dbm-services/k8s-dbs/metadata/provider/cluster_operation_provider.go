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
	metaentity "k8s-dbs/metadata/entity"
	models "k8s-dbs/metadata/model"

	"github.com/pkg/errors"

	"github.com/jinzhu/copier"
)

// ClusterOperationProvider 定义 cluster operation 业务逻辑层访问接口
type ClusterOperationProvider interface {
	CreateClusterOperation(entity *metaentity.ClusterOperationEntity) (*metaentity.ClusterOperationEntity, error)
	ListClusterOperations(pagination entity.Pagination) ([]*metaentity.ClusterOperationEntity, error)
}

// ClusterOperationProviderImpl ClusterOperationProvider 具体实现
type ClusterOperationProviderImpl struct {
	clusterOpDBAccess dbaccess.ClusterOperationDbAccess
	opDefDBAccess     dbaccess.OperationDefinitionDbAccess
}

// CreateClusterOperation 创建 cluster operation
func (o *ClusterOperationProviderImpl) CreateClusterOperation(entity *metaentity.ClusterOperationEntity) (
	*metaentity.ClusterOperationEntity, error,
) {
	model := models.ClusterOperationModel{}
	if err := copier.Copy(&model, entity); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	addedModel, err := o.clusterOpDBAccess.Create(&model)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to create cluster operation with entity: %+v", entity)
	}
	addedEntity := metaentity.ClusterOperationEntity{}
	if err = copier.Copy(&addedEntity, addedModel); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return &addedEntity, nil
}

// ListClusterOperations 获取 cluster operation 列表
func (o *ClusterOperationProviderImpl) ListClusterOperations(pagination entity.Pagination) (
	[]*metaentity.ClusterOperationEntity,
	error,
) {
	clusterOpModels, _, err := o.clusterOpDBAccess.ListByPage(pagination)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to list cluster operations with pagination: %+v", pagination)
	}

	var clusterOpEntities []*metaentity.ClusterOperationEntity
	if err = copier.Copy(&clusterOpEntities, clusterOpModels); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}

	for i, op := range clusterOpEntities {
		opDefModel, err := o.opDefDBAccess.FindByID(op.OperationID)
		if err != nil {
			return nil, errors.Wrapf(err, "failed to find operation with id %d", op.OperationID)
		}
		opDefEntity := metaentity.OperationDefinitionEntity{}
		if err := copier.Copy(&opDefEntity, opDefModel); err != nil {
			return nil, errors.Wrapf(err, "failed to copy")
		}
		clusterOpEntities[i].Operation = opDefEntity
	}
	return clusterOpEntities, nil
}

// NewClusterOperationProvider 创建 ClusterOperationProvider 接口实现实例
func NewClusterOperationProvider(
	clusterOpDBAccess dbaccess.ClusterOperationDbAccess,
	opDefDBAccess dbaccess.OperationDefinitionDbAccess,
) ClusterOperationProvider {
	return &ClusterOperationProviderImpl{clusterOpDBAccess, opDefDBAccess}
}
