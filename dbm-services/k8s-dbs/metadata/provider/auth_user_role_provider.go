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
	entitys "k8s-dbs/metadata/entity"
)

// AuthUserRoleProvider 定义 auth user role 业务逻辑层访问接口
type AuthUserRoleProvider interface {
	CheckUserRole(params entitys.AuthUserRoleQueryParams) bool
}

// AuthUserRoleProviderImpl AuthUserRoleProvider 具体实现
type AuthUserRoleProviderImpl struct {
	dbAccess dbaccess.AuthUserRoleDbAccess
}

// CheckUserRole 按照参数进行查询
func (k *AuthUserRoleProviderImpl) CheckUserRole(
	params entitys.AuthUserRoleQueryParams,
) bool {
	authModels, _ := k.dbAccess.FindByParams(params)
	if len(authModels) == 0 || authModels == nil {
		return false
	}
	return true
}

// NewAuthUserRoleProvider 创建 AuthUserRoleProvider 实例
func NewAuthUserRoleProvider(dbAccess dbaccess.AuthUserRoleDbAccess) AuthUserRoleProvider {
	return &AuthUserRoleProviderImpl{
		dbAccess: dbAccess,
	}
}
