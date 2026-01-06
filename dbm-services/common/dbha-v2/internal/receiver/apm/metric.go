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
	"dbm-services/common/go-pubpkg/apm/metric"
)

var (
	Metrics []*metric.Metric

	KafkaReadMessagesTotal *haapm.HaCounter
	KafkaReadBytesTotal    *haapm.HaCounter
	KafkaWriteErrorsTotal  *haapm.HaCounter

	MySqlWriteLatencyMs     *haapm.HaHistogram
	MySqlWriteMessagesTotal *haapm.HaCounter
	MySqlWriteBytesTotal    *haapm.HaCounter
	MySqlReadErrorsTotal    *haapm.HaCounter
	MySqlWriteErrorsTotal   *haapm.HaCounter
)

func init() {
	// Kafka
	KafkaReadBytesTotal = haapm.NewHaCounter(
		"kafka_read_bytes_total",
		"Total bytes read from Kafka",
		"kafka",
	)
	KafkaReadMessagesTotal = haapm.NewHaCounter(
		"kafka_read_messages_total",
		"Total messages read from Kafka",
		"kafka",
	)
	KafkaWriteErrorsTotal = haapm.NewHaCounter(
		"kafka_write_errors_total",
		"Total errors write to Kafka",
		"kafka",
	)

	// mysql
	MySqlWriteLatencyMs = haapm.NewHaHistogram(
		"mysql_write_latency_ms",
		"Latency of write to mysql (milliseconds)",
		"mysql",
	)
	MySqlWriteMessagesTotal = haapm.NewHaCounter(
		"mysql_write_messages_total",
		"Total messages write to mysql",
		"mysql",
	)
	MySqlWriteBytesTotal = haapm.NewHaCounter(
		"mysql_write_bytes_total",
		"Total bytes write to mysql",
		"mysql",
	)
	MySqlReadErrorsTotal = haapm.NewHaCounter(
		"mysql_read_errors_total",
		"Total errors read from mysql",
		"mysql",
	)
	MySqlWriteErrorsTotal = haapm.NewHaCounter(
		"mysql_write_errors_total",
		"Total errors write to mysql",
		"mysql",
	)
}

// InitAPM init apm
func InitAPM(serviceID, serviceName string) {
	haapm.AppStartupMetric.UpdateLabel(map[string]string{
		haapm.MetricLabelServiceID:   serviceID,
		haapm.MetricLabelServiceName: serviceName,
	})

	Metrics = append(Metrics, haapm.AppStartupMetric.ToMetric())

	// Kafka
	Metrics = append(Metrics, KafkaReadMessagesTotal.ToMetric())
	Metrics = append(Metrics, KafkaReadBytesTotal.ToMetric())
	Metrics = append(Metrics, KafkaWriteErrorsTotal.ToMetric())

	// mysql
	Metrics = append(Metrics, MySqlWriteLatencyMs.ToMetric())
	Metrics = append(Metrics, MySqlWriteMessagesTotal.ToMetric())
	Metrics = append(Metrics, MySqlWriteBytesTotal.ToMetric())
	Metrics = append(Metrics, MySqlReadErrorsTotal.ToMetric())
	Metrics = append(Metrics, MySqlWriteErrorsTotal.ToMetric())
}
