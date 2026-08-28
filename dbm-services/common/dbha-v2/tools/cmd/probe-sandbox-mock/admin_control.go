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

package main

import (
	"encoding/json"
	"fmt"
	"sync"

	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/proto"
)

const (
	adminModeSuccess = "success"
	adminModeNoData  = "no_data"
	adminModeFail    = "fail"
)

// adminControl is the live GetProbeConfig answer the HTTP control plane can change
// while the mock is running. The periodic-sync sandbox needs to swap payload and
// return NO_DATA without restarting the process.
type adminControl struct {
	mu sync.Mutex

	payload []byte
	mode    string

	lastBkCloudID uint64
	lastIP        string
	lastClientID  string
}

type lastAdminRequest struct {
	BkCloudID uint64 `json:"bk_cloud_id"`
	IP        string `json:"ip"`
	ClientID  string `json:"client_id"`
}

func newAdminControl(payload []byte) *adminControl {
	return &adminControl{payload: payload, mode: adminModeSuccess}
}

func (c *adminControl) snapshotPayload() []byte {
	c.mu.Lock()
	defer c.mu.Unlock()
	out := make([]byte, len(c.payload))
	copy(out, c.payload)
	return out
}

func (c *adminControl) setPayload(raw []byte) error {
	var payload probeconfig.ProbeConfigPayload
	if err := json.Unmarshal(raw, &payload); err != nil {
		return fmt.Errorf("payload is not ProbeConfigPayload: %w", err)
	}
	normalized, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	c.mu.Lock()
	c.payload = normalized
	c.mu.Unlock()
	return nil
}

func (c *adminControl) snapshotMode() string {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.mode
}

func (c *adminControl) setMode(mode string) error {
	switch mode {
	case adminModeSuccess, adminModeNoData, adminModeFail:
	default:
		return fmt.Errorf("unknown admin mode: %s", mode)
	}

	c.mu.Lock()
	c.mode = mode
	c.mu.Unlock()
	return nil
}

func (c *adminControl) recordRequest(req *proto.ProbeConfigRequest) {
	c.mu.Lock()
	c.lastBkCloudID = req.GetBkCloudId()
	c.lastIP = req.GetIp()
	c.lastClientID = req.GetClientID()
	c.mu.Unlock()
}

func (c *adminControl) lastRequest() lastAdminRequest {
	c.mu.Lock()
	defer c.mu.Unlock()
	return lastAdminRequest{
		BkCloudID: c.lastBkCloudID,
		IP:        c.lastIP,
		ClientID:  c.lastClientID,
	}
}

func (c *adminControl) respond() *proto.ProbeConfigResponse {
	c.mu.Lock()
	defer c.mu.Unlock()

	switch c.mode {
	case adminModeNoData:
		return &proto.ProbeConfigResponse{
			Code:   proto.ProbeConfigCode_PROBE_CONFIG_NO_DATA,
			Errmsg: "no data",
		}
	case adminModeFail:
		return &proto.ProbeConfigResponse{
			Code:   proto.ProbeConfigCode_PROBE_CONFIG_FAIL,
			Errmsg: "mock failure",
		}
	default:
		return &proto.ProbeConfigResponse{
			Code:    proto.ProbeConfigCode_PROBE_CONFIG_SUCCESS,
			Errmsg:  "ok",
			Payload: string(c.payload),
		}
	}
}
