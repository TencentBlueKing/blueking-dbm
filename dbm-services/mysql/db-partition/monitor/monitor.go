// Package monitor TODO
package monitor

import (
	"fmt"
	"net/http"
	"time"

	"dbm-services/mysql/db-partition/util"

	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
)

const cronHeartBeat = "partition_cron_beat"

// PartitionEvent TODO
const PartitionEvent = "partition"

// PartitionDeveloperEvent TODO
const PartitionDeveloperEvent = "partition_dev"

// PartitionCron TODO
const PartitionCron = "partition_cron"

// SendMetric TODO
func SendMetric(serverIp string) {
	l, _ := time.LoadLocation("Local")
	dimension := make(map[string]interface{})
	dimension["bk_cloud_id"] = 0
	dimension["immute_domain"] = PartitionCron
	dimension["server_ip"] = serverIp
	dimension["machine_type"] = PartitionCron

	body := metricsBody{
		commonBody: commonBody{
			DataId:      viper.GetInt("monitor.metric.data_id"),
			AccessToken: viper.GetString("monitor.metric.access_token"),
		},
		Data: []metricsData{
			{
				commonData: commonData{
					Target:    serverIp,
					Timestamp: time.Now().In(l).UnixMilli(),
					Dimension: dimension,
					Metrics: map[string]int{
						cronHeartBeat: 1,
					},
				},
			},
		},
	}
	c := util.NewClientByHosts(viper.GetString("monitor.service"))
	_, err := c.Do(http.MethodPost, "v2/push/", body)
	if err != nil {
		slog.Error("msg", "send partition cron heatbeat metric error", err)
	}
}

// SendEvent TODO
func SendEvent(eventName string, dimension map[string]interface{}, content string, serverIp string) {
	l, _ := time.LoadLocation("Local")

	body := eventBody{
		commonBody: commonBody{
			DataId:      viper.GetInt("monitor.event.data_id"),
			AccessToken: viper.GetString("monitor.event.access_token"),
		},
		Data: []eventData{
			{
				EventName: eventName,
				Event: map[string]interface{}{
					"content": content,
				},
				commonData: commonData{
					Target:    serverIp,
					Timestamp: time.Now().In(l).UnixMilli(),
					Dimension: dimension,
					Metrics:   nil,
				},
			},
		},
	}
	c := util.NewClientByHosts(viper.GetString("monitor.service"))
	_, err := c.Do(http.MethodPost, "v2/push/", body)
	if err != nil {
		slog.Info(fmt.Sprintf("%v", body))
		slog.Error("msg", "send partition event error", err)
	}
}

// NewDeveloperEventDimension TODO
func NewDeveloperEventDimension(serverIp string) map[string]interface{} {
	dimension := make(map[string]interface{})
	dimension["bk_biz_id"] = viper.GetString("dba.bk_biz_id")
	dimension["bk_cloud_id"] = 0
	dimension["immute_domain"] = PartitionCron
	dimension["server_ip"] = serverIp
	dimension["machine_type"] = PartitionCron
	return dimension
}

// NewPartitionEventDimension TODO
func NewPartitionEventDimension(bkBizId int, bkCloudId int, domain string) map[string]interface{} {
	dimension := make(map[string]interface{})
	dimension["bk_biz_id"] = bkBizId
	dimension["bk_biz_id"] = bkBizId
	dimension["bk_cloud_id"] = bkCloudId
	dimension["immute_domain"] = domain
	return dimension
}
