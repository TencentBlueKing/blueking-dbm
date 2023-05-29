package util

import (
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"fmt"
	"time"
)

// InitTimezone TODO
func InitTimezone(tzConf config.TimezoneConfig) {
	switch tzConf.Local {
	case constvar.TZ_UTC:
		SetTimezoneToUTC()
	case constvar.TZ_CST:
		SetTimezoneToCST()
	default:
		SetTimezoneToCST()
	}
}

// SetTimezoneToUTC TODO
func SetTimezoneToUTC() {
	time.Local = time.UTC
}

// SetTimezoneToCST TODO
func SetTimezoneToCST() {
	loc, err := time.LoadLocation("Asia/Shanghai")
	if err != nil {
		fmt.Println("load time location failed")
	} else {
		time.Local = loc
		fmt.Printf("timezone is set to CST Asia/shanghai\n")
	}
}
