/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package validate TODO
package validate

import (
	"fmt"
	"reflect"
	"strings"
	"time"

	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/locales/en"
	ut "github.com/go-playground/universal-translator"
	"github.com/go-playground/validator/v10"
	en_translations "github.com/go-playground/validator/v10/translations/en"
	"github.com/pkg/errors"
)

// ValidateEnums TODO
// make validate tag work with enums tag
// 避免 validate oneof 和 swagger enums 写 2 份重复的校验和文档
// example: Method string `validate:"required,enums" enums:"post,get" json:"method"`
func ValidateEnums(f validator.FieldLevel) bool {
	fieldValue := f.Field().String()
	fieldName := f.StructFieldName()
	// get StructField
	sf, _ := f.Parent().Type().FieldByName(fieldName)
	// get tag value from tag_field enums
	tagValue := sf.Tag.Get(TagEnum)
	enumsValues := strings.Split(tagValue, ",")
	if util.StringsHas(enumsValues, fieldValue) {
		return true
	} else {
		return false
	}
}

// GoValidateStructSimple TODO
// 简单校验 struct，不涉及逻辑
// 如果 struct 上有 tag validate:"enums"，必须启用enum=true校验
func GoValidateStructSimple(v interface{}, enum bool) error {
	validate := validator.New()
	if enum {
		_ = validate.RegisterValidation("enums", ValidateEnums)
	}
	if err := validate.Struct(v); err != nil {
		return err
	}
	return nil
}

// TagEnum TODO
const TagEnum = "enums"

// GoValidateStruct v 不能是Ptr
func GoValidateStruct(v interface{}, enum bool, charset bool) error {
	validate := validator.New()
	uni := ut.New(en.New())
	trans, _ := uni.GetTranslator("en")
	// 提示时显示 json 字段的名字
	validate.RegisterTagNameFunc(func(fld reflect.StructField) string {
		// name := fld.Tag.Get("json")
		name := strings.SplitN(fld.Tag.Get("json"), ",", 2)[0]
		if name == "-" {
			return ""
		}
		return name
	})
	if err := en_translations.RegisterDefaultTranslations(validate, trans); err != nil {
		return err
	}

	if enum {
		_ = validate.RegisterValidation(TagEnum, ValidateEnums)
	}
	if charset {
		_ = validate.RegisterValidation("checkCharset", validCharSet)
	}
	_ = validate.RegisterValidation("time", validateTimeStr)
	if err := validate.Struct(v); err != nil {
		return translateErr2Msg(v, trans, err)
	}
	return nil
}

// translateErr2Msg v 不能是Ptr
func translateErr2Msg(v interface{}, trans ut.Translator, err error) error {
	var errStr []string
	_, ok := err.(*validator.InvalidValidationError)
	if ok {
		return fmt.Errorf("param error:%s", err.Error())
	}
	for _, vErr := range err.(validator.ValidationErrors) {
		if vErr.Tag() == TagEnum {
			errmsg := ""
			// errmsg := customEnumTransFunc(vErr, v)
			if vErr.Param() == "" {
				sf, _ := reflect.TypeOf(v).FieldByName(vErr.StructField())
				tagValue := sf.Tag.Get(TagEnum)
				errmsg = fmt.Sprintf("%s must be one of [%s]", vErr.Field(), tagValue)
			} else {
				errmsg = vErr.Param()
			}
			errStr = append(errStr, errmsg)
			continue
		}
		errStr = append(errStr, vErr.Translate(trans))
	}
	return errors.New(strings.Join(errStr, " || "))
}

func validCharSet(f validator.FieldLevel) bool {
	v := f.Field().String()
	return util.HasElem(v, []string{"default", "utf8mb4", "utf8", "latin1", "gb2312", "gbk", "binary", "gb18030"})
}

// validateTimeStr TODO
// 验证时间字符串 "09:00:00" 这种
func validateTimeStr(f validator.FieldLevel) bool {
	v := f.Field().String()
	if strings.TrimSpace(v) == "" {
		return true
	}
	_, err := time.Parse("15:04:05", v)
	return err == nil
}
