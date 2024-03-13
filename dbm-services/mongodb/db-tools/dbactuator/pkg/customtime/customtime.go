// Package customtime 自定义time
package customtime

import (
	"database/sql/driver"
	"fmt"
	"strings"
	"time"
)

// CustomTime 自定义时间类型
type CustomTime struct {
	time.Time
}

const ctLayout = "2006-01-02 15:04:05"

var nilTime = (time.Time{}).UnixNano()

// UnmarshalJSON ..
func (ct *CustomTime) UnmarshalJSON(b []byte) (err error) {
	s := strings.Trim(string(b), "\"")
	if s == "null" || s == "" {
		ct.Time = time.Time{}
		return
	}
	ct.Time, err = time.ParseInLocation(ctLayout, s, time.Local)
	return
}

// MarshalJSON ..
func (ct CustomTime) MarshalJSON() ([]byte, error) {
	if ct.Time.UnixNano() == nilTime {
		return []byte("null"), nil
	}
	return []byte(fmt.Sprintf("\"%s\"", ct.Time.Format(ctLayout))), nil
}

// Scan scan
func (ct *CustomTime) Scan(value interface{}) error {
	switch v := value.(type) {
	case []byte:
		return ct.UnmarshalText(string(v))
	case string:
		return ct.UnmarshalText(v)
	case time.Time:
		ct.Time = v
	case nil:
		ct.Time = time.Time{}
	default:
		return fmt.Errorf("cannot sql.Scan() CustomTime from: %#v", v)
	}
	return nil
}

// UnmarshalText unmarshal ...
func (ct *CustomTime) UnmarshalText(value string) error {
	dd, err := time.ParseInLocation(ctLayout, value, time.Local)
	if err != nil {
		return err
	}
	ct.Time = dd
	return nil
}

// Value ..
// 注意这里ct不能是指针
// 参考文章:https://www.codenong.com/44638610/
func (ct CustomTime) Value() (driver.Value, error) {
	return driver.Value(ct.Local().Format(ctLayout)), nil
}

// IsSet ..
func (ct *CustomTime) IsSet() bool {
	return ct.UnixNano() != nilTime
}
