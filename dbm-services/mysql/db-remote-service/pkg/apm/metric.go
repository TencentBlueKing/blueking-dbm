package apm

import "dbm-services/common/go-pubpkg/apm/metric"

var (
	ErrCnt     = "err_cnt"
	ExecuteCnt = "execute_cnt"
)

var CustomMetrics = []*metric.Metric{
	{
		ID:          ErrCnt,
		Name:        ErrCnt,
		Description: "Counter test metric",
		Type:        "counter_vec",
		Labels:      []string{"url", "method", "code"},
	},
	{
		ID:          ExecuteCnt,
		Name:        ExecuteCnt,
		Description: "Counter test metric",
		Type:        "counter_vec",
		Labels:      []string{"url", "method", "code"},
	},
}
