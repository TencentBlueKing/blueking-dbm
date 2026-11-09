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
	"time"

	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/logger"
)

var haServerLocation = loadShanghaiLocation(time.LoadLocation)

const (
	// HaServerListUnavailableMessage is the fixed client-facing message when HA servers cannot be listed.
	// Raw discovery errors are only logged and never returned to clients.
	HaServerListUnavailableMessage = "service discovery unavailable"

	shanghaiLocationName   = "Asia/Shanghai"
	shanghaiFallbackZone   = "CST"
	shanghaiFallbackOffset = 8 * 60 * 60
)

// HaServerOutputInfo is one HA server instance in the V1 JSON response.
type HaServerOutputInfo struct {
	Role      string   `json:"role"`
	ID        string   `json:"id"`
	IPs       []string `json:"ips"`
	StartTime string   `json:"start_time"`
	UpdatedAt string   `json:"updated_at"`
	Uptime    string   `json:"uptime"`
}

// HaServerListData is the data field of the HA server list V1 response.
// Servers and IPs are always encoded as arrays, never null.
type HaServerListData struct {
	Servers []HaServerOutputInfo `json:"servers"`
	IPs     []string             `json:"ips"`
}

// HaServerListResponse documents the successful V1 envelope of GET /api/admin/meta/ha-servers.
type HaServerListResponse struct {
	Data    HaServerListData `json:"data"`
	Code    int              `json:"code"`
	Message string           `json:"message"`
}

// HaServerListErrorResponse documents the failed V1 envelope of GET /api/admin/meta/ha-servers,
// where data is always an empty string. It is only referenced by Swagger annotations.
type HaServerListErrorResponse struct {
	Data    string `json:"data"`
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// NewHaServerListData converts a discovery result into V1 output. Times are formatted with
// TimeFormat in Asia/Shanghai; a zero time is formatted as "". A nil list yields empty arrays.
func NewHaServerListData(list *discovery.HaServerList) HaServerListData {
	data := HaServerListData{Servers: []HaServerOutputInfo{}, IPs: []string{}}
	if list == nil {
		return data
	}

	for _, server := range list.Servers {
		data.Servers = append(data.Servers, HaServerOutputInfo{
			Role:      server.Role,
			ID:        server.ID,
			IPs:       copyStrings(server.IPs),
			StartTime: formatHaServerTime(server.StartTime, haServerLocation),
			UpdatedAt: formatHaServerTime(server.UpdatedAt, haServerLocation),
			Uptime:    server.Uptime,
		})
	}
	data.IPs = copyStrings(list.IPs)

	return data
}

// loadShanghaiLocation loads Asia/Shanghai with load and falls back to a fixed +08:00 zone on error.
func loadShanghaiLocation(load func(name string) (*time.Location, error)) *time.Location {
	loc, err := load(shanghaiLocationName)
	if err != nil {
		logger.Warn("load time location failed, location: %s, errmsg: %s, fallback: +08:00",
			shanghaiLocationName, err)
		return time.FixedZone(shanghaiFallbackZone, shanghaiFallbackOffset)
	}

	return loc
}

func formatHaServerTime(t time.Time, loc *time.Location) string {
	if t.IsZero() {
		return ""
	}

	return t.In(loc).Format(TimeFormat)
}

func copyStrings(values []string) []string {
	return append(make([]string, 0, len(values)), values...)
}
