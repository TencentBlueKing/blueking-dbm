package cmutil

import "time"

// TimeToSecondPrecision keep only second precision for time
func TimeToSecondPrecision(t time.Time) time.Time {
	timeStr := t.Local().Format(time.RFC3339)
	tt, _ := time.ParseInLocation(time.RFC3339, timeStr, time.Local)
	return tt
}
