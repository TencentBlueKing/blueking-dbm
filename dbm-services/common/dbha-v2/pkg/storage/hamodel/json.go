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

package hamodel

import (
	"context"
	"database/sql/driver"
	"encoding/json"

	"dbm-services/common/dbha-v2/pkg/gerrors"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

// JSON wrapper
type JSON[T any] struct {
	Data  T
	Valid bool
}

// Scan Implement the SQL driver interface.
func (j *JSON[T]) Scan(value interface{}) error {
	if value == nil {
		return nil
	}

	var data []byte
	switch v := value.(type) {
	case []byte:
		data = v

	case string:
		data = []byte(v)

	default:
		return gerrors.Newf(gerrors.InvalidJson, "Invalid JSON value type: %T", v)
	}

	if err := json.Unmarshal(data, &j.Data); err != nil {
		return err
	}

	j.Valid = true
	return nil
}

func (j JSON[T]) Value() (driver.Value, error) {
	if !j.Valid {
		return nil, nil
	}

	return json.Marshal(j.Data)
}

// GormDataType Implement the GORM interface.
func (JSON[T]) GormDataType() string {
	return "json"
}

// GormValue Implement the GORM interface.
func (j JSON[T]) GormValue(ctx context.Context, db *gorm.DB) clause.Expr {
	if !j.Valid {
		return gorm.Expr("NULL")
	}
	data, _ := json.Marshal(j.Data)
	return gorm.Expr("?", string(data))
}
