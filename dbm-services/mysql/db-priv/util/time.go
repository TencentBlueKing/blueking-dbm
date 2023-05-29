package util

import (
	"database/sql/driver"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"golang.org/x/exp/slog"
)

// TimeFormat TODO
type TimeFormat string

// Value TODO
/*
在 gorm save 或者 update 的时候调用该方法，这个就是 string -> time 的地方。
*/
func (t TimeFormat) Value() (driver.Value, error) {
	if t.IsNull() {
		return nil, nil
	}
	localTimezone, err := time.LoadLocation("Local") // 服务器设置的时区
	if err != nil {
		slog.Error("time.LoadLocation", err)
		localTimezone, _ = time.LoadLocation("Asia/Shanghai") // 失败的话，默认就是上海的时区
	}
	ti, err := time.ParseInLocation("2006-01-02 15:04:05", string(t), localTimezone)
	if err != nil {
		slog.Error("TimeFormat Value", err)
		return time.Now(), nil
	}
	return ti.In(localTimezone), nil
}

/*
 1. 在调用 gorm 的 find 查询类操作的时候，会调用数据类型的 Scan 方法。
  2. 但是如果 value 是 nil ，就不会调用。
    2.1 这个时候，如果在后面进行 marshall 的时候，需要 return []byte("\"\"")，
		否则会出现 "json: error calling MarshalJSON for type model.TimeFormat: unexpected end of JSON input" 错误。
*/

// Scan TODO
/* Scan
 1. 在调用 gorm 的 find 查询类操作的时候，会调用数据类型的 Scan 方法。
 2. 但是如果 value 是 nil ，就不会调用。
    2.1 这个时候，如果在后面进行 marshall 的时候，需要 return []byte("\"\"")，
		否则会出现 "json: error calling MarshalJSON for type model.TimeFormat: unexpected end of JSON input" 错误。
*/
func (t *TimeFormat) Scan(value interface{}) error {
	localTimezone, err := time.LoadLocation("Local") // 服务器设置的时区
	if err != nil {
		slog.Error("time.LoadLocation error", err)
		localTimezone, _ = time.LoadLocation("Asia/Shanghai") // 失败的话，默认就是上海的时区
	}
	if value == nil {
		*t = "\"2006-01-02 00:00:00\""
		return nil
	}
	s, ok := value.(time.Time)
	if !ok {
		return errors.New("Invalid Scan Source")
	}
	// 记得哪里需要加上反引号。。
	// *t = TimeFormat(s.In(localTimezone).Format("2006-01-02 15:04:05"))
	*t = TimeFormat(s.In(localTimezone).Format("2006-01-02 15:04:05"))
	return nil
}

// MarshalJSON 在 handler.go 执行 SendResponse 的 c.WriteHeaderAndJSON 时候，会调用该方法。
func (t TimeFormat) MarshalJSON() ([]byte, error) {
	if t == "" {
		return []byte("\"\""), nil
	}
	return []byte(fmt.Sprintf("\"%s\"", string(t))), nil
	// return []byte(t), nil
}

// UnmarshalJSON TODO
func (t *TimeFormat) UnmarshalJSON(data []byte) error {
	var str string
	err := json.Unmarshal(data, &str)
	*t = TimeFormat(str)
	return err
}

// IsNull TODO
func (t TimeFormat) IsNull() bool {
	return len(t) == 0 || t == ""
}

// NowTimeFormat TODO
func NowTimeFormat() TimeFormat {
	return TimeFormat(time.Now().Format("2006-01-02 15:04:05"))
}
