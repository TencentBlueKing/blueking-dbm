/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package manage

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// GetOperationInfoParam TODO
type GetOperationInfoParam struct {
	OperationType string   `json:"operation_type"`
	BillIds       []string `json:"bill_ids"`
	BillTypes     []string `json:"bill_types"`
	TaskIds       []string `json:"task_ids"`
	IpList        []string `json:"ip_list"`
	Operator      string   `json:"operator"`
	BeginTime     string   `json:"begin_time"  binding:"omitempty,datetime=2006-01-02 15:04:05" `
	EndTime       string   `json:"end_time"  binding:"omitempty,datetime=2006-01-02 15:04:05"`
	Orderby       string   `json:"orderby"`
	Limit         int      `json:"limit"`
	Offset        int      `json:"offset"`
}

// OperationInfoList TODO
func (o MachineResourceHandler) OperationInfoList(r *gin.Context) {
	var input GetOperationInfoParam
	requestId := r.GetString("request_id")
	if err := o.Prepare(r, &input); err != nil {
		logger.Error(fmt.Sprintf("Preare Error %s", err.Error()))
		return
	}
	db := model.DB.Self.Table(model.TbRpOperationInfoTableName())
	input.query(db)
	var count int64
	if err := db.Count(&count).Error; err != nil {
		o.SendResponse(r, errno.ErrDBQuery.AddErr(err), requestId, err.Error())
		return
	}
	var data []model.TbRpOperationInfo
	if input.Limit > 0 {
		db = db.Offset(input.Offset).Limit(input.Limit)
	}
	if err := db.Scan(&data).Error; err != nil {
		o.SendResponse(r, errno.ErrDBQuery.AddErr(err), err.Error(), requestId)
		return
	}

	o.SendResponse(r, nil, map[string]interface{}{"details": data, "count": count}, requestId)
}

func (p GetOperationInfoParam) query(db *gorm.DB) {
	if len(p.IpList) > 0 {
		for _, ip := range p.IpList {
			db.Or(model.JSONQuery("ip_list").Contains([]string{ip}))
		}
		return
	}
	if len(p.BillIds) > 0 {
		db.Where("bill_id in (?)", p.BillIds)
	}
	if len(p.BillTypes) > 0 {
		db.Where("bill_type in (?)", p.BillTypes)
	}
	if len(p.TaskIds) > 0 {
		db.Where("task_id in (?)", p.TaskIds)
	}
	if cmutil.IsNotEmpty(p.Operator) {
		db.Where("operator = ?", p.Operator)
	}
	if cmutil.IsNotEmpty(p.OperationType) {
		db.Where("operation_type = ? ", p.OperationType)
	}
	if cmutil.IsNotEmpty(p.EndTime) {
		db.Where("create_time <= ? ", p.EndTime)
	}
	if cmutil.IsNotEmpty(p.BeginTime) {
		db.Where("create_time >= ? ", p.BeginTime)
	}
	switch strings.ToLower(strings.TrimSpace(p.Orderby)) {
	case "asc":
		db.Order("create_time asc")
	default:
		db.Order("create_time desc")
	}
}

// CreateOperationParam 提前导入记录
type CreateOperationParam struct {
	TaskId   string     `json:"task_id"`
	Operator string     `json:"operator"`
	Hosts    []HostBase `json:"hosts" binding:"gt=0,dive,required"`
}

// RecordImportResource TODO
func (o MachineResourceHandler) RecordImportResource(r *gin.Context) {
	var input CreateOperationParam
	if err := o.Prepare(r, &input); err != nil {
		logger.Error(fmt.Sprintf("Preare Error %s", err.Error()))
		return
	}
	var ipList []string
	var hostIdList []int
	for _, v := range input.Hosts {
		if !cmutil.IsEmpty(v.Ip) {
			ipList = append(ipList, v.Ip)
		}
		if v.HostId > 0 {
			hostIdList = append(hostIdList, v.HostId)
		}
	}
	ipJsStr, err := json.Marshal(ipList)
	if err != nil {
		o.SendResponse(r, errno.ErrJSONMarshal.Add("input ips"), "failed", "")
		return
	}
	bkHostIdJsStr, err := json.Marshal(hostIdList)
	if err != nil {
		o.SendResponse(r, errno.ErrJSONMarshal.Add("input hostids"), "failed", "")
	}
	m := model.TbRpOperationInfo{
		TotalCount:    len(ipList),
		BkHostIds:     bkHostIdJsStr,
		OperationType: model.Imported,
		IpList:        ipJsStr,
		Operator:      input.Operator,
		TaskId:        input.TaskId,
		UpdateTime:    time.Now(),
		CreateTime:    time.Now(),
	}
	if err := model.DB.Self.Table(model.TbRpOperationInfoTableName()).Create(&m).Error; err != nil {
		o.SendResponse(r, fmt.Errorf("记录导入任务日志失败,%w", err), err.Error(), "")
	}
	o.SendResponse(r, nil, "记录日志成功", "")
	return
}
