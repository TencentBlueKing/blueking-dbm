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
	MetricLabelKafka  = "kafka"
	MetricLabelMysql  = "mysql"
	MetricLabelProbe  = "probe"
	MetricLabelSink   = "sink"
	MetricLabelDbType = "db_type"
	MetricLabelReason = "reason"
)

// sinkWriteDelayBuckets covers the 60s analysis window and late writes up to 5 minutes.
var sinkWriteDelayBuckets = []float64{
	1000, 2000, 5000, 10000, 20000, 30000, 45000, 60000, 120000, 300000,
}

var (
	KafkaReadMessagesTotal *haapm.HaCounter
	KafkaReadBytesTotal    *haapm.HaCounter
	KafkaWriteErrorsTotal  *haapm.HaCounter
	KafkaConsumeDelayMs    *haapm.HaHistogram

	MySqlWriteDurationMs      *haapm.HaHistogram
	MySqlWriteMessagesTotal   *haapm.HaCounter
	MySqlWriteBytesTotal      *haapm.HaCounter
	MySqlReadErrorsTotal      *haapm.HaCounter
	MySqlWriteErrorsTotal     *haapm.HaCounter
	MySqlBatchWriteDurationMs *haapm.HaHistogram
	MySqlWriteBatchSize       *haapm.HaHistogram
	MySqlDedupDroppedTotal    *haapm.HaCounter
	MySqlBatchFallbackTotal   *haapm.HaCounter
	MySqlRetryTotal           *haapm.HaCounter

	ProbeReceiveMessagesTotal *haapm.HaCounter
	ProbeReceiveBytesTotal    *haapm.HaCounter
	ProbeQueueFullTotal       *haapm.HaCounter

	SinkWriteDelayMs      *haapm.HaHistogram
	SinkDropMessagesTotal *haapm.HaCounter
)

func init() {
	initKafkaMetrics()
	initMySQLMetrics()
	initProbeMetrics()
	initSinkMetrics()
}

func initKafkaMetrics() {
	KafkaReadBytesTotal = haapm.NewHaCounter(
		"kafka_read_bytes_total",
		"Total bytes read from Kafka",
		MetricLabelKafka,
	)
	KafkaReadMessagesTotal = haapm.NewHaCounter(
		"kafka_read_messages_total",
		"Total messages read from Kafka",
		MetricLabelKafka,
	)
	KafkaWriteErrorsTotal = haapm.NewHaCounter(
		"kafka_write_errors_total",
		"Total errors write to Kafka",
		MetricLabelKafka,
	)
	KafkaConsumeDelayMs = haapm.NewHaHistogramWithBuckets(
		"kafka_consume_delay_ms",
		"End-to-end delay from Kafka message timestamp to MySQL write (milliseconds)",
		haapm.DefaultDurationBuckets,
		MetricLabelKafka,
	)
}

func initMySQLMetrics() {
	MySqlWriteDurationMs = haapm.NewHaHistogramWithBuckets(
		"mysql_write_duration_ms",
		"Duration of write to mysql (milliseconds)",
		haapm.DefaultDurationBuckets,
		MetricLabelMysql,
	)
	MySqlBatchWriteDurationMs = haapm.NewHaHistogramWithBuckets(
		"mysql_batch_write_duration_ms",
		"Duration of batch write to mysql per endpoint (milliseconds)",
		haapm.DefaultDurationBuckets,
		MetricLabelMysql,
	)
	MySqlWriteBatchSize = haapm.NewHaHistogramWithBuckets(
		"mysql_write_batch_size",
		"Rows written per batch after dedup",
		haapm.DefaultDurationBuckets,
		MetricLabelMysql,
	)
	MySqlDedupDroppedTotal = haapm.NewHaCounter(
		"mysql_dedup_dropped_total",
		"Total messages dropped by primary-key dedup within a batch",
		MetricLabelMysql,
	)
	MySqlBatchFallbackTotal = haapm.NewHaCounter(
		"mysql_batch_fallback_total",
		"Total times a chunk fell back to per-row write due to data errors",
		MetricLabelMysql,
	)
	MySqlRetryTotal = haapm.NewHaCounter(
		"mysql_retry_total",
		"Total chunk write retry attempts",
		MetricLabelMysql,
	)
	MySqlWriteMessagesTotal = haapm.NewHaCounter(
		"mysql_write_messages_total",
		"Total messages write to mysql",
		MetricLabelMysql,
	)
	MySqlWriteBytesTotal = haapm.NewHaCounter(
		"mysql_write_bytes_total",
		"Total bytes write to mysql",
		MetricLabelMysql,
	)
	MySqlReadErrorsTotal = haapm.NewHaCounter(
		"mysql_read_errors_total",
		"Total errors read from mysql",
		MetricLabelMysql,
	)
	MySqlWriteErrorsTotal = haapm.NewHaCounter(
		"mysql_write_errors_total",
		"Total errors write to mysql",
		MetricLabelMysql,
	)
}

func initProbeMetrics() {
	ProbeReceiveMessagesTotal = haapm.NewHaCounter(
		"probe_receive_messages_total",
		"Total messages receive from Probe",
		MetricLabelProbe,
	)
	ProbeReceiveBytesTotal = haapm.NewHaCounter(
		"probe_receive_bytes_total",
		"Total bytes receive from Probe",
		MetricLabelProbe,
	)
	ProbeQueueFullTotal = haapm.NewHaCounter(
		"probe_queue_full_total",
		"Total queue full times happen to Probe",
		MetricLabelProbe,
	)
}

func initSinkMetrics() {
	SinkWriteDelayMs = haapm.NewHaHistogramWithBuckets(
		"sink_write_delay_ms",
		"Delay from probe report_timestamp to a successful sink write (milliseconds)",
		sinkWriteDelayBuckets,
		MetricLabelSink,
		MetricLabelDbType,
	)
	SinkDropMessagesTotal = haapm.NewHaCounter(
		"sink_drop_messages_total",
		"Messages not written to storage or dropped on purpose",
		MetricLabelSink,
		MetricLabelDbType,
		MetricLabelReason,
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
		KafkaReadMessagesTotal,
		KafkaReadBytesTotal,
		KafkaWriteErrorsTotal,
		KafkaConsumeDelayMs,
		MySqlWriteDurationMs,
		MySqlWriteMessagesTotal,
		MySqlWriteBytesTotal,
		MySqlReadErrorsTotal,
		MySqlWriteErrorsTotal,
		MySqlBatchWriteDurationMs,
		MySqlWriteBatchSize,
		MySqlDedupDroppedTotal,
		MySqlBatchFallbackTotal,
		MySqlRetryTotal,
		ProbeReceiveMessagesTotal,
		ProbeReceiveBytesTotal,
		ProbeQueueFullTotal,
		SinkWriteDelayMs,
		SinkDropMessagesTotal,
	)
}
