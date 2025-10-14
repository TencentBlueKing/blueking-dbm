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

package monitor

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os/exec"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"golang.org/x/net/context"
)

var (
	agentEndpoint string
	accessToken   string
	bkMonitorBeat string
	dataID        uint64 = 0
	reporterType  string = "agent"
	reporterKind  string = "event"
)

// Event monitor's event
type Event struct {
	DataID      uint64       `json:"data_id"`
	AccessToken string       `json:"access_token"`
	Data        []*EventData `json:"data"`
}

type EventData struct {
	Name   string `json:"event_name"`
	Target string `json:"target"`

	// Precise to the millisecond.
	Timestamp uint64 `json:"timestamp,omitempty"`

	Content struct {
		Content string `json:"content"`
	} `json:"event"`

	Dimension struct {
		// Added in v2
		BkCloudID         int                            `json:"bk_cloud_id,omitempty"`
		IP                string                         `json:"ip,omitempty"`
		Port              int                            `json:"port,omitempty"`
		BkBizID           int                            `json:"bk_biz_id,omitempty"`
		DbClusterType     hamodel.DbmMetadataClusterType `json:"dbm_cluster_type,omitempty"`
		DbMachineType     hamodel.DbmMetadataMachineType `json:"dbm_machine_type,omitempty"`
		DbTypeName        haprobe.DbType                 `json:"db_type_name,omitempty"`
		DbEventName       haprobe.DbEventName            `json:"db_event_name,omitempty"`
		DbEventNameReason haprobe.DbEventNameReason      `json:"db_event_name_reason,omitempty"`

		// Compatible with V1.
		SwitchInfoBkBizIdV1       string `json:"appid,omitempty"`
		SwitchInfoServerIpV1      string `json:"server_ip,omitempty"`
		SwitchInfoServerPortV1    int    `json:"server_port,omitempty"`
		SwitchInfoStatusV1        string `json:"status,omitempty"`
		SwitchInfoClusterDomainV1 string `json:"cluster_domain,omitempty"`
		SwitchInfoMachineTypeV1   string `json:"machine_type,omitempty"`

		// switch info.
		SwitchInfoInstanceRoleV1      string `json:"instance_role,omitempty"`
		SwitchInfoIdcV1               string `json:"idc,omitempty"`
		SwitchInfoCheckIdV1           string `json:"double_check_id,omitempty"`
		SwitchInfoNewMasterBinlogFile string `json:"new_master_binlog_file,omitempty"`
		SwitchInfoNewMasterBinlogPos  uint64 `json:"new_master_binlog_pos,omitempty"`
		SwitchInfoNewMasterHost       string `json:"new_master_host,omitempty"`
		SwitchInfoNewMasterPort       int    `json:"new_master_port,omitempty"`

		// switch detect info.
		SwitchInfoDetectClusterType string `json:"cluster_type,omitempty"`

		// global switch info.
		SwitchInfoGlobalUncoveredInsNum  int    `json:"uncovered_ins_num,omitempty"`
		SwitchInfoGlobalNeedDetectNum    int    `json:"need_detect_num,omitempty"`
		SwitchInfoGlobalHaDetectNum      int    `json:"ha_detect_num,omitempty"`
		SwitchInfoGlobalUncoveredCityIDs string `json:"uncovered_city_ids,omitempty"` // joined with ','

		// API info.
		SwitchInfoApiName    string `json:"api_name,omitempty"`
		SwitchInfoApiMessage string `json:"api_message,omitempty"`
	} `json:"dimension"`
}

func SetEndpoint(epoint string) {
	agentEndpoint = epoint
}

func SetAccessToken(token string) {
	accessToken = token
}

func SetBkMonitorBeat(beatPath string) {
	bkMonitorBeat = beatPath
}

func SetDataID(id uint64) {
	dataID = id
}

func SetReportType(rtype string) {
	reporterType = rtype
}

func SetReporterKind(rkind string) {
	reporterKind = rkind
}

func PostBKMonitor(timeout time.Duration, edatas ...*EventData) error {
	if dataID == 0 {
		return gerrors.Newf(gerrors.InvalidParameter, "invalid data id(%d)", dataID)
	}

	if agentEndpoint == "" {
		return gerrors.Newf(gerrors.InvalidParameter, "invalid agent endpoint(%s)", agentEndpoint)
	}

	if timeout < 5*time.Second {
		timeout = 5 * time.Second
	}

	if len(edatas) == 0 {
		return gerrors.New(gerrors.InvalidParameter, "not set any event data")
	}

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	event := &Event{
		DataID:      dataID,
		AccessToken: accessToken,
	}

	for _, data := range edatas {
		if data == nil {
			logger.Warn("invalid event data(nil), data id(%d)", dataID)
			continue
		}
		event.Data = append(event.Data, data)
	}

	if len(event.Data) == 0 {
		logger.Error("invalid event data(nil), data id(%d)", dataID)
		return gerrors.New(gerrors.InvalidParameter, "not set any event data")
	}

	datas, err := json.Marshal(event)
	if err != nil {
		return gerrors.Newf(gerrors.BkMonitorFailure, "marshal event data failed, %v", err)
	}

	cmd := exec.CommandContext(ctx, bkMonitorBeat, []string{
		"-report",
		"-report.type", reporterType,
		"-report.message.kind", reporterKind,
		"-report.bk_data_id", fmt.Sprintf("%d", dataID),
		"-report.agent.address", agentEndpoint,
		"-report.message.body", string(datas),
	}...)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err = cmd.Run(); err != nil {
		logger.Error("post bkmonitor event failed, stdout(%s), stderr(%s), %v", stdout.String(), stderr.String(), err)
		return gerrors.Newf(gerrors.BkMonitorFailure, "post bkmonitor event failed, %v", err)
	}

	return nil
}
