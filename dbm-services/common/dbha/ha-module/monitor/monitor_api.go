package monitor

import (
	"bytes"
	"dbm-services/common/dbha/ha-module/log"
	"encoding/json"
	"fmt"
	"os/exec"
	"time"
)

// bkCustom struct of bk monitor information
type bkCustom struct {
	BkDataId    int    `yaml:"bk_data_id" validate:"required"`
	AccessToken string `yaml:"access_token" validate:"required"`
	ReportType  string `yaml:"report_type" validate:"required"`
	MessageKind string `yaml:"message_kind" validate:"required"`
}

// BkMonitorBeat information of bkmonitorbeat tool
type BkMonitorBeat struct {
	CustomMetrics    bkCustom `yaml:"custom_metrics" validate:"required"`
	CustomEvent      bkCustom `yaml:"custom_event" validate:"required"`
	InnerEventName   string   `yaml:"inner_event_name" validate:"required"`
	InnerMetricsName string   `yaml:"inner_metrics_name" validate:"required"`
	BeatPath         string   `yaml:"beat_path" validate:"required,file"`
	AgentAddress     string   `yaml:"agent_address" validate:"required,file"`
}

// runtimeConfig the runtime struct of monitor
type runtimeConfig struct {
	Ip            string        `yaml:"ip" validate:"required,ipv4"`
	BkCloudID     int           `yaml:"bk_cloud_id" validate:"required,gte=0"`
	BkMonitorBeat BkMonitorBeat `yaml:"bk_monitor_beat" validate:"required"`
}

// commonData the common data of bk monitor message
type commonData struct {
	Target    string                 `json:"target"`
	Timestamp int64                  `json:"timestamp"`
	Dimension map[string]interface{} `json:"dimension"`
	Metrics   map[string]int         `json:"metrics"`
}

// eventData the event data of bk monitor message
type eventData struct {
	EventName string                 `json:"event_name"`
	Event     map[string]interface{} `json:"event"`
	commonData
}

// commonBody the common body of bk monitor message
type commonBody struct {
	DataId      int    `json:"bk_data_id"`
	AccessToken string `json:"access_token"`
}

// eventBody the event body of bk monitor message
type eventBody struct {
	commonBody
	Data []eventData `json:"data"`
}

// buildDimension asemble dimension of monitor messsage
func buildDimension(addition map[string]interface{}) map[string]interface{} {
	dimension := make(map[string]interface{})
	dimension["bk_cloud_id"] = RuntimeConfig.BkCloudID

	for k, v := range addition {
		dimension[k] = v
	}

	return dimension
}

// SendBkMonitorBeat send bk monitor message
func SendBkMonitorBeat(
	dataId int, reportType string,
	messageKind string, body interface{},
) error {
	output, err := json.Marshal(body)
	if err != nil {
		log.Logger.Errorf("send bk monitor heart beat encode body, err:%s,body:%v",
			err.Error(), body)
		return err
	}

	cmd := exec.Command(
		RuntimeConfig.BkMonitorBeat.BeatPath, []string{
			"-report",
			"-report.bk_data_id", fmt.Sprintf("%d", dataId),
			"-report.type", reportType,
			"-report.message.kind", messageKind,
			"-report.agent.address", RuntimeConfig.BkMonitorBeat.AgentAddress,
			"-report.message.body", string(output),
		}...,
	)
	log.Logger.Infof("send bk monitor, command=%s", cmd.String())
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err = cmd.Run()
	if err != nil {
		log.Logger.Errorf("send bk monitor beat failed, err:%s, stdout:%s, stderr:%s",
			err.Error(), stdout.String(), stderr.String())
		return err
	}

	return nil
}

// SendEvent send bk montor event
func SendEvent(name string, content string, additionDimension map[string]interface{}) error {
	ts := time.Now().UnixNano() / (1000 * 1000)
	body := eventBody{
		commonBody: commonBody{
			DataId:      RuntimeConfig.BkMonitorBeat.CustomEvent.BkDataId,
			AccessToken: RuntimeConfig.BkMonitorBeat.CustomEvent.AccessToken,
		},
		Data: []eventData{
			{
				EventName: name, // RuntimeConfig.BkMonitorBeat.CustomEvent.Name,
				Event: map[string]interface{}{
					"content": content,
				},
				commonData: commonData{
					Target:    RuntimeConfig.Ip,
					Timestamp: ts,
					Dimension: buildDimension(additionDimension),
					Metrics:   nil,
				},
			},
		},
	}

	err := SendBkMonitorBeat(
		RuntimeConfig.BkMonitorBeat.CustomEvent.BkDataId,
		RuntimeConfig.BkMonitorBeat.CustomEvent.ReportType,
		RuntimeConfig.BkMonitorBeat.CustomEvent.MessageKind,
		body,
	)
	if err != nil {
		log.Logger.Errorf("send event failed, err:%s", err.Error())
		return err
	}

	return nil
}

// RuntimeConfig TODO
var RuntimeConfig *runtimeConfig

// RuntimeConfigInit init monitor
func RuntimeConfigInit(
	targetIp string, bkDataId int, accessToken string, bkCloudId string,
	reportType string, msgKind string, beatPath string, agentAddress string,
) {
	RuntimeConfig = &runtimeConfig{}
	RuntimeConfig.Ip = targetIp

	bkMonitorBeat := BkMonitorBeat{
		CustomEvent: bkCustom{
			BkDataId:    bkDataId,
			AccessToken: accessToken,
			ReportType:  reportType,
			MessageKind: msgKind,
		},
		BeatPath:     beatPath,
		AgentAddress: agentAddress,
	}

	RuntimeConfig.BkMonitorBeat = bkMonitorBeat
	return
}
