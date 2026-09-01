package base

import (
	json "github.com/goccy/go-json"

	"dbm-services/common/go-pubpkg/cmutil"
)

// MessageWrapper bklog message
/*
map[
    bizid:0
    bk_agent_id:abcdefg
    bk_biz_id:1234
    bk_host_id:9.858837e+06
    cloudid:0
    dataid:123465
    datetime:2026-08-11 08:46:04
    ext:map[]
    filename:/data/mysql-proxy/10000/log/mysql-proxy.log
    gseindex:12345
    hostname:VM-aa-bb-tencentos
    ip:1.2.3.4
    items:[
        map[data:2026-08-11 08:46:03: (critical) conn_log, current user is 'user1'@'1.2.3.4' 36428656    iterationindex:0]
        map[data:2026-08-11 08:46:03: (critical) conn_log, current user is 'user2'@'1.2.3.4' 1920517042   iterationindex:2]
    ]
    time:1.786409164e+09
    utctime:2026-08-11 00:46:04
]
*/
type MessageWrapper struct {
	Items []struct {
		Data json.RawMessage `json:"data"`
	} `json:"items"`
	Ip       string                 `json:"ip"`
	Filename string                 `json:"filename"`
	Ext      map[string]interface{} `json:"ext"`

	ParseFailure bool `json:"__parse_failure"`
	BkHostId     int  `json:"bk_host_id"`
	// Ts 1773032226
	Ts uint `json:"time"`
	// LogTime report local time: 2026-03-09 12:57:06
	LogTime cmutil.Datetime `json:"datetime"`
	// UtcTime report utc time: 2026-03-09 04:57:06
	UtcTime   cmutil.UtcDatetime `json:"utctime"`
	Dataid    int                `json:"dataid"`
	BkCloudId int                `json:"cloudid"`
	//Gseindex int                `json:"gseindex"`
}

type MessageWrapper2 map[string]interface{}
