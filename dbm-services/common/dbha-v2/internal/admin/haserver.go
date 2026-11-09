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

package admin

import (
	"context"

	"dbm-services/common/dbha-v2/internal/admin/api/open/serializer"
	adminconfig "dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/proto"
)

var errDiscoveryUnavailable = gerrors.New(gerrors.EtcdFailure, "discovery resource is unavailable")

// haServerLister resolves the current discovery resource on every call, so a reload
// takes effect without re-registering routes.
type haServerLister struct {
	srv *Service
}

func (l *haServerLister) List(ctx context.Context) (*discovery.HaServerList, error) {
	resource := l.srv.discoverySlot.Get()
	if resource == nil || resource.discovery == nil {
		return nil, errDiscoveryUnavailable
	}

	return discovery.ListHaServers(ctx, resource.discovery, adminconfig.Snapshot().Discovery.ServiceUpdateTimeout)
}

// newListHaServersResponse builds the success response from the same V1 data used by HTTP,
// so both protocols always carry identical values.
func newListHaServersResponse(data serializer.HaServerListData) *proto.ListHaServersResponse {
	servers := make([]*proto.HaServerInfo, 0, len(data.Servers))
	for _, server := range data.Servers {
		servers = append(servers, &proto.HaServerInfo{
			Role:      server.Role,
			Id:        server.ID,
			Ips:       server.IPs,
			StartTime: server.StartTime,
			UpdatedAt: server.UpdatedAt,
			Uptime:    server.Uptime,
		})
	}

	return &proto.ListHaServersResponse{
		Code:    proto.HaServerListCode_HA_SERVER_LIST_SUCCESS,
		Errmsg:  "success",
		Servers: servers,
		Ips:     data.IPs,
	}
}
