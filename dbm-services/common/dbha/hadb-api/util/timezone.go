package util

import (
	"fmt"
	"time"
)

// InitTimezone init local timezone
func InitTimezone(tzInfo string) {
	switch tzInfo {
	case TZ_UTC:
		SetTimezoneToUTC()
	case TZ_CST:
		SetTimezoneToCST()
	default:
		SetTimezoneToCST()
	}
}

// SetTimezoneToUTC set local timezone to utc
func SetTimezoneToUTC() {
	time.Local = time.UTC
}

// SetTimezoneToCST set local timezone to cst
func SetTimezoneToCST() {
	loc, err := time.LoadLocation("Asia/Shanghai")
	if err != nil {
		fmt.Println("load time location failed")
	} else {
		time.Local = loc
		fmt.Printf("timezone is set to CST Asia/shanghai\n")
	}
}
