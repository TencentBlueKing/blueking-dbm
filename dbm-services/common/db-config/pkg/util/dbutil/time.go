package util

import (
	"database/sql/driver"
	"encoding/json"
	"errors"
	"fmt"
	"time"
)

// TimeFormat TODO
type TimeFormat string

// Value TODO
func (t TimeFormat) Value() (driver.Value, error) {
	if t.IsNull() {
		return nil, nil
	}
	localTimezone, err := time.LoadLocation("Local") // 服务器设置的时区
	if err != nil {
		fmt.Printf("time.LoadLocation error:%s", err)
		localTimezone, _ = time.LoadLocation("Asia/Shanghai") // 失败的话，默认就是上海的时区
	}
	ti, err := time.ParseInLocation("2006-01-02 15:04:05", string(t), localTimezone)
	if err != nil {
		fmt.Printf("TimeFormat Value error:%s", err)
		return time.Now(), nil
	}
	return ti.In(localTimezone), nil
}

// Scan TODO
func (t *TimeFormat) Scan(value interface{}) error {
	localTimezone, err := time.LoadLocation("Local") // 服务器设置的时区
	if err != nil {
		fmt.Printf("time.LoadLocation error:%s", err)
		localTimezone, _ = time.LoadLocation("Asia/Shanghai") // 失败的话，默认就是上海的时区
	}
	// fmt.Println("Scan()")
	if value == nil {
		*t = ""
		return nil
	}
	s, ok := value.(time.Time)
	if !ok {
		return errors.New("Invalid Scan Source")
	}
	// 记得哪里需要加上反引号。。
	// *t = TimeFormat(s.In(localTimezone).Format("2006-01-02 15:04:05"))
	*t = TimeFormat("\"" + s.In(localTimezone).Format("2006-01-02 15:04:05") + "\"")
	return nil
}

// MarshalJSON TODO
func (t TimeFormat) MarshalJSON() ([]byte, error) {
	if t == "" {
		return []byte("\"\""), nil
	}
	return []byte(fmt.Sprintf("\"%s\"", string(t))), nil
	// return []byte(t), nil
}

// UnmarshalJSON TODO
func (t *TimeFormat) UnmarshalJSON(data []byte) error {
	/*
	   fmt.Println("UnmarshalJSON()")
	   if t == nil {
	       return errors.New("null point exception")
	   }
	   *t = TimeFormat(string(data[:]))
	   return nil
	*/
	var str string
	err := json.Unmarshal(data, &str)
	*t = TimeFormat(str)
	return err
}

// IsNull TODO
func (t TimeFormat) IsNull() bool {
	// fmt.Println("IsNull()")
	return len(t) == 0 || t == ""
}

// Add TODO
func (t TimeFormat) Add(d time.Duration) time.Time {
	// fmt.Println("IsNull()")
	if t.IsNull() {
		return time.Now()
	}
	localTimezone, err := time.LoadLocation("Local") // 服务器设置的时区
	if err != nil {
		fmt.Printf("time.LoadLocation error:%s", err)
		localTimezone, _ = time.LoadLocation("Asia/Shanghai") // 失败的话，默认就是上海的时区
	}
	ti, err := time.ParseInLocation("2006-01-02 15:04:05", string(t), localTimezone)
	if err != nil {
		fmt.Printf("TimeFormat Value error:%s", err)
		return time.Now()
	}
	return ti.Add(d)
}
