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

package handler

import (
	"fmt"
	"strconv"
	"time"

	"dbm-services/common/dbha-v2/internal/admin/api/open/serializer"
	"dbm-services/common/dbha-v2/internal/admin/ginx"
	"dbm-services/common/dbha-v2/internal/admin/switchlog"

	"github.com/gin-gonic/gin"
)

// SwitchLogHandler switch log handler
type SwitchLogHandler struct {
	switchLogService *switchlog.SwitchLog
}

// NewSwitchLogHandler new switch log handler
func NewSwitchLogHandler(switchLogService *switchlog.SwitchLog) *SwitchLogHandler {
	return &SwitchLogHandler{
		switchLogService: switchLogService,
	}
}

// List lists switchqueue
//
//	@ID			openapi_switchlog_list
//	@Summary	List switch logs
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.switchlog
//	@Param		request	body		serializer.SwitchLogRequest	false	"query parameters"
//	@Success	200		{object}	serializer.SwitchLogListResponse
//	@Router		/api/admin/switchqueue/ [post]
func (h *SwitchLogHandler) List(c *gin.Context) {
	var req serializer.SwitchLogRequest

	if err := c.ShouldBindJSON(&req); err != nil {
		ginx.V1ErrorJSONResponse(c, serializer.RespErr, err)
		return
	}

	bkBizID, err := strconv.Atoi(req.QueryArgs.App)
	if err != nil || bkBizID == 0 {
		ginx.V1ErrorJSONResponse(c, serializer.RespErr, fmt.Errorf("app is not valid"))
		return
	}

	var startTime, finishedTime time.Time
	if req.QueryArgs.SwitchStartTime != "" {
		t, err := time.Parse(time.RFC3339, req.QueryArgs.SwitchStartTime)
		if err != nil {
			ginx.V1ErrorJSONResponse(c, serializer.RespErr, err)
			return
		}
		startTime = t
	}
	if req.QueryArgs.SwitchFinishedTime != "" {
		t, err := time.Parse(time.RFC3339, req.QueryArgs.SwitchFinishedTime)
		if err != nil {
			ginx.V1ErrorJSONResponse(c, serializer.RespErr, err)
			return
		}
		finishedTime = t
	}

	switchSnapshotLogs, _, err := h.switchLogService.ListSwitchSnapshotLogs(
		c.Request.Context(),
		bkBizID,
		startTime,
		finishedTime,
		req.PageArgs.Offset,
		req.PageArgs.Limit,
	)
	if err != nil {
		ginx.V1ErrorJSONResponse(c, serializer.RespErr, err)
		return
	}

	output := serializer.SwitchLogInfoListOutput(switchSnapshotLogs)

	ginx.V1SuccessJSONResponse(c, output, serializer.RespOK, "")
}

// Get gets a switch log info
//
//	@ID			openapi_switchlog_info_list
//	@Summary	Get switch log info
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.switchlog
//	@Param		request	body		serializer.SwitchLogRequest	false	"query parameters"
//	@Success	200		{object}	serializer.SwitchLogInfoListResponse
//	@Router		/api/admin/switchlogs/ [post]
func (h *SwitchLogHandler) Get(c *gin.Context) {
	var req serializer.SwitchLogRequest

	if err := c.ShouldBindJSON(&req); err != nil {
		ginx.V1ErrorJSONResponse(c, serializer.RespErr, err)
		return
	}

	if req.QueryArgs.SwID <= 0 {
		ginx.V1ErrorJSONResponse(c, serializer.RespErr, fmt.Errorf("sw_id is not valid"))
		return
	}
	if req.QueryArgs.IP == "" || req.QueryArgs.Port == 0 {
		ginx.V1ErrorJSONResponse(c, serializer.RespErr, fmt.Errorf("ip or port is not valid"))
		return
	}

	switchSnapshotLogInfo, err := h.switchLogService.GetSwitchSnapshotLogByID(c.Request.Context(), req.QueryArgs.SwID)
	if err != nil {
		ginx.V1ErrorJSONResponse(c, serializer.RespErr, err)
		return
	}
	if switchSnapshotLogInfo == nil {
		ginx.V1ErrorJSONResponse(c, serializer.RespErr, fmt.Errorf("switch log not found, sw_id: %d", req.QueryArgs.SwID))
		return
	}

	switchLogInfos, err := h.switchLogService.ListSwitchLogInfo(
		c.Request.Context(),
		switchSnapshotLogInfo.BkBizID,
		switchSnapshotLogInfo.SwitchID,
		req.QueryArgs.IP,
		req.QueryArgs.Port,
	)
	if err != nil {
		ginx.V1ErrorJSONResponse(c, serializer.RespErr, err)
		return
	}

	output := make(serializer.SwitchLogInfoListResponse, 0)
	loc, _ := time.LoadLocation("Asia/Shanghai")

	for _, info := range switchLogInfos {
		output = append(output, serializer.SwitchLogOutputInfo{
			UID:      info.ID,
			SwID:     req.QueryArgs.SwID,
			App:      strconv.Itoa(info.BkBizID),
			IP:       info.DbIP,
			Port:     info.DbPort,
			Result:   info.Level,
			Datetime: info.CreatedTime.In(loc).Format(serializer.TimeFormat),
			Comment:  info.Content,
		})
	}

	ginx.V1SuccessJSONResponse(c, output, serializer.RespOK, "")
}
