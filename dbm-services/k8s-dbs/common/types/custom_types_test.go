package types

import (
	"os"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func TestToDateString(t *testing.T) {
	err := os.Setenv("TZ", "Asia/Shanghai")
	if err != nil {
		return
	}
	defer func() {
		err := os.Unsetenv("TZ")
		if err != nil {
			panic(err)
		}
	}()
	location, err = time.LoadLocation(timeZone)
	parsedTime, err := time.ParseInLocation(time.RFC3339, "2025-07-18T12:00:00+08:00", location)
	if err != nil {
		panic(err)
	}
	var jd = JSONDatetime(parsedTime)
	assert.Equal(t, "2025-07-18 12:00:00", jd.ToDateString())
}

func TestMarshalJSON(t *testing.T) {
	err := os.Setenv("TZ", "Asia/Shanghai")
	if err != nil {
		return
	}
	defer func() {
		err := os.Unsetenv("TZ")
		if err != nil {
			panic(err)
		}
	}()
	parsedTime, err := time.Parse(time.RFC3339, "2025-07-18T12:00:00+08:00")
	if err != nil {
		panic(err)
	}
	jd := JSONDatetime(parsedTime)
	jsonStr, err := jd.MarshalJSON()
	if err != nil {
		panic(err)
	}
	assert.Equal(t, "\"2025-07-18 12:00:00\"", string(jsonStr))
}

func TestUnmarshalJSON(t *testing.T) {
	err := os.Setenv("TZ", "Asia/Shanghai")
	if err != nil {
		return
	}
	defer func() {
		err := os.Unsetenv("TZ")
		if err != nil {
			panic(err)
		}
	}()
	dateStr := "\"2025-07-18 12:00:00\""
	var jd JSONDatetime
	err = jd.UnmarshalJSON([]byte(dateStr))
	if err != nil {
		panic(err)
	}
	assert.NotNil(t, jd)
	assert.Equal(t, "2025-07-18 12:00:00", jd.ToDateString())
}
