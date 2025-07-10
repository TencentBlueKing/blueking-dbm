// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package sinker

import (
	"github.com/pkg/errors"
)

var ModelSinkerRegistered = make(map[string]ModelSinker)

func RegisterModelSinker(modelObj ModelSinker) error {
	/*
		name := reflect.TypeOf(model).Name()
		if _, ok := modelSinker[name]; ok {
			return errors.Errorf("model sinker name [%s] is exist", name)
		}
	*/
	name := modelObj.TableName()
	if _, ok := ModelSinkerRegistered[name]; ok {
		return errors.Errorf("model sinker name [%s] is exist", name)
	}
	/*
		if _, ok := modelObj.(model.CustomCreator); ok {
			modelObj.(model.CustomCreator).CustomInit()
		}
	*/
	ModelSinkerRegistered[name] = modelObj
	return nil
}

var ModelWriterType = make(map[string]DSWriter)

func RegisterModelWriteType(typeObj DSWriter) error {
	name := typeObj.Type()
	if _, ok := ModelWriterType[name]; ok {
		return errors.Errorf("model writer name [%s] is exist", name)
	}
	ModelWriterType[name] = typeObj
	return nil
}
