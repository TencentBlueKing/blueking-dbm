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
	"context"
	"errors"

	"dbm-services/common/dbha-v2/internal/admin/api/open/serializer"
	"dbm-services/common/dbha-v2/internal/admin/ginx"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/logger"

	"github.com/gin-gonic/gin"
)

// HaServerLister lists live HA server instances. A non-nil error means discovery is unavailable.
type HaServerLister interface {
	List(ctx context.Context) (*discovery.HaServerList, error)
}

var errHaServerListUnavailable = errors.New(serializer.HaServerListUnavailableMessage)

// HaServerHandler serves HA server metadata APIs.
type HaServerHandler struct {
	lister HaServerLister
}

// NewHaServerHandler creates an HaServerHandler backed by lister.
func NewHaServerHandler(lister HaServerLister) *HaServerHandler {
	return &HaServerHandler{lister: lister}
}

// List lists live admin, analysis and receiver instances and their merged IPs.
// Query parameters and request body are ignored. On discovery failure it responds with
// HTTP 400, code 1 and the fixed message "service discovery unavailable".
//
//	@ID			openapi_meta_ha_servers_list
//	@Summary	List live HA servers
//	@Produce	json
//	@Tags		openapi.meta
//	@Success	200	{object}	serializer.HaServerListResponse
//	@Failure	400	{object}	serializer.HaServerListErrorResponse
//	@Router		/api/admin/meta/ha-servers [get]
func (h *HaServerHandler) List(c *gin.Context) {
	list, err := h.lister.List(c.Request.Context())
	if err != nil {
		logger.Warn("list ha servers failed, errmsg: %s", err)
		ginx.V1ErrorJSONResponse(c, serializer.RespErr, errHaServerListUnavailable)
		return
	}

	ginx.V1SuccessJSONResponse(c, serializer.NewHaServerListData(list), serializer.RespOK, "")
}
