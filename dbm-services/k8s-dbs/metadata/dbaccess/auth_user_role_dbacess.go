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

package dbaccess

import (
	mconst "k8s-dbs/common/constant"
	entitys "k8s-dbs/metadata/entity"
	models "k8s-dbs/metadata/model"
	"sync"

	"github.com/pkg/errors"
	"gorm.io/gorm"
)

// AuthUserRoleDbAccess 定义 auth user role 元数据的数据库访问接口
type AuthUserRoleDbAccess interface {
	FindByParams(params entitys.AuthUserRoleQueryParams) ([]*models.AuthUserRoleModel, error)
}

// AuthUserRoleDbAccessImpl AuthUserRoleDbAccess 的具体实现
type AuthUserRoleDbAccessImpl struct {
	db *gorm.DB
}

var (
	authUserRoleInstance AuthUserRoleDbAccess
	authUserRoleOnce     sync.Once
)

// GetAuthUserRoleDbAccess 获取 AuthUserRoleDbAccess 单例实例
func GetAuthUserRoleDbAccess(db *gorm.DB) AuthUserRoleDbAccess {
	authUserRoleOnce.Do(func() {
		authUserRoleInstance = &AuthUserRoleDbAccessImpl{db: db}
	})
	if authUserRoleInstance == nil {
		panic("AuthUserRoleDbAccess instance is nil after initialization")
	}
	return authUserRoleInstance
}

// FindByParams 参数查询实现
func (k *AuthUserRoleDbAccessImpl) FindByParams(
	params entitys.AuthUserRoleQueryParams,
) ([]*models.AuthUserRoleModel, error) {
	var authModels []*models.AuthUserRoleModel
	if err := k.db.
		Where(params).
		Limit(mconst.MaxFetchSize).
		Find(&authModels).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, errors.Wrapf(err, "failed to find auth user role with params %+v", params)
	}
	return authModels, nil
}
