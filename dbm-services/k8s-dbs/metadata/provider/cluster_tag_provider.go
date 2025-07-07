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
	commentity "k8s-dbs/common/entity"
	"k8s-dbs/metadata/dbaccess"
	models "k8s-dbs/metadata/dbaccess/model"
	entitys "k8s-dbs/metadata/provider/entity"

	"github.com/jinzhu/copier"
)

// K8sCrdClusterTagProvider 定义 cluster tag 业务逻辑层访问接口
type K8sCrdClusterTagProvider interface {
	Create(
		dbsContext *commentity.DbsContext,
		entity *entitys.K8sCrdClusterTagEntity,
	) (*entitys.K8sCrdClusterTagEntity, error)
	BatchCreate(dbsContext *commentity.DbsContext, inputEntities []*entitys.K8sCrdClusterTagEntity) (uint64, error)
	DeleteByClusterID(dbsContext *commentity.DbsContext, clusterID uint64) (uint64, error)
	FindByClusterID(dbsContext *commentity.DbsContext, clusterID uint64) ([]*entitys.K8sCrdClusterTagEntity, error)
}

// K8sCrdClusterTagProviderImpl K8sCrdClusterTagProvider 具体实现
type K8sCrdClusterTagProviderImpl struct {
	dbAccess dbaccess.K8sCrdClusterTagDbAccess
}

// BatchCreate 批次创建 tags
func (k K8sCrdClusterTagProviderImpl) BatchCreate(
	dbsContext *commentity.DbsContext,
	inputEntities []*entitys.K8sCrdClusterTagEntity,
) (uint64, error) {
	dbModels := make([]*models.K8sCrdClusterTagModel, 0, len(inputEntities))
	for _, inputEntity := range inputEntities {
		inputEntity.CreatedBy = dbsContext.BkAuth.BkUserName
		inputEntity.UpdatedBy = dbsContext.BkAuth.BkUserName
	}
	err := copier.Copy(&dbModels, &inputEntities)
	if err != nil {
		return 0, err
	}
	rows, err := k.dbAccess.BatchCreate(dbModels)
	if err != nil {
		return 0, err
	}
	return rows, nil
}

// Create 单次创建 tag
func (k K8sCrdClusterTagProviderImpl) Create(
	dbsContext *commentity.DbsContext,
	inputEntity *entitys.K8sCrdClusterTagEntity,
) (*entitys.K8sCrdClusterTagEntity, error) {
	dbModel := models.K8sCrdClusterTagModel{}
	inputEntity.CreatedBy = dbsContext.BkAuth.BkUserName
	inputEntity.UpdatedBy = dbsContext.BkAuth.BkUserName
	err := copier.Copy(&dbModel, inputEntity)
	if err != nil {
		return nil, err
	}

	createdDbModel, err := k.dbAccess.Create(&dbModel)
	if err != nil {
		return nil, err
	}
	outputEntity := entitys.K8sCrdClusterTagEntity{}
	if err := copier.Copy(&outputEntity, createdDbModel); err != nil {
		return nil, err
	}
	return &outputEntity, nil
}

// DeleteByClusterID 按照 clusterId 删除 tags
func (k K8sCrdClusterTagProviderImpl) DeleteByClusterID(_ *commentity.DbsContext, clusterID uint64) (uint64, error) {
	return k.dbAccess.DeleteByClusterID(clusterID)
}

// FindByClusterID 按照 clusterId 检索 tags
func (k K8sCrdClusterTagProviderImpl) FindByClusterID(_ *commentity.DbsContext, clusterID uint64) (
	[]*entitys.K8sCrdClusterTagEntity,
	error,
) {
	dbModels, err := k.dbAccess.FindByClusterID(clusterID)
	if err != nil {
		return nil, err
	}
	var outputEntities []*entitys.K8sCrdClusterTagEntity
	err = copier.Copy(&outputEntities, dbModels)
	if err != nil {
		return nil, err
	}
	return outputEntities, nil
}

// NewK8sCrdClusterTagProvider 创建 K8sCrdClusterTagProvider
func NewK8sCrdClusterTagProvider(dbAccess dbaccess.K8sCrdClusterTagDbAccess) K8sCrdClusterTagProvider {
	return &K8sCrdClusterTagProviderImpl{dbAccess: dbAccess}
}
