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

package util

import (
	"fmt"
	commconst "k8s-dbs/common/constant"
	commentity "k8s-dbs/common/entity"
	"k8s-dbs/core/entity"
	"k8s-dbs/errors"
	"reflect"
	"strconv"

	"github.com/mitchellh/mapstructure"

	"github.com/gin-gonic/gin"
)

// BuildPagination 构建 Pagination
func BuildPagination(ctx *gin.Context) (*commentity.Pagination, error) {
	page, err := strconv.Atoi(ctx.DefaultQuery(commconst.ParamsPage, commconst.DefaultPageStr))
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return nil, err
	}
	limit, err := strconv.Atoi(ctx.DefaultQuery(commconst.ParamsLimit, commconst.DefaultFetchSizeStr))
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return nil, err
	}
	limit = min(limit, commconst.MaxFetchSize)
	pagination := commentity.Pagination{Page: page, Limit: limit}
	return &pagination, nil
}

// BuildPageParams 构建 Page Params
func BuildPageParams(ctx *gin.Context) map[string]interface{} {
	params := make(map[string]interface{})
	for key, values := range ctx.Request.URL.Query() {
		if key != commconst.ParamsPage && key != commconst.ParamsLimit {
			if len(values) > 0 {
				params[key] = values[0]
			}
		}
	}
	return params
}

// BuildParams 构建 Params
func BuildParams(ctx *gin.Context) map[string]interface{} {
	params := make(map[string]interface{})
	for key, values := range ctx.Request.URL.Query() {
		if len(values) > 0 {
			params[key] = values[0]
		}
	}
	return params
}

// DecodeParams 从 gin.Context 中解析 JSON 请求体，并映射到目标结构体
func DecodeParams(ctx *gin.Context,
	paramExtractFunc func(*gin.Context) map[string]interface{},
	result interface{},
	targetFiledMap map[string]reflect.Type,
) error {
	paramMap := paramExtractFunc(ctx)
	if targetFiledMap != nil {
		for key, value := range paramMap {
			if targetType, ok := targetFiledMap[key]; ok {
				convertedValue, err := convertValue(value, targetType)
				if err != nil {
					return fmt.Errorf("字段 %s 转换失败 %v", key, err)
				}
				paramMap[key] = convertedValue
			}
		}
	}
	decoder, err := mapstructure.NewDecoder(&mapstructure.DecoderConfig{
		Result:  result,
		TagName: "json",
	})
	if err != nil {
		return err
	}
	if err := decoder.Decode(paramMap); err != nil {
		return err
	}
	return nil
}

// convertValue 根据目标类型尝试转换值
func convertValue(val interface{}, targetType reflect.Type) (interface{}, error) {
	valStr, ok := val.(string)
	if !ok {
		return val, nil
	}

	switch targetType.Kind() {
	case reflect.Uint64:
		uintVal, err := strconv.ParseUint(valStr, 10, 64)
		if err != nil {
			return nil, err
		}
		return uintVal, nil
	case reflect.Int64:
		intVal, err := strconv.ParseInt(valStr, 10, 64)
		if err != nil {
			return nil, err
		}
		return intVal, nil
	case reflect.Float64:
		floatVal, err := strconv.ParseFloat(valStr, 64)
		if err != nil {
			return nil, err
		}
		return floatVal, nil

	case reflect.Uint32:
		uintVal, err := strconv.ParseUint(valStr, 10, 32)
		if err != nil {
			return nil, err
		}
		return uintVal, nil
	case reflect.Int32:
		intVal, err := strconv.ParseInt(valStr, 10, 32)
		if err != nil {
			return nil, err
		}
		return intVal, nil
	case reflect.Float32:
		floatVal, err := strconv.ParseFloat(valStr, 32)
		if err != nil {
			return nil, err
		}
		return floatVal, nil
	case reflect.String:
		return valStr, nil
	default:
		return nil, fmt.Errorf("不支持的类型转换: %v", targetType)
	}
}
