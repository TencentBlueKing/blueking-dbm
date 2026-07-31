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
	MetricLabelURL         = "url"
	MetricLabelMethod      = "method"
	MetricLabelStatusCode  = "status_code"
	MetricLabelBizID       = "biz_id"

	MetricServerName                 = "analysis"
	MetricApiNameQueryMetadata       = "query_metadata"
	MetricApiNameSyncMetadata        = "sync_metadata"
	MetricQueryTypeReadMetadata      = "read_metadata"
	MetricQueryTypeReadSkipInstances = "read_skip_instances"
	MetricQueryTypeReadDBStatus      = "read_db_status"
)

var (
	// Scan*
	ScanBusinessTimeConsumingMs *haapm.HaHistogram
	ScanBusinessTotal           *haapm.HaCounter

	// PopSwitch*
	PopSwitchTimeConsumingMs *haapm.HaHistogram
	PopSwitchBusinessTotal   *haapm.HaCounter

	// SlidingWindow*
	SlidingWindowSize *haapm.HaGauge

	// Am Business*
	AmBusinessTotal *haapm.HaGauge

	// Switching*
	TriggerSwitchingInstanceTotal *haapm.HaCounter
	SwitchingInstanceErrorTotal   *haapm.HaCounter
	SwitchingInstanceSuccessTotal *haapm.HaCounter
	SwitchingTimeConsumingMs      *haapm.HaHistogram

	// DB*
	DbQueryTimeConsumingMs *haapm.HaHistogram
	DbQueryErrorTotal      *haapm.HaCounter

	// ThirdPartyAPI*
	ThirdPartyApiRequestTimeConsumingMs *haapm.HaHistogram
	ThirdPartyApiRequestErrorTotal      *haapm.HaCounter

	// DBM API*
	DbmApiSyncMetadataTotal            *haapm.HaCounter
	DbmApiSyncMetadataTimeConsumingMs  *haapm.HaHistogram
	DbmApiSyncMetadataErrorTotal       *haapm.HaCounter
	DbmApiQueryMetadataTimeConsumingMs *haapm.HaHistogram
	DbmApiQueryMetadataErrorTotal      *haapm.HaCounter
	DbmApiQueryMetadataIpCount         *haapm.HaGauge

	// SSH Detector*
	DetectorSshTimeConsumingMs *haapm.HaHistogram
	DetectorSshErrorTotal      *haapm.HaCounter

	// Dbm Metadata*
	DbmMetadataSaveTimeConsumingMs *haapm.HaHistogram
	DbmMetadataUpdatedCount        *haapm.HaGauge
	DbhaDataStatusUpdatedCount     *haapm.HaGauge
)

func init() {
	initScanMetrics()
	initPopSwitchMetrics()
	initSwitchingMetrics()
	initSlidingWindowMetrics()
	initAmBusinessMetrics()
	initDBMetrics()
	initThirdPartyApiMetrics()
	initDbmApiMetrics()
	initDetectorMetrics()
	initDbTableUpdatedMetrics()
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
		haapm.DefaultDurationBuckets,
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
		haapm.DefaultDurationBuckets,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)
}

func initSlidingWindowMetrics() {
	SlidingWindowSize = haapm.NewHaGauge(
		"sliding_window_size",
		"Size of sliding window",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelBizID,
	)
}

func initAmBusinessMetrics() {
	AmBusinessTotal = haapm.NewHaGauge(
		"am_business_total",
		"Total number of business processed by am",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)
}

