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

package serializer

import (
	"fmt"
	"strconv"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

const (
	RespOK  = 0
	RespErr = 1

	// SwitchVersionV2 Used to distinguish v2 switch log api.
	SwitchVersionV2 = "v2"

	TimeFormat = "2006-01-02T15:04:05-07:00"
)

// QueryPage query page
type QueryPage struct {
	Limit  int `json:"limit"`
	Offset int `json:"offset"`
}

// QueryArgs query args
type QueryArgs struct {
	App                string `json:"app"`
	SwID               int    `json:"sw_id"`
	IP                 string `json:"ip"`
	Port               int    `json:"port"`
	SwitchStartTime    string `json:"switch_start_time"`
	SwitchFinishedTime string `json:"switch_finished_time"`
}

// SwitchLogRequest switch log request
type SwitchLogRequest struct {
	// query args from request.body
	QueryArgs QueryArgs `json:"query_args"`
	// query limit
	PageArgs QueryPage `json:"page_args"`
}

// SwitchLogListResponse switch log list response
type SwitchLogListResponse []SwitchLogListOutputInfo

// SwitchLogListOutputInfo switch log list output info
type SwitchLogListOutputInfo struct {
	UID                uint   `json:"uid"`
	IP                 string `json:"ip"`
	Port               int    `json:"port"`
	ConfirmCheckTime   string `json:"confirm_check_time"`
	DbRole             string `json:"db_role"`
	Status             string `json:"status"`
	SlaveIP            string `json:"slave_ip"`
	SlavePort          int    `json:"slave_port"`
	ConfirmResult      string `json:"confirm_result"`
	SwitchResult       string `json:"switch_result"`
	Remark             string `json:"remark"`
	App                string `json:"app"`
	DbType             string `json:"db_type"`
	IdcID              int    `json:"idc_id"`
	CloudID            int    `json:"cloud_id"`
	Cluster            string `json:"cluster"`
	SwitchStartTime    string `json:"switch_start_time"`
	SwitchFinishedTime string `json:"switch_finished_time"`
	SwitchVersion      string `json:"switch_version"`
}

// SwitchLogInfoListResponse switch log info list response
type SwitchLogInfoListResponse []SwitchLogOutputInfo

// SwitchLogOutputInfo switch log output info
type SwitchLogOutputInfo struct {
	UID      uint   `json:"uid"`
	SwID     int    `json:"sw_id"`
	App      string `json:"app"`
	IP       string `json:"ip"`
	Result   string `json:"result"`
	Datetime string `json:"datetime"`
	Comment  string `json:"comment"`
	Port     int    `json:"port"`
}

// SwitchLogInfoListOutput switch log info list output
func SwitchLogInfoListOutput(switchSnapshotLogs []*hamodel.DbSwitchingSnapshotLog) SwitchLogListResponse {
	res := make(SwitchLogListResponse, 0)
	loc, _ := time.LoadLocation("Asia/Shanghai")

	switchLogCheckTime := map[string]string{}
	for _, switchLog := range switchSnapshotLogs {
		if !switchLog.Instances.Valid {
			continue
		}

		var switchStartTime string
		var switchFinishTime string

		if switchLog.StartTime != nil {
			switchStartTime = switchLog.StartTime.In(loc).Format(TimeFormat)
		} else {
			switchStartTime = time.Now().In(loc).Format(TimeFormat)
		}

		if switchLog.FinishedTime != nil {
			switchFinishTime = switchLog.FinishedTime.In(loc).Format(TimeFormat)
		} else {
			switchFinishTime = time.Now().In(loc).Format(TimeFormat)
		}

		for _, instance := range switchLog.Instances.Data {
			var checkStartTime string
			if instance.CheckStartTime != nil {
				checkStartTime = instance.CheckStartTime.In(loc).Format(TimeFormat)
				k := fmt.Sprintf("%d:%s", switchLog.ID, instance.IP)
				switchLogCheckTime[k] = checkStartTime
			}

			res = append(res, SwitchLogListOutputInfo{
				UID:                switchLog.ID,
				IP:                 instance.IP,
				Port:               instance.Port,
				DbType:             instance.MachineType,
				DbRole:             instance.InstanceRole,
				SlaveIP:            instance.NewMasterIP,
				SlavePort:          instance.NewMasterPort,
				IdcID:              instance.BkIdcID,
				ConfirmCheckTime:   checkStartTime,
				ConfirmResult:      switchLog.Reason,
				Remark:             "",
				App:                strconv.Itoa(switchLog.BkBizID),
				CloudID:            switchLog.BkCloudID,
				Cluster:            instance.ClusterName,
				SwitchResult:       switchLog.Result,
				SwitchStartTime:    switchStartTime,
				SwitchFinishedTime: switchFinishTime,
				Status:             switchLog.Status.String(),
				SwitchVersion:      SwitchVersionV2,
			})
		}
	}

	// Backfill the check time for records of the same switch request sharing the same IP
	// but different ports; fall back to the switch start time if none is available.
	for i := range res {
		if res[i].ConfirmCheckTime != "" {
			continue
		}

		k := fmt.Sprintf("%d:%s", res[i].UID, res[i].IP)
		if checkTime, ok := switchLogCheckTime[k]; ok {
			res[i].ConfirmCheckTime = checkTime
		} else {
			res[i].ConfirmCheckTime = res[i].SwitchStartTime
		}
	}

	return res
}
