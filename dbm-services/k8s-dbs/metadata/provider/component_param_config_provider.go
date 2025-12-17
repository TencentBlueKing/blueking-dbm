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
	metaentity "k8s-dbs/metadata/entity"

	"github.com/jinzhu/copier"
	"github.com/pkg/errors"
)

// AddonParamConfigProvider 定义组件参数配置业务逻辑层访问接口
type AddonParamConfigProvider interface {
	// FindByVersionAndComponent 根据版本和组件查询参数配置
	// 实现版本匹配规则：精确匹配 > 空（跳过验证）
	FindByVersionAndComponent(
		addonID uint64, serviceVersion, componentName string,
	) ([]*metaentity.AddonParamConfigEntity, error)

	// FindByParams 根据参数查询
	FindByParams(
		params *metaentity.AddonParamConfigQueryParams,
	) ([]*metaentity.AddonParamConfigEntity, error)
}

// AddonParamConfigProviderImpl AddonParamConfigProvider 具体实现
type AddonParamConfigProviderImpl struct {
	dbAccess dbaccess.AddonParamConfigDbAccess
}

// FindByVersionAndComponent 根据版本和组件查询参数配置
func (k *AddonParamConfigProviderImpl) FindByVersionAndComponent(
	addonID uint64, serviceVersion, componentName string,
) ([]*metaentity.AddonParamConfigEntity, error) {
	active := true
	params := &metaentity.AddonParamConfigQueryParams{
		AddonID:        addonID,
		ServiceVersion: serviceVersion,
		ComponentName:  componentName,
		Active:         &active,
	}
	return k.FindByParams(params)
}

// FindByParams 根据参数查询
func (k *AddonParamConfigProviderImpl) FindByParams(
	params *metaentity.AddonParamConfigQueryParams,
) ([]*metaentity.AddonParamConfigEntity, error) {
	models, err := k.dbAccess.FindByParams(params)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to find component param config with params %+v", params)
	}

	var entities []*metaentity.AddonParamConfigEntity
	if err = copier.Copy(&entities, models); err != nil {
		return nil, errors.Wrap(err, "failed to copy models to entities")
	}

	// 转换 ParamType 类型
	for i, model := range models {
		entities[i].ParamType = metaentity.ParamType(model.ParamType)
	}

	return entities, nil
}

// NewAddonParamConfigProvider 创建 AddonParamConfigProvider 接口实现实例
func NewAddonParamConfigProvider(
	dbAccess dbaccess.AddonParamConfigDbAccess,
) AddonParamConfigProvider {
	return &AddonParamConfigProviderImpl{dbAccess: dbAccess}
}