func initSwitchingMetrics() {
	// Trigger switching instance total counter
	TriggerSwitchingInstanceTotal = haapm.NewHaCounter(
		"trigger_switching_instance_total",
		"Total number of trigger switching instances",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// Switching time consuming histogram
	SwitchingTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"switching_time_consuming_ms",
		"Time consuming of switching in milliseconds",
		haapm.DefaultDurationBuckets,
		MetricLabelDbType,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// Switching instance success total counter
	SwitchingInstanceSuccessTotal = haapm.NewHaCounter(
		"switching_instance_success_total",
		"Total number of switching instance success",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// Switching instance error total counter
	SwitchingInstanceErrorTotal = haapm.NewHaCounter(
		"switching_instance_error_total",
		"Total number of switching instance error",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)
}

func initDBMetrics() {
	// DB query time consuming histogram
	DbQueryTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"db_query_time_consuming_ms",
		"Time consuming of database queries in milliseconds",
		haapm.DefaultDurationBuckets,
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

func initThirdPartyApiMetrics() {
	// Third-party API request time consuming histogram
	ThirdPartyApiRequestTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"third_party_api_request_time_consuming_ms",
		"Time consuming of third-party API requests in milliseconds",
		haapm.DefaultDurationBuckets,
		MetricLabelURL, MetricLabelMethod, MetricLabelStatusCode,
		haapm.MetricLabelServiceName,
	)

	// Third-party API request error counter
	ThirdPartyApiRequestErrorTotal = haapm.NewHaCounter(
		"third_party_api_request_error_total",
		"Total number of third-party API request errors",
		MetricLabelURL, MetricLabelMethod, MetricLabelStatusCode,
		haapm.MetricLabelServiceName,
	)
}

func initDbmApiMetrics() {
	// DBM API sync metadata total counter
	DbmApiSyncMetadataTotal = haapm.NewHaCounter(
		"dbm_api_sync_metadata_total",
		"Total number of DBM API sync metadata",
		MetricLabelApiName,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// DBM API sync metadata request time consuming histogram
	DbmApiSyncMetadataTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"dbm_api_sync_metadata_request_time_consuming_ms",
		"Time consuming of DBM API sync metadata requests in milliseconds",
		haapm.DefaultDurationBuckets,
		MetricLabelApiName,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// DBM API sync metadata request error counter
	DbmApiSyncMetadataErrorTotal = haapm.NewHaCounter(
		"dbm_api_sync_metadata_request_error_total",
		"Total number of DBM API sync metadata request errors",
		MetricLabelApiName,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// DBM API query metadata time consuming histogram
	DbmApiQueryMetadataTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"dbm_api_query_metadata_request_time_consuming_ms",
		"Time consuming of DBM API query metadata requests in milliseconds",
		haapm.DefaultDurationBuckets,
		MetricLabelApiName,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelStatusCode,
	)

	// DBM API query metadata error counter
	DbmApiQueryMetadataErrorTotal = haapm.NewHaCounter(
		"dbm_api_query_metadata_request_error_total",
		"Total number of DBM API query metadata request errors",
		MetricLabelApiName,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelStatusCode,
	)

	// DBM API query metadata ip count gauge
	DbmApiQueryMetadataIpCount = haapm.NewHaGauge(
		"dbm_api_query_metadata_ip_count",
		"Number of DBM API query metadata request ips per query",
		MetricLabelApiName,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)
}

func initDetectorMetrics() {
	// SSH detector time consuming histogram
	DetectorSshTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"detector_ssh_time_consuming_ms",
		"Time consuming of SSH detection in milliseconds",
		haapm.DefaultDurationBuckets,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelStatusCode,
	)

	// SSH detector error counter
	DetectorSshErrorTotal = haapm.NewHaCounter(
		"detector_ssh_error_total",
		"Total number of SSH detection errors",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelStatusCode,
	)
}

func initDbTableUpdatedMetrics() {
	// DbmMetadata updated time consuming histogram
	DbmMetadataSaveTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"dbm_metadata_save_time_consuming_ms",
		"Time consuming of DbmMetadata save in milliseconds",
		haapm.DefaultDurationBuckets,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// DbmMetadata rows updated within the latest statistics window, grouped by db_type.
	DbmMetadataUpdatedCount = haapm.NewHaGauge(
		"dbm_metadata_updated_count",
		"Number of DbmMetadata rows updated within the latest statistics window, by db_type",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelDbType,
	)

	// DbhaDataStatus rows updated within the latest statistics window, grouped by db_type.
	DbhaDataStatusUpdatedCount = haapm.NewHaGauge(
		"dbha_data_status_updated_count",
		"Number of DbhaDataStatus rows updated within the latest statistics window, by db_type",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelDbType,
	)
}

// InitAPM sets service labels for startup metric and registers all metrics to haapm (Option 2).
// Must be called before haapm.Serve so metrics are collected automatically.
func InitAPM(serviceID, serviceName string) {
	haapm.AppStartupMetric.UpdateLabel(map[string]string{
		haapm.MetricLabelServiceID:   serviceID,
		haapm.MetricLabelServiceName: serviceName,
	})

	fw := frameworkMetrics()
	db := DbMetrics()
	all := make([]interface{}, 0, len(fw)+len(db))
	all = append(all, fw...)
	all = append(all, db...)
	haapm.MustRegister(all...)
}
