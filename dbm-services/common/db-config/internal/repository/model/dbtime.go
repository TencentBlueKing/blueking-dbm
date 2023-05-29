package model

import (
	"database/sql/driver"
	"fmt"
	"time"
)

// DBTime TODO
type DBTime struct {
	time.Time
}

// DBTimeFormat TODO
const DBTimeFormat = "2006-01-02 15:04:05"

// MarshalJSON TODO
func (t DBTime) MarshalJSON() ([]byte, error) {
	str := fmt.Sprintf(`"%s"`, t.Format(DBTimeFormat))
	return []byte(str), nil
}

// Value TODO
func (t DBTime) Value() (driver.Value, error) {
	var zeroTime time.Time
	if t.Time.UnixNano() == zeroTime.UnixNano() {
		return nil, nil
	}
	return t.Time, nil
}

// Scan TODO
func (t *DBTime) Scan(v interface{}) error {
	if val, ok := v.(time.Time); ok {
		*t = DBTime{Time: val}
		return nil
	}
	return fmt.Errorf("error when converting %v to datetime", v)
}

// String 用于打印
func (t DBTime) String() string {
	// 以当前机器时区
	return t.Format(DBTimeFormat)
}

// BaseDatetime TODO
type BaseDatetime struct {
	// gorm.Model
	CreatedAt DBTime `json:"created_at" gorm:"->;column:created_at;type:varchar(30)"`
	UpdatedAt DBTime `json:"updated_at" gorm:"->;column:updated_at;type:varchar(30)"`
}
