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
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/pkg/proto"
)

func TestAdminControl_RespondsByMode(t *testing.T) {
	ctl := newAdminControl([]byte(`{"gse":{},"metadata":[]}`))

	got := ctl.respond()
	if got.GetCode() != proto.ProbeConfigCode_PROBE_CONFIG_SUCCESS {
		t.Fatalf("default mode code: %s", got.GetCode())
	}
	if got.GetPayload() == "" {
		t.Fatal("success mode must return the current payload")
	}

	if err := ctl.setMode(adminModeNoData); err != nil {
		t.Fatalf("set no_data failed, errmsg: %s", err)
	}
	got = ctl.respond()
	if got.GetCode() != proto.ProbeConfigCode_PROBE_CONFIG_NO_DATA {
		t.Fatalf("no_data mode code: %s", got.GetCode())
	}
	if got.GetPayload() != "" {
		t.Fatal("no_data must not carry a payload the probe could write")
	}

	if err := ctl.setMode(adminModeFail); err != nil {
		t.Fatalf("set fail failed, errmsg: %s", err)
	}
	got = ctl.respond()
	if got.GetCode() != proto.ProbeConfigCode_PROBE_CONFIG_FAIL {
		t.Fatalf("fail mode code: %s", got.GetCode())
	}
}

func TestAdminControl_RejectsUnknownMode(t *testing.T) {
	ctl := newAdminControl([]byte(`{"gse":{},"metadata":[]}`))
	if err := ctl.setMode("explode"); err == nil {
		t.Fatal("expected unknown mode to be rejected")
	}
}

func TestAdminControl_SetPayloadRejectsGarbage(t *testing.T) {
	ctl := newAdminControl([]byte(`{"gse":{},"metadata":[]}`))
	if err := ctl.setPayload([]byte(`[]`)); err == nil {
		t.Fatal("a legacy metadata array must not be accepted as a payload swap")
	}
}

func TestAdminControl_RecordsLastRequest(t *testing.T) {
	ctl := newAdminControl([]byte(`{"gse":{},"metadata":[]}`))
	ctl.recordRequest(&proto.ProbeConfigRequest{
		BkCloudId: 7,
		Ip:        "127.0.0.1",
		ClientID:  "probe-machine",
	})
	got := ctl.lastRequest()
	if got.BkCloudID != 7 || got.IP != "127.0.0.1" || got.ClientID != "probe-machine" {
		t.Fatalf("last request: %+v", got)
	}
}

func TestAdminControl_SetPayloadRoundTrip(t *testing.T) {
	raw, err := defaultPayloadJSON()
	if err != nil {
		t.Fatalf("default payload, errmsg: %s", err)
	}
	ctl := newAdminControl(raw)

	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		t.Fatalf("unmarshal default, errmsg: %s", err)
	}
	meta, _ := payload["metadata"].([]any)
	meta = append(meta, map[string]any{
		"ip": "127.0.0.1", "port": 13307, "cluster_type": "tendbha",
		"machine_type": "backend", "instance_role": "backend_master", "access_layer": "storage",
	})
	payload["metadata"] = meta
	next, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal swapped payload, errmsg: %s", err)
	}
	if err := ctl.setPayload(next); err != nil {
		t.Fatalf("set payload failed, errmsg: %s", err)
	}
	if !strings.Contains(string(ctl.snapshotPayload()), "13307") {
		t.Fatal("swapped payload does not contain the new port")
	}
}
