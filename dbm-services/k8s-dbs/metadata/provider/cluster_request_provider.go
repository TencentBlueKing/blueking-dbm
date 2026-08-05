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
	metamodel "k8s-dbs/metadata/model"
	"sync"

	"github.com/pkg/errors"

	"github.com/jinzhu/copier"
)

// ClusterRequestRecordProvider 定义 request record 业务逻辑层访问接口
type ClusterRequestRecordProvider interface {
	CreateRequestRecord(entity *metaentity.ClusterRequestRecordEntity) (*metaentity.ClusterRequestRecordEntity, error)
	DeleteRequestRecordByID(id uint64) (uint64, error)
	DeleteRequestRecords(params *metaentity.ClusterRequestQueryParams) (uint64, error)
	FindRequestRecordByID(id uint64) (*metaentity.ClusterRequestRecordEntity, error)
	UpdateRequestRecord(entity *metaentity.ClusterRequestRecordEntity) (uint64, error)
	ListRecords(
		params *metaentity.ClusterRequestQueryParams,
		pagination *entity.Pagination,
	) ([]*metaentity.ClusterRequestRecordEntity, uint64, error)
	AssociateTicketRecord(ticketID uint64, params *metaentity.UpdateClusterRequestParams) error
}

// ClusterRequestRecordProviderImpl ClusterRequestRecordProvider 具体实现
type ClusterRequestRecordProviderImpl struct {
	dbAccess dbaccess.ClusterRequestRecordDbAccess
}

var (
	clusterRequestInstance ClusterRequestRecordProvider
	clusterRequestOnce     sync.Once
)

// GetClusterRequestRecordProvider 获取 ClusterRequestRecordProvider 单例实例
func GetClusterRequestRecordProvider(dbAccess dbaccess.ClusterRequestRecordDbAccess) ClusterRequestRecordProvider {
	clusterRequestOnce.Do(func() {
		clusterRequestInstance = &ClusterRequestRecordProviderImpl{dbAccess: dbAccess}
	})
	if clusterRequestInstance == nil {
		panic("ClusterRequestRecordProvider instance is nil after initialization")
	}
	return clusterRequestInstance
}

// ListRecords 查询 record 列表
func (k *ClusterRequestRecordProviderImpl) ListRecords(
	params *metaentity.ClusterRequestQueryParams,
	pagination *entity.Pagination,
) ([]*metaentity.ClusterRequestRecordEntity, uint64, error) {
	recordModels, count, err := k.dbAccess.ListByPage(params, pagination)
	if err != nil {
		return nil, 0, errors.Wrapf(err, "failed to list request record with params: %+v", params)
	}
	var recordEntities []*metaentity.ClusterRequestRecordEntity
	if err = copier.Copy(&recordEntities, recordModels); err != nil {
		return nil, 0, errors.Wrapf(err, "failed to copy")
	}
	return recordEntities, count, nil

}

// DeleteRequestRecords 按条件删除 request record
func (k *ClusterRequestRecordProviderImpl) DeleteRequestRecords(
	params *metaentity.ClusterRequestQueryParams,
) (uint64, error) {
	rows, err := k.dbAccess.DeleteByParams(params)
	if err != nil {
		return 0, errors.Wrapf(err, "failed to delete request record with params: %+v", params)
	}
	return rows, nil
}

// CreateRequestRecord 创建 request record
func (k *ClusterRequestRecordProviderImpl) CreateRequestRecord(entity *metaentity.ClusterRequestRecordEntity) (
	*metaentity.ClusterRequestRecordEntity,
	error,
) {
	newModel := metamodel.ClusterRequestRecordModel{}
	err := copier.Copy(&newModel, entity)
	if err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}

	addedModel, err := k.dbAccess.Create(&newModel)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to create request record with entity: %+v", entity)
	}

	addedEntity := metaentity.ClusterRequestRecordEntity{}
	if err = copier.Copy(&addedEntity, addedModel); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}

	return &addedEntity, nil
}

// DeleteRequestRecordByID 删除 addon
func (k *ClusterRequestRecordProviderImpl) DeleteRequestRecordByID(id uint64) (uint64, error) {
	return k.dbAccess.DeleteByID(id)
}

// FindRequestRecordByID 查找 cluster
func (k *ClusterRequestRecordProviderImpl) FindRequestRecordByID(id uint64) (
	*metaentity.ClusterRequestRecordEntity, error,
) {
	foundModel, err := k.dbAccess.FindByID(id)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find request record with id %d", id)
	}
	foundEntity := metaentity.ClusterRequestRecordEntity{}
	if err = copier.Copy(&foundEntity, foundModel); err != nil {
		return nil, errors.Wrap(err, "failed to copy")
	}
	return &foundEntity, nil
}

// UpdateRequestRecord 更新 cluster
func (k *ClusterRequestRecordProviderImpl) UpdateRequestRecord(entity *metaentity.ClusterRequestRecordEntity) (
	uint64, error,
) {
	newModel := metamodel.ClusterRequestRecordModel{}
	err := copier.Copy(&newModel, entity)
	if err != nil {
		return 0, errors.Wrap(err, "failed to copy")
	}
	rows, err := k.dbAccess.Update(&newModel)
	if err != nil {
		return 0, errors.Wrapf(err, "failed to update request record with entity: %+v", entity)
	}
	return rows, nil
}

// AssociateTicketRecord 关联 ticket 与 request record
func (k *ClusterRequestRecordProviderImpl) AssociateTicketRecord(
	ticketID uint64,
	params *metaentity.UpdateClusterRequestParams,
) error {
	// 1. 通过 ticket_id 查询数据（复用 ListByPage）
	listParams := &metaentity.ClusterRequestQueryParams{
		TicketID: &ticketID,
	}
	pagination := &entity.Pagination{Page: 1, Limit: 1}
	ticketRecords, _, err := k.dbAccess.ListByPage(listParams, pagination)
	if err != nil {
		return errors.Wrapf(err, "failed to list request record by ticket_id %d", ticketID)
	}

	// 2. 查询最新一条 ticket_id 为空的记录
	emptyTicketRecord, err := k.dbAccess.FindLatestEmptyTicketByCondition(params)
	if err != nil {
		return errors.Wrapf(err, "failed to find latest empty ticket record with params: %+v", params)
	}
	if emptyTicketRecord == nil {
		return nil
	}

	if len(ticketRecords) > 0 {
		// 3. ticket_id 对应记录存在：把空 ticket 记录的 request_params 赋值给 ticket 记录，更新并删除空 ticket 记录
		ticketRecord := ticketRecords[0]
		ticketRecord.RequestParams = emptyTicketRecord.RequestParams
		if _, err := k.dbAccess.Update(ticketRecord); err != nil {
			return errors.Wrapf(err, "failed to update request record with ticket_id %d", ticketID)
		}
		if _, err := k.dbAccess.DeleteByID(emptyTicketRecord.ID); err != nil {
			return errors.Wrapf(err, "failed to delete empty ticket record with id %d", emptyTicketRecord.ID)
		}
	} else {
		// 4. ticket_id 对应记录不存在：把 ticket_id 赋值给空 ticket 记录并更新
		emptyTicketRecord.TicketID = &ticketID
		if _, err := k.dbAccess.Update(emptyTicketRecord); err != nil {
			return errors.Wrapf(err, "failed to update empty ticket record with ticket_id %d", ticketID)
		}
	}
	return nil
}
