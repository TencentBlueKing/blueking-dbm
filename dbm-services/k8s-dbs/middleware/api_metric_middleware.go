/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package middleware

import (
	"bytes"
	"encoding/json"
	commapi "k8s-dbs/common/api"
	commconst "k8s-dbs/common/constant"
	dbsmetrics "k8s-dbs/metric"
	"log/slog"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
)

// IgnoreAPINames 忽略指标上报的接口列表
var IgnoreAPINames = map[string]bool{
	commconst.APIHealth: true,
}

// APIMetricsMiddleware 收集 API 请求的指标数据并上报
func APIMetricsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		basicMetricTags := dbsmetrics.BaseMetricTags{}
		// 记录请求开始时间
		start := time.Now()

		// 设置用户标签
		if err := setAPISourceTags(c, &basicMetricTags); err != nil {
			slog.Warn("用户标签设置失败", "error", err.Error())
			return
		}

		// 劫持 ResponseWriter 以捕获响应内容
		writer := &DbsResponseWriter{
			body:           bytes.NewBufferString(""),
			ResponseWriter: c.Writer,
		}
		c.Writer = writer

		// 执行业务逻辑
		c.Next()

		// 过滤不需要指标上报的接口
		if skip := shouldSkipAPI(c); skip {
			return
		}

		// 设置基础标签
		setAPIBasicTags(c, &basicMetricTags)

		// 设置响应标签
		if err := setAPIResponseTags(writer, &basicMetricTags); err != nil {
			slog.Warn("响应标签设置失败", "error", err.Error())
			return
		}

		// 指标上报
		reportAPIMetrics(&basicMetricTags, start)
	}
}

// reportAPIMetrics api 指标上报
func reportAPIMetrics(basicMetricTags *dbsmetrics.BaseMetricTags, start time.Time) {
	// http api 通用计数指标上报
	dbsmetrics.HTTPAPITotalCounter.WithLabelValues(
		basicMetricTags.APIName,
		basicMetricTags.Method,
		basicMetricTags.Status,
		basicMetricTags.BkUserName,
		basicMetricTags.BkAppCode,
		basicMetricTags.ResultCode,
		basicMetricTags.Result,
	).Inc()

	// http api 通用时延指标上报
	dbsmetrics.HTTPAPIDurationHistogram.WithLabelValues(
		basicMetricTags.APIName,
		basicMetricTags.Method,
		basicMetricTags.Status,
		basicMetricTags.BkUserName,
		basicMetricTags.BkAppCode,
		basicMetricTags.ResultCode,
		basicMetricTags.Result,
	).Observe(time.Since(start).Seconds())
}

// setAPIBasicTags 设置 API 基础标签
func setAPIBasicTags(c *gin.Context, basicMetricTags *dbsmetrics.BaseMetricTags) {
	basicMetricTags.APIName = c.GetString(commconst.APIName)
	basicMetricTags.Method = c.Request.Method
	basicMetricTags.Status = strconv.Itoa(c.Writer.Status())
}

// setAPIResponseTags 设置 API 响应相关标签
func setAPIResponseTags(
	writer *DbsResponseWriter,
	metricTags *dbsmetrics.BaseMetricTags,
) error {
	// 处理返回参数
	resBody := writer.body.Bytes()
	var response commapi.Response
	if err := json.Unmarshal(resBody, &response); err != nil {
		slog.Error("返回消息体反序列化失败", "err", err)
		return err
	}

	// 获取返回码和请求处理结果
	metricTags.ResultCode = strconv.Itoa(int(response.Code))
	metricTags.Result = strconv.FormatBool(response.Result)
	return nil
}

// shouldSkip 是否忽略指标上报
func shouldSkipAPI(c *gin.Context) bool {
	apiName := c.GetString(commconst.APIName)
	if apiName == "" || IgnoreAPINames[apiName] {
		slog.Warn("当前接口不需要进行指标统计", "接口名称", apiName)
		return true
	}
	return false
}

// setAPISourceTags 设置 API Source 标签
func setAPISourceTags(c *gin.Context, metricTags *dbsmetrics.BaseMetricTags) error {
	reqBody := ParseReqBody(c)
	if c.Request.Method == http.MethodGet {
		metricTags.BkUserName = c.Query("bk_username")
		metricTags.BkAppCode = c.Query("bk_app_code")
	} else {
		var reqMap = make(map[string]any)
		if err := json.Unmarshal(reqBody, &reqMap); err != nil {
			slog.Error("请求消息体参数反序列化失败", "reqBody", string(reqBody), "err", err)
			return err
		}
		metricTags.BkUserName = getBkUserName(reqMap)
		metricTags.BkAppCode = getBkAppCode(reqMap)
	}
	return nil
}

// getBkAppCode 获取 appCode
func getBkAppCode(reqMap map[string]any) (s string) {
	if bkAppCodeVal, ok := reqMap["bk_app_code"]; ok {
		if bkAppCodeStr, ok := bkAppCodeVal.(string); ok {
			return bkAppCodeStr
		}
	}
	return
}

// getBkUserName 获取用户名
func getBkUserName(reqMap map[string]any) (s string) {
	if bkUserNameVal, ok := reqMap["bk_username"]; ok {
		if bkUserNameStr, ok := bkUserNameVal.(string); ok {
			return bkUserNameStr
		}
	}
	return
}
