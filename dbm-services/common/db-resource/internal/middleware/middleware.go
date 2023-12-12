/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package middleware TODO
package middleware

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"time"

	"dbm-services/common/db-resource/internal/controller"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
)

// RequestLoggerFilter TODO
var RequestLoggerFilter *ApiLoggerFilter

func init() {
	RequestLoggerFilter = &ApiLoggerFilter{}
}

// ApiLoggerFilter TODO
type ApiLoggerFilter struct {
	WhitelistUri []string
}

func (a *ApiLoggerFilter) filter(uri string) bool {
	return cmutil.HasElem(uri, a.WhitelistUri)
}

// Add TODO
func (a *ApiLoggerFilter) Add(uri string) {
	a.WhitelistUri = append(a.WhitelistUri, uri)
}

type bodyLogWriter struct {
	gin.ResponseWriter
	body *bytes.Buffer
}

// Write 用于常见IO
func (w bodyLogWriter) Write(b []byte) (int, error) {
	w.body.Write(b)
	return w.ResponseWriter.Write(b)
}

// BodyLogMiddleware TODO
func BodyLogMiddleware(c *gin.Context) {
	if c.Request.URL.Path == "/metrics" || c.Request.URL.Path == "/ping" {
		c.Next()
		return
	}

	blw := &bodyLogWriter{body: bytes.NewBufferString(""), ResponseWriter: c.Writer}
	c.Writer = blw
	c.Next()
	statusCode := c.Writer.Status()
	// if statusCode >= 400 {
	// ok this is an request with error, let's make a record for it
	// now print body (or log in your preferred way)
	var rp controller.Response
	if blw.body == nil {
		rp = controller.Response{}
	} else {
		if err := json.Unmarshal(blw.body.Bytes(), &rp); err != nil {
			logger.Error("unmarshal respone body failed %s", err.Error())
			return
		}
	}
	if err := model.UpdateTbRequestLog(rp.RequestId, map[string]interface{}{"respone_body": blw.body.String(),
		"respone_code": statusCode, "update_time": time.Now()}); err != nil {
		logger.Warn("update request respone failed %s", err.Error())
	}
}

// ApiLogger TODO
func ApiLogger(c *gin.Context) {
	if c.Request.URL.Path == "/metrics" || c.Request.URL.Path == "/ping" {
		c.Next()
		return
	}

	rid := requestid.Get(c)
	c.Set("request_id", rid)
	if c.Request.Method == http.MethodPost {
		if !RequestLoggerFilter.filter(c.Request.RequestURI) {
			return
		}
		var bodyBytes []byte
		// read from the original request body
		bodyBytes, err := io.ReadAll(c.Request.Body)
		if err != nil {
			return
		}
		if len(bodyBytes) <= 0 {
			bodyBytes = []byte("{}")
		}
		// create a new buffer and replace the original request body
		c.Request.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))
		if err := model.CreateTbRequestLog(model.TbRequestLog{
			RequestID:   rid,
			RequestUser: "",
			RequestUrl:  c.Request.RequestURI,
			RequestBody: string(bodyBytes),
			SourceIP:    c.Request.RemoteAddr,
			CreateTime:  time.Now(),
			ResponeBody: "{}",
		}); err != nil {
			logger.Warn("record request log failed %s", err.Error())
		}
	}
}
