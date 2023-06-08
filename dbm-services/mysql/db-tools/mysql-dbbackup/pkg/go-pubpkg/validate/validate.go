// Package validate TODO
package validate

import (
	"fmt"
	"reflect"
	"strings"

	"github.com/go-playground/locales/en"
	ut "github.com/go-playground/universal-translator"
	"github.com/go-playground/validator/v10"
	en_translations "github.com/go-playground/validator/v10/translations/en"
	"github.com/pkg/errors"
)

// GoValidateStruct v 不能是Ptr
func GoValidateStruct(v interface{}) error {
	validate := validator.New()
	uni := ut.New(en.New())
	trans, _ := uni.GetTranslator("en")
	// 提示时显示 json 字段的名字
	validate.RegisterTagNameFunc(func(fld reflect.StructField) string {
		name := strings.SplitN(fld.Tag.Get("ini"), ",", 2)[0]
		if name == "-" {
			return ""
		}
		return name
	})
	if err := en_translations.RegisterDefaultTranslations(validate, trans); err != nil {
		return err
	}

	if err := validate.Struct(v); err != nil {
		return translateErr2Msg(v, trans, err)
	}
	return nil
}

// translateErr2Msg v 不能是Ptr
func translateErr2Msg(v interface{}, trans ut.Translator, err error) error {
	var errStr []string
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
	return errors.New(strings.Join(errStr, "\n") + "\n")
}

// TagEnum TODO
const TagEnum = "enums"
