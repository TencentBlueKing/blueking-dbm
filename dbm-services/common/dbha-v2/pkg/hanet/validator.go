/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package hanet

import (
	"context"
	"fmt"
	"reflect"
	"strings"
	"sync"

	"github.com/gin-gonic/gin"
	validator "github.com/go-playground/validator/v10"
)

// validationRule validation rule
type validationRule struct {
	Tag    string
	Fn     validator.Func
	ErrMsg string
}

var (
	validate        *validator.Validate
	once            sync.Once
	errMsgs         = make(map[string]string)
	validationRules []validationRule
)

// getValidate get validate
func getValidate() *validator.Validate {
	once.Do(func() {
		validate = validator.New()
	})
	return validate
}

// AddValidation add validation
func AddValidation(tag string, fn validator.Func, errMsg string) {
	validationRules = append(validationRules, validationRule{
		Tag:    tag,
		Fn:     fn,
		ErrMsg: errMsg,
	})
}

// RegisterValidator register validator
func RegisterValidator() error {
	for _, rule := range validationRules {
		errMsgs[rule.Tag] = rule.ErrMsg
		if err := getValidate().RegisterValidation(rule.Tag, rule.Fn); err != nil {
			return err
		}
	}
	return nil
}

// BindAndValidate bind and validate
func BindAndValidate(c *gin.Context, obj any) error {
	if err := c.ShouldBindJSON(obj); err != nil {
		return err
	}
	return ValidateStruct(c.Request.Context(), obj)
}

// ValidateStruct validate struct
func ValidateStruct(ctx context.Context, s interface{}) error {
	v := reflect.ValueOf(s)
	if v.Kind() == reflect.Ptr {
		v = v.Elem()
	}

	if v.Kind() == reflect.Slice {
		return validateSlice(ctx, v, "")
	}

	return validateSingleStruct(ctx, s)
}

// validateSlice validate slice elements
func validateSlice(ctx context.Context, v reflect.Value, prefix string) error {
	var allErrors []string
	for i := 0; i < v.Len(); i++ {
		elem := v.Index(i)
		if elem.Kind() == reflect.Ptr {
			elem = elem.Elem()
		}
		if elem.Kind() == reflect.Struct {
			indexPrefix := fmt.Sprintf("%s[%d]", prefix, i)
			if err := validateStructWithPrefix(ctx, elem.Addr().Interface(), indexPrefix); err != nil {
				allErrors = append(allErrors, err.Error())
			}
		}
	}
	if len(allErrors) > 0 {
		return fmt.Errorf(strings.Join(allErrors, "; "))
	}
	return nil
}

// validateSingleStruct validate single struct
func validateSingleStruct(ctx context.Context, s interface{}) error {
	return validateStructWithPrefix(ctx, s, "")
}

// validateStructWithPrefix validate struct with field prefix
func validateStructWithPrefix(ctx context.Context, s interface{}, prefix string) error {
	err := getValidate().StructCtx(ctx, s)
	if err == nil {
		return validateNestedSlices(ctx, s, prefix)
	}

	validationErrs, ok := err.(validator.ValidationErrors)
	if !ok || len(validationErrs) == 0 {
		return err
	}

	var errList []string
	for _, fe := range validationErrs {
		field := fe.Field()
		tag := fe.Tag()
		fieldName := field
		if prefix != "" {
			fieldName = fmt.Sprintf("%s.%s", prefix, field)
		}
		if msg, exists := errMsgs[tag]; exists {
			errList = append(errList, fmt.Sprintf("%s: %s", fieldName, msg))
		} else {
			errList = append(errList, fmt.Sprintf("%s: %s", fieldName, fe.Error()))
		}
	}

	// continue checking nested slice fields
	if nestedErr := validateNestedSlices(ctx, s, prefix); nestedErr != nil {
		errList = append(errList, nestedErr.Error())
	}

	return fmt.Errorf(strings.Join(errList, "; "))
}

// validateNestedSlices validate nested slice fields in struct
func validateNestedSlices(ctx context.Context, s interface{}, prefix string) error {
	v := reflect.ValueOf(s)
	if v.Kind() == reflect.Ptr {
		v = v.Elem()
	}
	if v.Kind() != reflect.Struct {
		return nil
	}

	t := v.Type()
	var allErrors []string
	for i := 0; i < v.NumField(); i++ {
		field := v.Field(i)
		fieldType := t.Field(i)

		if !field.CanInterface() {
			continue
		}

		if field.Kind() == reflect.Slice {
			fieldName := fieldType.Name
			if prefix != "" {
				fieldName = fmt.Sprintf("%s.%s", prefix, fieldType.Name)
			}
			if err := validateSlice(ctx, field, fieldName); err != nil {
				allErrors = append(allErrors, err.Error())
			}
		}
	}

	if len(allErrors) > 0 {
		return fmt.Errorf(strings.Join(allErrors, "; "))
	}
	return nil
}
