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

package apm

import (
	"dbm-services/common/dbha-v2/pkg/haapm"
)

const (
	MetricLabelSwitchID    = "switch_id"
	MetricLabelActionScope = "action_scope"
	MetricLabelDbType      = "db_type"
)

var (
	// Mysql*
	MysqlClusterSwitchingTimeConsumingMs  *haapm.HaHistogram
	MysqlHostSwitchingTimeConsumingMs     *haapm.HaHistogram
	MysqlInstanceSwitchingTimeConsumingMs *haapm.HaHistogram
	MysqlSwitchingErrorTotal              *haapm.HaCounter
	MysqlSwitchingSuccessTotal            *haapm.HaCounter

	// Redis*
	RedisSwitchingErrorTotal   *haapm.HaCounter
	RedisSwitchingSuccessTotal *haapm.HaCounter

	// Scan*
	ScanBusinessTimeConsumingMs *haapm.HaHistogram
	ScanBusinessTotal           *haapm.HaCounter

	// Switching*
	SwitchingErrorTotal      *haapm.HaCounter
	SwitchingSuccessTotal    *haapm.HaCounter
	SwitchingTimeConsumingMs *haapm.HaHistogram
)

// Default histogram buckets for latency (milliseconds)
var defaultLatencyBuckets = []float64{1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000}

func init() {
	// Scan business total counter
	ScanBusinessTotal = haapm.NewHaCounter(
		"scan_business_total",
		"Total number of scan business",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// Scan business time consuming histogram
	ScanBusinessTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"scan_business_time_consuming_ms",
		"Time consuming of scan business in milliseconds",
		defaultLatencyBuckets,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// Switching time consuming histogram
	SwitchingTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"switching_time_consuming_ms",
		"Time consuming of switching in milliseconds",
		defaultLatencyBuckets,
		MetricLabelDbType,
	)

	// Mysql cluster switching time consuming histogram
	MysqlClusterSwitchingTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"mysql_cluster_switching_time_consuming_ms",
		"Time consuming of MySQL cluster switching in milliseconds",
		defaultLatencyBuckets,
		MetricLabelSwitchID, MetricLabelActionScope, MetricLabelDbType,
	)

	// Mysql host switching time consuming histogram
	MysqlHostSwitchingTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"mysql_host_switching_time_consuming_ms",
		"Time consuming of MySQL host switching in milliseconds",
		defaultLatencyBuckets,
		MetricLabelSwitchID, MetricLabelActionScope, MetricLabelDbType,
	)

	// Mysql instance switching time consuming histogram
	MysqlInstanceSwitchingTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"mysql_instance_switching_time_consuming_ms",
		"Time consuming of MySQL instance switching in milliseconds",
		defaultLatencyBuckets,
		MetricLabelSwitchID, MetricLabelActionScope, MetricLabelDbType,
	)

	// Switching success total counter
	SwitchingSuccessTotal = haapm.NewHaCounter("switching_success_total", "Total number of switching success")

	// Switching error total counter
	SwitchingErrorTotal = haapm.NewHaCounter("switching_error_total", "Total number of switching error")

	// Mysql switching success total counter
	MysqlSwitchingSuccessTotal = haapm.NewHaCounter(
		"mysql_switching_success_total",
		"Total number of MySQL switching success",
		MetricLabelActionScope, MetricLabelDbType,
	)

	// Mysql switching error total counter
	MysqlSwitchingErrorTotal = haapm.NewHaCounter(
		"mysql_switching_error_total",
		"Total number of MySQL switching error",
		MetricLabelActionScope, MetricLabelDbType,
	)

	// Redis switching success total counter
	RedisSwitchingSuccessTotal = haapm.NewHaCounter(
		"redis_switching_success_total",
		"Total number of Redis switching success",
		MetricLabelActionScope, MetricLabelDbType,
	)

	// Redis switching error total counter
	RedisSwitchingErrorTotal = haapm.NewHaCounter(
		"redis_switching_error_total",
		"Total number of Redis switching error",
		MetricLabelActionScope, MetricLabelDbType,
	)
}

// InitAPM sets service labels for startup metric and registers all metrics to haapm (Option 2).
// Must be called before haapm.Serve so metrics are collected automatically.
func InitAPM(serviceID, serviceName string) {
	haapm.AppStartupMetric.UpdateLabel(map[string]string{
		haapm.MetricLabelServiceID:   serviceID,
		haapm.MetricLabelServiceName: serviceName,
	})

	haapm.MustRegister(
		haapm.AppStartupMetric,
		MysqlClusterSwitchingTimeConsumingMs,
		MysqlHostSwitchingTimeConsumingMs,
		MysqlInstanceSwitchingTimeConsumingMs,
		MysqlSwitchingErrorTotal,
		MysqlSwitchingSuccessTotal,
		RedisSwitchingErrorTotal,
		RedisSwitchingSuccessTotal,
		ScanBusinessTimeConsumingMs,
		ScanBusinessTotal,
		SwitchingErrorTotal,
		SwitchingSuccessTotal,
		SwitchingTimeConsumingMs,
	)
}
