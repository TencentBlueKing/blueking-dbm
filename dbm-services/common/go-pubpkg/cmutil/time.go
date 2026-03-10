// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package cmutil

import (
	"strings"
	"time"

	"github.com/pkg/errors"
)

// TimeToSecondPrecision keep only second precision for time
func TimeToSecondPrecision(t time.Time) time.Time {
	timeStr := t.Local().Format(time.RFC3339)
	tt, _ := time.ParseInLocation(time.RFC3339, timeStr, time.Local)
	return tt
}

// ParseLocalTimeString 将 time.Datetime or time.RFC3339 格式转换传本地时区 time.Time 类型
func ParseLocalTimeString(s string) (time.Time, error) {
	t, err := time.ParseInLocation(time.DateTime, s, time.Local)
	if err != nil {
		if t, err = time.ParseInLocation(time.RFC3339, s, time.Local); err != nil {
			return time.Time{},
				errors.Errorf("expect time format '%s' or '%s' but got '%s'", time.DateTime, time.RFC3339, s)
		}
	}
	return t, nil
}

func NewTimestampString() string {
	return time.Now().Format("20060102150405")
}

type Datetime struct {
	time.Time
}

func (t *Datetime) UnmarshalJSON(b []byte) (err error) {
	s := strings.Trim(string(b), `"`)
	if strings.EqualFold(s, "null") {
		return nil
	}

	t.Time, err = time.ParseInLocation(time.DateTime, s, time.Local)
	if err != nil {
		t.Time, err = time.ParseInLocation(time.RFC3339, s, time.Local)
	}
	return err
}

func (t *Datetime) MarshalJSON() ([]byte, error) {
	return []byte(`"` + t.Time.Format(time.DateTime) + `"`), nil
}

type UtcDatetime struct {
	time.Time
}

func (t *UtcDatetime) UnmarshalJSON(b []byte) (err error) {
	s := strings.Trim(string(b), `"`)
	if strings.EqualFold(s, "null") {
		return nil
	}

	t.Time, err = time.ParseInLocation(time.DateTime, s, time.UTC)
	if err != nil {
		t.Time, err = time.ParseInLocation(time.RFC3339, s, time.UTC)
	}
	return err
}

func (t *UtcDatetime) MarshalJSON() ([]byte, error) {
	return []byte(`"` + t.Time.UTC().Format(time.DateTime) + `"`), nil
}
