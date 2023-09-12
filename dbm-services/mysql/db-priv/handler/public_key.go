/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package handler

import (
	"io/ioutil"
	"net/http"
	"os"

	"dbm-services/common/go-pubpkg/errno"

	"github.com/gin-gonic/gin"
	"golang.org/x/exp/slog"
)

// GetPubKey 获取公钥。加密账号的明文密码，避免传输过程中暴露密码。
func (m *PrivService) GetPubKey(c *gin.Context) {
	slog.Info("do GetPubKey!")
	file, err := os.Open("./pubkey.pem")
	if err != nil {
		SendResponse(c, err, nil)
		return
	}
	defer file.Close()
	content, err := ioutil.ReadAll(file)
	if err != nil {
		SendResponse(c, err, nil)
		return
	}
	SendResponse(c, err, string(content))
	return
}

// SendResponse TODO
func SendResponse(c *gin.Context, err error, data interface{}) {
	code, message := errno.DecodeErr(err)

	c.JSON(http.StatusOK, Response{
		Code:    code,
		Message: message,
		Data:    data,
	})
}

// Response TODO
type Response struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data"`
}

// ListResponse TODO
type ListResponse struct {
	Count int64       `json:"count"`
	Items interface{} `json:"items"`
}
