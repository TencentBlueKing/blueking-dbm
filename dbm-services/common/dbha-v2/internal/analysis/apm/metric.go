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
	MetricLabelActionScope = "action_scope"
	MetricLabelDbType      = "db_type"
	MetricLabelQueryType   = "query_type"
	MetricLabelApiName     = "api_name"
	MetricLabelURL         = "url"
	MetricLabelMethod      = "method"
	MetricLabelStatusCode  = "status_code"
	MetricLabelBizID       = "biz_id"
	MetricLabelHarvestType = "harvest_type"
	MetricLabelTable       = "table"
	MetricLabelReason      = "reason"
	MetricLabelStage       = "stage"
	MetricLabelKind        = "kind"

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
	SwitchingRequestedInstanceTotal *haapm.HaCounter
	SwitchingInstanceErrorTotal     *haapm.HaCounter
	SwitchingInstanceSuccessTotal   *haapm.HaCounter
	SwitchingTimeConsumingMs        *haapm.HaHistogram

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
	DbhaDataStatusUpdatedIPCount   *haapm.HaGauge
	DbhaDataStatusActiveIPCount    *haapm.HaGauge

	// Retention*
	RetentionEnabled                           *haapm.HaGauge
	RetentionLeader                            *haapm.HaGauge
	RetentionDeletedRowsTotal                  *haapm.HaCounter
	RetentionAttemptedRowsTotal                *haapm.HaCounter
	RetentionSkippedTotal                      *haapm.HaCounter
	RetentionErrorsTotal                       *haapm.HaCounter
	RetentionStatementTimeConsumingMs          *haapm.HaHistogram
	RetentionRoundTimeConsumingMs              *haapm.HaHistogram
	RetentionPassStaleRows                     *haapm.HaGauge
	RetentionPassScannedRows                   *haapm.HaGauge
	RetentionLastPassCompletedTimestampSeconds *haapm.HaGauge
	RetentionStalled                           *haapm.HaGauge
)

// retentionRoundBuckets covers the 60s default round budget; the default duration buckets stop at 10s.
var retentionRoundBuckets = []float64{100, 500, 1000, 2500, 5000, 10000, 30000, 60000, 120000}

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
	initRetentionMetrics()
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
	// Switching requested instance total counter, counted before the switch executes.
	SwitchingRequestedInstanceTotal = haapm.NewHaCounter(
		"switching_requested_instance_total",
		"Total number of instances requested for switching, counted before the switch executes; "+
			"includes requests later skipped by gating.",
		MetricLabelDbType, MetricLabelActionScope,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// Switching time consuming histogram
	SwitchingTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"switching_time_consuming_ms",
		"Time consuming of switching in milliseconds",
		haapm.DefaultDurationBuckets,
		MetricLabelDbType, MetricLabelActionScope,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// Switching instance success total counter
	SwitchingInstanceSuccessTotal = haapm.NewHaCounter(
		"switching_instance_success_total",
		"Total number of switching instance success",
		MetricLabelDbType, MetricLabelActionScope,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)

	// Switching instance error total counter
	SwitchingInstanceErrorTotal = haapm.NewHaCounter(
		"switching_instance_error_total",
		"Total number of switching instance error",
		MetricLabelDbType, MetricLabelActionScope,
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

	// DbhaDataStatus instances updated within the latest statistics window, grouped by
	// db_type and harvest_type. One instance keeps one row per collection group, so rows
	// are de-duplicated by (bk_cloud_id, db_ip, db_port).
	DbhaDataStatusUpdatedCount = haapm.NewHaGauge(
		"dbha_data_status_updated_count",
		"Number of DbhaDataStatus instances (distinct cloud/ip/port) updated within the latest statistics window, "+
			"by db_type and harvest_type",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelDbType, MetricLabelHarvestType,
	)

	// DbhaDataStatus IPs updated within the latest statistics window, grouped by db_type and harvest_type.
	DbhaDataStatusUpdatedIPCount = haapm.NewHaGauge(
		"dbha_data_status_updated_ip_count",
		"Number of IPs (distinct cloud/ip) with DbhaDataStatus updated within the latest statistics window, "+
			"by db_type and harvest_type",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelDbType, MetricLabelHarvestType,
	)

	// Alive probe IP count within the latest statistics window, by db_type.
	DbhaDataStatusActiveIPCount = haapm.NewHaGauge(
		"dbha_data_status_active_ip_count",
		"Number of IPs (distinct cloud/ip) that reported within the latest statistics window, by db_type: "+
			"active (reporting) IPs, not an installed count",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelDbType,
	)
}

func initRetentionMetrics() {
	RetentionEnabled = haapm.NewHaGauge(
		"retention_enabled",
		"Whether stale-row retention is enabled in this instance (1) or not (0)",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)
	RetentionLeader = haapm.NewHaGauge(
		"retention_leader",
		"Whether this instance holds the retention election (1) or not (0)",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName,
	)
	RetentionDeletedRowsTotal = haapm.NewHaCounter(
		"retention_deleted_rows_total",
		"Total number of stale rows physically deleted by retention, by table",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelTable,
	)
	RetentionAttemptedRowsTotal = haapm.NewHaCounter(
		"retention_attempted_rows_total",
		"Total number of stale candidate rows submitted to DELETE by retention, by table",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelTable,
	)
	RetentionSkippedTotal = haapm.NewHaCounter(
		"retention_skipped_total",
		"Total number of retention runs that yielded on purpose, by table and reason",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelTable, MetricLabelReason,
	)
	RetentionErrorsTotal = haapm.NewHaCounter(
		"retention_errors_total",
		"Total number of retention statement failures, by table, stage and kind",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelTable, MetricLabelStage, MetricLabelKind,
	)
	RetentionStatementTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"retention_statement_time_consuming_ms",
		"Time consuming of retention statements in milliseconds, by table and stage",
		haapm.DefaultDurationBuckets,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelTable, MetricLabelStage,
	)
	RetentionRoundTimeConsumingMs = haapm.NewHaHistogramWithBuckets(
		"retention_round_time_consuming_ms",
		"Time consuming of one retention run on a table in milliseconds",
		retentionRoundBuckets,
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelTable,
	)

	initRetentionPassMetrics()
}

func initRetentionPassMetrics() {
	RetentionPassStaleRows = haapm.NewHaGauge(
		"retention_pass_stale_rows",
		"Stale rows submitted to DELETE during the latest completed retention pass, by table",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelTable,
	)
	RetentionPassScannedRows = haapm.NewHaGauge(
		"retention_pass_scanned_rows",
		"Rows covered by the cursor during the latest completed retention pass, by table",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelTable,
	)
	RetentionLastPassCompletedTimestampSeconds = haapm.NewHaGauge(
		"retention_last_pass_completed_timestamp_seconds",
		"Unix time of the latest completed retention pass, initialized to the election time, by table",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelTable,
	)
	RetentionStalled = haapm.NewHaGauge(
		"retention_stalled",
		"Whether retention made no progress for stallAlertAfter while work or errors existed (1) or not (0)",
		haapm.MetricLabelServiceID, haapm.MetricLabelServiceName, MetricLabelTable,
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
