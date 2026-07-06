// Package timeutil TODO
package timeutil

import "time"

// GetMidnight 获取指定时间所在自然日的 00:00:00
func GetMidnight(t time.Time) time.Time {
	return time.Date(t.Year(), t.Month(), t.Day(), 0, 0, 0, 0, t.Location())
}
