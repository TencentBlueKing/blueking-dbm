package cmutil

import (
	"time"

	"github.com/pkg/errors"
)

// TimeToSecondPrecision keep only second precision for time
func TimeToSecondPrecision(t time.Time) time.Time {
	timeStr := t.Local().Format(time.RFC3339)
	tt, _ := time.ParseInLocation(time.RFC3339, timeStr, time.Local)
	return tt
}

// ParseLocalTimeString 讲 time.Datetime or time.RFC3339 格式转换传本地时区 time.Time 类型
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
