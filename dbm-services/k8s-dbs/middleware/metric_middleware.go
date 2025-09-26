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

// MetricsMiddleware 指标上报中间件
func MetricsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// 记录请求开始时间
		start := time.Now()
		// 劫持 ResponseWriter 以捕获响应内容
		writer := &DbsResponseWriter{
			body:           bytes.NewBufferString(""),
			ResponseWriter: c.Writer,
		}
		c.Writer = writer

		// 执行业务逻辑
		c.Next()

		// 过滤不需要指标上报的接口
		if skip := shouldSkip(c); skip {
			return
		}

		basicMetricTags := dbsmetrics.BaseMetricTags{}
		// 设置标签
		if err := setMetricTags(c, &basicMetricTags, writer); err != nil {
			return
		}

		// 指标上报
		reportAPIMetrics(&basicMetricTags, start)
	}
}

func setMetricTags(
	c *gin.Context,
	basicMetricTags *dbsmetrics.BaseMetricTags,
	writer *DbsResponseWriter,
) error {
	// 设置基础标签
	setBasicTags(c, basicMetricTags)

	// 设置用户标签
	if err := setUserInfoTags(c, basicMetricTags); err != nil {
		slog.Warn("用户标签设置失败", "error", err.Error())
		return err
	}

	// 设置返回标签
	if err := setResponseTags(writer, basicMetricTags); err != nil {
		slog.Warn("返回标签设置失败", "error", err.Error())
		return err
	}
	return nil
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

// setBasicTags 设置基础标签
func setBasicTags(c *gin.Context, basicMetricTags *dbsmetrics.BaseMetricTags) {
	basicMetricTags.APIName = c.GetString(commconst.APIName)
	basicMetricTags.Method = c.Request.Method
	basicMetricTags.Status = strconv.Itoa(c.Writer.Status())
}

// setResponseTags 设置响应相关标签
func setResponseTags(
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
func shouldSkip(c *gin.Context) bool {
	apiName := c.GetString(commconst.APIName)
	if apiName == "" || IgnoreAPINames[apiName] {
		slog.Warn("当前接口不需要进行指标统计", "接口名称", apiName)
		return true
	}
	return false
}

// setUserInfoTags 设置用户标签
func setUserInfoTags(c *gin.Context, metricTags *dbsmetrics.BaseMetricTags) error {
	reqBody := ParseReqBody(c)
	if c.Request.Method == http.MethodGet {
		metricTags.BkUserName = c.Query("bk_username")
		metricTags.BkAppCode = c.Query("bk_app_code")
	} else {
		var reqMap = make(map[string]any)
		if err := json.Unmarshal(reqBody, &reqMap); err != nil {
			slog.Error("请求消息体参数反序列化失败", "err", err)
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
