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
	MetricLabelQueryType   = "query_type"
	MetricLabelApiName     = "api_name"

	MetricServerName                 = "analysis"
	MetricApiNameQueryMetadata       = "query_metadata"
	MetricApiNameSyncMetadata        = "sync_metadata"
	MetricQueryTypeReadMetadata      = "read_metadata"
	MetricQueryTypeReadSkipInstances = "read_skip_instances"
	MetricQueryTypeReadDBStatus      = "read_db_status"
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

	// PopSwitch*
	PopSwitchTimeConsumingMs *haapm.HaHistogram
	PopSwitchBusinessTotal   *haapm.HaCounter

	// Switching*
	SwitchingErrorTotal      *haapm.HaCounter
	SwitchingSuccessTotal    *haapm.HaCounter
	SwitchingTimeConsumingMs *haapm.HaHistogram

	// DB*
	DbQueryTimeConsumingMs *haapm.HaHistogram
	DbQueryErrorTotal      *haapm.HaCounter

	// DBM API*
	DbmApiRequestTimeConsumingMs *haapm.HaHistogram
	DbmApiRequestErrorTotal      *haapm.HaCounter

	// SSH Detector*
	DetectorSshTimeConsumingMs *haapm.HaHistogram
	DetectorSshErrorTotal      *haapm.HaCounter
)

// Default histogram buckets for latency (milliseconds)
var defaultLatencyBuckets = []float64{1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000}

func init() {
	initScanMetrics()
	initPopSwitchMetrics()
	initSwitchingMetrics()
	initMySQLMetrics()
	initRedisMetrics()
	initDBMetrics()
	initDbmApiMetrics()
	initDetectorMetrics()
}

func initScanMetrics() {
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
}

func initPopSwitchMetrics() {
	// Pop-switch business total counter
	PopSwitchBusinessTotal = haapm.NewHaCounter(
		"pop_switch_business_total",
		"Total number of business IDs processed by pop-switch",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// Pop-switch business time consuming histogram
	PopSwitchTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"pop_switch_time_consuming_ms",
		"Time consuming of pop-switch business in milliseconds",
		defaultLatencyBuckets,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)
}

func initSwitchingMetrics() {
	// Switching time consuming histogram
	SwitchingTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"switching_time_consuming_ms",
		"Time consuming of switching in milliseconds",
		defaultLatencyBuckets,
		MetricLabelDbType,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// Switching success total counter
	SwitchingSuccessTotal = haapm.NewHaCounter(
		"switching_success_total",
		"Total number of switching success",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// Switching error total counter
	SwitchingErrorTotal = haapm.NewHaCounter(
		"switching_error_total",
		"Total number of switching error",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)
}

func initMySQLMetrics() {
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
}

func initRedisMetrics() {
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

func initDBMetrics() {
	// DB query time consuming histogram
	DbQueryTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"db_query_time_consuming_ms",
		"Time consuming of database queries in milliseconds",
		defaultLatencyBuckets,
		MetricLabelQueryType,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// DB query error counter
	DbQueryErrorTotal = haapm.NewHaCounter(
		"db_query_error_total",
		"Total number of database query errors",
		MetricLabelQueryType,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)
}

func initDbmApiMetrics() {
	// DBM API request time consuming histogram
	DbmApiRequestTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"dbm_api_request_time_consuming_ms",
		"Time consuming of DBM API requests in milliseconds",
		defaultLatencyBuckets,
		MetricLabelApiName,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// DBM API request error counter
	DbmApiRequestErrorTotal = haapm.NewHaCounter(
		"dbm_api_request_error_total",
		"Total number of DBM API request errors",
		MetricLabelApiName,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)
}

func initDetectorMetrics() {
	// SSH detector time consuming histogram
	DetectorSshTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"detector_ssh_time_consuming_ms",
		"Time consuming of SSH detection in milliseconds",
		defaultLatencyBuckets,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// SSH detector error counter
	DetectorSshErrorTotal = haapm.NewHaCounter(
		"detector_ssh_error_total",
		"Total number of SSH detection errors",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
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
		PopSwitchBusinessTotal,
		PopSwitchTimeConsumingMs,
		ScanBusinessTimeConsumingMs,
		ScanBusinessTotal,
		SwitchingErrorTotal,
		SwitchingSuccessTotal,
		SwitchingTimeConsumingMs,
		DbQueryTimeConsumingMs,
		DbQueryErrorTotal,
		DbmApiRequestTimeConsumingMs,
		DbmApiRequestErrorTotal,
		DetectorSshTimeConsumingMs,
		DetectorSshErrorTotal,
	)
}
