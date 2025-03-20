// Package validate TODO
package validate

import (
	"fmt"
	"log"
	"reflect"
	"strings"

	"github.com/go-playground/locales/en"
	ut "github.com/go-playground/universal-translator"
	"github.com/go-playground/validator/v10"
	en_translations "github.com/go-playground/validator/v10/translations/en"
	"github.com/pkg/errors"
)

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

// GoValidateStruct v 不能是Ptr
func GoValidateStruct(v interface{}, enum bool) error {
	return GoValidateTransError(v, "json", enum, false)
}

func GoValidateStructCharset(v interface{}, enum bool, checkCharset bool) error {
	return GoValidateTransError(v, "json", enum, checkCharset)
}

// GoValidateStructTag v 不能是Ptr
func GoValidateStructTag(v interface{}, tagName string) error {
	return GoValidateTransError(v, tagName, true, false)
}

// GoValidateTransError v 不能是Ptr
func GoValidateTransError(v interface{}, tagKey string, enum bool, charset bool) error {
	if tagKey == "" {
		tagKey = "json"
	}
	validate := validator.New()
	uni := ut.New(en.New())
	trans, _ := uni.GetTranslator("en")
	// 提示时显示 json 字段的名字
	validate.RegisterTagNameFunc(func(fld reflect.StructField) string {
		// name := fld.Tag.Get("json")
		name := strings.SplitN(fld.Tag.Get(tagKey), ",", 2)[0]
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
		} else if vErr.Tag() == "dir" {
			errmsg := fmt.Sprintf("dir %s=%s may not exist", vErr.Field(), vErr.Value())
			errStr = append(errStr, errmsg)
		} else {
			errStr = append(errStr, vErr.Translate(trans))
		}
	}
	return errors.New(strings.Join(errStr, " || "))
}
func customEnumTransFunc(fe validator.FieldError, v interface{}) string {
	if fe.Param() == "" {
		sf, _ := reflect.TypeOf(v).FieldByName(fe.StructField())
		tagValue := sf.Tag.Get(TagEnum)
		errmsg := fmt.Sprintf("%s must be one of [%s]", fe.Field(), tagValue)
		return errmsg
	} else {
		return fe.Param()
	}
}

// registerTranslator 为自定义字段添加翻译功能
func registerTranslator(tag string, msg string) validator.RegisterTranslationsFunc {
	return func(trans ut.Translator) error {
		if err := trans.Add(tag, msg, false); err != nil {
			return err
		}
		return nil
	}
}

// customTransFunc TODO
// translate 自定义字段的翻译方法
func customTransFunc(trans ut.Translator, fe validator.FieldError) string {
	msg, err := trans.T(fe.Tag(), fe.Field())
	if err != nil {
		panic(fe.(error).Error())
	}
	return msg
}

func translate(ut ut.Translator, fe validator.FieldError) string {
	s, err := ut.T(fe.Tag(), fe.Field(), "fe.Param()")
	if err != nil {
		log.Printf("warning: error translating FieldError: %#v", fe)
		return fe.(error).Error()
	}
	return s
}
