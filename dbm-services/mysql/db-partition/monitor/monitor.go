// Package monitor TODO
package monitor

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
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

// SendEvent 发送自定义监控事件
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
		// 监控无法上报，如果服务异常无法上报监控，所以让服务退出，可触发服务故障的告警。
		InitMonitor()
	}
}

// NewDeveloperEventDimension 构建自定监控事件的维度，发送给平台管理员
func NewDeveloperEventDimension(serverIp string) map[string]interface{} {
	dimension := make(map[string]interface{})
	dimension["bk_biz_id"] = viper.GetString("dba.bk_biz_id")
	dimension["bk_cloud_id"] = 0
	dimension["cluster_domain"] = PartitionCron
	dimension["server_ip"] = serverIp
	dimension["machine_type"] = PartitionCron
	return dimension
}

// NewPartitionEventDimension 构建自定监控事件的维度，发送给业务的dba
func NewPartitionEventDimension(bkBizId int, bkCloudId int, domain string) map[string]interface{} {
	dimension := make(map[string]interface{})
	dimension["bk_biz_id"] = bkBizId
	dimension["bk_cloud_id"] = bkCloudId
	dimension["cluster_domain"] = domain
	return dimension
}

// TestSendEvent 测试监控上报链路
func TestSendEvent(dataId int, token string, serviceHost string) error {
	dimension := NewDeveloperEventDimension("0.0.0.0")
	l, _ := time.LoadLocation("Local")

	body := eventBody{
		commonBody: commonBody{
			DataId:      dataId,
			AccessToken: token,
		},
		Data: []eventData{
			{
				EventName: PartitionDeveloperEvent,
				Event: map[string]interface{}{
					"content": "test partition monitor",
				},
				commonData: commonData{
					Target:    "0.0.0.0",
					Timestamp: time.Now().In(l).UnixMilli(),
					Dimension: dimension,
					Metrics:   nil,
				},
			},
		},
	}
	c := util.NewClientByHosts(serviceHost)
	_, err := c.Do(http.MethodPost, "", body)
	if err != nil {
		slog.Info(fmt.Sprintf("%v", body))
		slog.Error("msg", "send partition event error", err)
		return err
	}
	return nil
}

// GetMonitorSetting 获取监控配置，并测试验证上报链路
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
	if setting.MonitorService == "" || setting.MonitorService == "127.0.0.1" || setting.MonitorEventDataID == 0 ||
		setting.MonitorEventAccessToken == "" {
		slog.Error("msg", "settings have null or default value", setting)
		return setting, fmt.Errorf("settings have null or default value")
	}
	// 测试配置是否可以连通
	err = TestSendEvent(setting.MonitorEventDataID, setting.MonitorEventAccessToken, setting.MonitorService)
	if err != nil {
		slog.Error("msg", "test send event setting", setting, "error", err)
		return setting, fmt.Errorf("test send event setting error: %s", err.Error())
	}
	return setting, nil
}

// InitMonitor 多次尝试获取监控配置，更新配置；获取失败退出
func InitMonitor() {
	i := 1
	for ; i <= 10; i++ {
		setting, err := GetMonitorSetting()
		if err != nil {
			slog.Error(fmt.Sprintf("try %d time", i), "get monitor setting error", err)
			if i == 10 {
				slog.Error("try too many times")
				os.Exit(0)
			}
			time.Sleep(3 * time.Second)
		} else {
			slog.Info("msg", "monitor setting", setting)
			viper.Set("monitor.service", setting.MonitorService)
			// 蓝鲸监控自定义事件
			viper.Set("monitor.event.data_id", setting.MonitorEventDataID)
			viper.Set("monitor.event.access_token", setting.MonitorEventAccessToken)
			break
		}
	}
}
