package base

import (
	"encoding/json"

	"dbm-services/common/go-pubpkg/cmutil"
)

type MessageWrapper struct {
	Items []struct {
		Data json.RawMessage `json:"data"`
	} `json:"items"`
	Ext map[string]interface{} `json:"ext"`
	// BklogMessage BklogMessage           `json:",inline"`

	Filename string `json:"filename"`
	BkHostId int    `json:"bk_host_id"`
	Ip       string `json:"ip"`
	// Ts 1773032226
	Ts uint `json:"time"`
	// LogTime report local time: 2026-03-09 12:57:06
	LogTime cmutil.Datetime `json:"datetime"`
	// UtcTime report utc time: 2026-03-09 04:57:06
	UtcTime  cmutil.UtcDatetime `json:"utctime"`
	Gseindex int                `json:"gseindex"`
	Dataid   int                `json:"dataid"`
}
