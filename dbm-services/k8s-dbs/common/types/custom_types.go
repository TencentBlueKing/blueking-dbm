package types

import (
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"sync"
	"time"
)

type JSONDatetime time.Time

const DefaultTimeZone = "Asia/shanghai"

var (
	timeZone string
	location *time.Location
	once     sync.Once
)

// initLocation 初始化时区
func initLocation() {
	timeZone = os.Getenv("TZ")
	if timeZone == "" {
		timeZone = DefaultTimeZone
	}
	var err error
	location, err = time.LoadLocation(timeZone)
	if err != nil {
		location = time.Local
		slog.Warn("load time zone failed, using default timezone", "timezone", timeZone)
	}
}

// MarshalJSON 自定义 JSONDatetime JSON 序列化逻辑
func (j JSONDatetime) MarshalJSON() ([]byte, error) {
	once.Do(initLocation)
	locTime := time.Time(j).In(location)
	return []byte(fmt.Sprintf("\"%s\"", locTime.Format(time.DateTime))), nil
}

// UnmarshalJSON 自定义 JSONDatetime JSON 反序列化逻辑
func (j *JSONDatetime) UnmarshalJSON(data []byte) error {
	once.Do(initLocation)
	if string(data) == "null" {
		return nil
	}
	if len(data) < 2 || data[0] != '"' || data[len(data)-1] != '"' {
		return errors.New("Time.UnmarshalJSON: input is not a JSON string")
	}
	var timeStr string
	if err := json.Unmarshal(data, &timeStr); err != nil {
		return fmt.Errorf("invalid JSON datetime format: %w", err)
	}
	parsedTime, err := time.ParseInLocation(time.DateTime, timeStr, location)
	if err != nil {
		return fmt.Errorf("failed to parse datetime: %w", err)
	}
	*j = JSONDatetime(parsedTime)
	return nil
}

// ToDateString 将 JSONDatetime 格式化为 "yyyy-MM-dd HH:mm:ss" 字符串
func (j JSONDatetime) ToDateString() string {
	return time.Time(j).Format(time.DateTime)
}
