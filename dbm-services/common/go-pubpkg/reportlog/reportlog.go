// Package reportlog TODO
package reportlog

import "time"

const (
	// ReportTimeLayout1 YYYY-MM-DDTHH:mm:ssZ  example: 2023-12-08T05:03:07+08:00
	ReportTimeLayout1 = time.RFC3339 //"2006-01-02T15:04:05-0700"
	// ReportTimeLayout2 rfc3339 example: 2023-12-08T05:03:07Z08:00
	ReportTimeLayout2 = "2006-01-02T15:04:05Z0700"
	// ReportTimeLayout3 YYYY-MM-DDTHH:mm:ss.SSSSSSZ example: 2023-12-08T05:03:07.123456+08:00
	ReportTimeLayout3 = "2006-01-02T15:04:05.000000-07:00"
)
