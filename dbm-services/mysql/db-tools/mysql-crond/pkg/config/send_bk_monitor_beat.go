package config

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log/slog"
	"os/exec"
	"strconv"
	"time"
)

type commonData struct {
	Target    string                 `json:"target"`
	Timestamp int64                  `json:"timestamp"`
	Dimension map[string]interface{} `json:"dimension"`
	Metrics   map[string]int64       `json:"metrics"`
}

type eventData struct {
	EventName string                 `json:"event_name"`
	Event     map[string]interface{} `json:"event"`
	commonData
}

type metricsData struct {
	commonData
}

type commonBody struct {
	DataId      int    `json:"bk_data_id"`
	AccessToken string `json:"access_token"`
}

type eventBody struct {
	commonBody
	Data []eventData `json:"data"`
}

type metricsBody struct {
	commonBody
	Data []metricsData `json:"data"`
}

// SendBkMonitorBeat TODO
func SendBkMonitorBeat(
	dataId int, reportType string,
	messageKind string, body interface{},
) error {
	output, err := json.Marshal(body)
	if err != nil {
		slog.Error(
			"send bk monitor heart beat encode body",
			slog.String("error", err.Error()),
			slog.Any("body", body),
		)
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
	slog.Info("send bk monitor", slog.String("command", cmd.String()))
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err = cmd.Run()
	if err != nil {
		slog.Error(
			"send bk monitor beat",
			slog.String("error", err.Error()),
			slog.String("std out", stdout.String()),
			slog.String("std err", stderr.String()),
		)
		return err
	}

	return nil
}

// SendEvent TODO
func SendEvent(name string, content string, additionDimension map[string]interface{}) error {
	l, _ := time.LoadLocation("Local")

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
					Timestamp: time.Now().In(l).UnixMilli(),
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
		slog.Error("send event", slog.String("error", err.Error()))
		return err
	}

	return nil
}

// SendMetrics TODO
func SendMetrics(mKey string, mValue int64, additionDimension map[string]interface{}) error {
	l, _ := time.LoadLocation("Local")

	body := metricsBody{
		commonBody: commonBody{
			DataId:      RuntimeConfig.BkMonitorBeat.CustomMetrics.BkDataId,
			AccessToken: RuntimeConfig.BkMonitorBeat.CustomMetrics.AccessToken,
		},
		Data: []metricsData{
			{
				commonData: commonData{
					Target:    RuntimeConfig.Ip,
					Timestamp: time.Now().In(l).UnixMilli(),
					Dimension: buildDimension(additionDimension),
					Metrics: map[string]int64{
						mKey: mValue,
					},
				},
			},
		},
	}

	err := SendBkMonitorBeat(
		RuntimeConfig.BkMonitorBeat.CustomMetrics.BkDataId,
		RuntimeConfig.BkMonitorBeat.CustomMetrics.ReportType,
		RuntimeConfig.BkMonitorBeat.CustomMetrics.MessageKind,
		body,
	)

	if err != nil {
		slog.Error("send event", slog.String("error", err.Error()))
		return err
	}

	return nil
}

func buildDimension(addition map[string]interface{}) map[string]interface{} {
	dimension := make(map[string]interface{})
	dimension["bk_biz_id"] = strconv.Itoa(JobsConfig.BkBizId)
	dimension["appid"] = strconv.Itoa(JobsConfig.BkBizId)
	dimension["bk_cloud_id"] = strconv.Itoa(*RuntimeConfig.BkCloudID)
	dimension["server_ip"] = RuntimeConfig.Ip
	dimension["bk_target_ip"] = RuntimeConfig.Ip

	// dimension["immute_domain"] = JobsConfig.ImmuteDomain
	// dimension["machine_type"] = JobsConfig.MachineType
	//
	// if JobsConfig.Role != nil {
	//	dimension["role"] = *JobsConfig.Role
	// }

	for k, v := range addition {
		dimension[k] = v
	}

	return dimension
}
