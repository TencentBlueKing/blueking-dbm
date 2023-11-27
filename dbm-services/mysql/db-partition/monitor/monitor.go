// Package monitor TODO
package monitor

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"time"

	"dbm-services/mysql/db-partition/util"

	"github.com/spf13/viper"
)

// PartitionEvent TODO
const PartitionEvent = "partition"

// PartitionDeveloperEvent TODO
const PartitionDeveloperEvent = "partition_dev"

// PartitionCron TODO
const PartitionCron = "partition_cron"

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
	_, err := c.Do(http.MethodPost, "", body)
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
	dimension["cluster_domain"] = PartitionCron
	dimension["server_ip"] = serverIp
	dimension["machine_type"] = PartitionCron
	return dimension
}

// NewPartitionEventDimension TODO
func NewPartitionEventDimension(bkBizId int, bkCloudId int, domain string) map[string]interface{} {
	dimension := make(map[string]interface{})
	dimension["bk_biz_id"] = bkBizId
	dimension["bk_cloud_id"] = bkCloudId
	dimension["cluster_domain"] = domain
	return dimension
}

func GetMonitorSetting() (Setting, error) {
	var setting Setting
	c := util.NewClientByHosts(viper.GetString("dbm_ticket_service"))
	result, err := c.Do(http.MethodGet, "conf/system_settings/sensitive_environ/", nil)
	if err != nil {
		slog.Error("msg", "get monitor setting error", err)
		return setting, err
	}
	if err = json.Unmarshal(result.Data, &setting); err != nil {
		return setting, err
	}
	if setting.MonitorService == "" || setting.MonitorEventDataID == 0 ||
		setting.MonitorMetricDataID == 0 || setting.MonitorEventAccessToken == "" ||
		setting.MonitorMetricAccessToken == "" {
		slog.Error("msg", "settings have null value:", setting)
		return setting, fmt.Errorf("settings have null value")
	}
	return setting, nil
}
