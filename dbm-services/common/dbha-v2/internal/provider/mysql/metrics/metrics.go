/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

// Package mysqlmetrics owns MySQL switching APM metrics and self-registers them.
package mysqlmetrics

import (
	"dbm-services/common/dbha-v2/internal/analysis/apm"
	"dbm-services/common/dbha-v2/pkg/haapm"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var (
	ClusterSwitchingTimeConsumingMs  *haapm.HaHistogram
	HostSwitchingTimeConsumingMs     *haapm.HaHistogram
	InstanceSwitchingTimeConsumingMs *haapm.HaHistogram
	SwitchingSuccessTotal            *haapm.HaCounter
	SwitchingErrorTotal              *haapm.HaCounter
)

func init() {
	ClusterSwitchingTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"mysql_cluster_switching_time_consuming_ms",
		"Time consuming of MySQL cluster switching in milliseconds",
		haapm.DefaultDurationBuckets,
		apm.MetricLabelSwitchID, apm.MetricLabelActionScope, apm.MetricLabelDbType,
	)

	HostSwitchingTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"mysql_host_switching_time_consuming_ms",
		"Time consuming of MySQL host switching in milliseconds",
		haapm.DefaultDurationBuckets,
		apm.MetricLabelSwitchID, apm.MetricLabelActionScope, apm.MetricLabelDbType,
	)

	InstanceSwitchingTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"mysql_instance_switching_time_consuming_ms",
		"Time consuming of MySQL instance switching in milliseconds",
		haapm.DefaultDurationBuckets,
		apm.MetricLabelSwitchID, apm.MetricLabelActionScope, apm.MetricLabelDbType,
	)

	SwitchingSuccessTotal = haapm.NewHaCounter(
		"mysql_switching_success_total",
		"Total number of MySQL switching success",
		apm.MetricLabelActionScope, apm.MetricLabelDbType,
	)

	SwitchingErrorTotal = haapm.NewHaCounter(
		"mysql_switching_error_total",
		"Total number of MySQL switching error",
		apm.MetricLabelActionScope, apm.MetricLabelDbType,
	)

	apm.RegisterDbMetrics(
		haprobe.DbTypeMySql,
		ClusterSwitchingTimeConsumingMs,
		HostSwitchingTimeConsumingMs,
		InstanceSwitchingTimeConsumingMs,
		SwitchingSuccessTotal,
		SwitchingErrorTotal,
	)
}
