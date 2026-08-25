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

package mysql

import (
	"reflect"
	"strings"

	"dbm-services/common/dbha-v2/pkg/converter"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// globalStatus mysql global status
type globalStatus struct {
	Variable string `gorm:"column:Variable_name"`
	Value    string `gorm:"column:Value"`
}

// convertToMySqlStatus convert the global status to status
func convertToMySqlStatus(status []globalStatus) *haprobe.MySqlGlobalStatus {
	statusMaps := map[string]string{}
	for _, s := range status {
		statusMaps[strings.ToLower(s.Variable)] = s.Value
	}

	dbStatus := haprobe.MySqlGlobalStatus{}
	t := reflect.TypeOf(dbStatus)
	v := reflect.ValueOf(&dbStatus).Elem()

	for i := 0; i < t.NumField(); i++ {
		field := t.Field(i)

		jTag := field.Tag.Get("json")
		if jTag == "" {
			logger.Debug("the field: %s has no tag", field.Name)
			continue
		}

		jTagName := strings.Split(jTag, ",")[0]

		statusValue, exists := statusMaps[strings.ToLower(jTagName)]
		if !exists {
			logger.Debug("missed the key: %s in the global status", jTagName)
			continue
		}

		fieldValue := v.Field(i)
		if !fieldValue.CanSet() {
			logger.Debug("can not set the key: %s", jTagName)
			continue
		}

		switch field.Type.Kind() {
		case reflect.String:
			fieldValue.SetString(statusValue)

		case reflect.Int, reflect.Int64:
			sVal, err := converter.ToInt64(statusValue)
			if err != nil {
				logger.Warn("can not convert the value: %s to int64, errmsg: %s", statusValue, err)
				continue
			}

			fieldValue.SetInt(sVal)

		case reflect.Uint, reflect.Uint64:
			sVal, err := converter.ToUint64(statusValue)
			if err != nil {
				logger.Warn("can not convert the value: %s to uint64, errmsg: %s", statusValue, err)
				continue
			}

			fieldValue.SetUint(sVal)

		case reflect.Float32, reflect.Float64:
			sVal, err := converter.ToFloat64(statusValue)
			if err != nil {
				logger.Warn("can not convert the value: %s to uint64, errmsg: %s", statusValue, err)
				continue
			}

			fieldValue.SetFloat(sVal)
		default:
			logger.Warn("unsurpported the type: %s, field: %s", field.Type.Kind(), field.Name)
		}
	}

	return &dbStatus
}
