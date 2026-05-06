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

package discovery

import (
	"encoding/json"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/hanet"
)

func TestServiceInfoCreation(t *testing.T) {
	now := time.Now()
	info := ServiceInfo{
		ID:        "test-id",
		Name:      "test-service",
		Nice:      0,
		IPs:       []string{"127.0.0.1", "127.0.0.2"},
		StartTime: now,
		Uptime:    "1h30m",
		UpdatedAt: now,
	}

	if info.ID != "test-id" {
		t.Fatalf("ServiceInfo.ID = %v, want test-id", info.ID)
	}
	if info.Name != "test-service" {
		t.Fatalf("ServiceInfo.Name = %v, want test-service", info.Name)
	}
	if len(info.IPs) != 2 {
		t.Fatalf("ServiceInfo.IPs length = %v, want 2", len(info.IPs))
	}
	t.Logf("ServiceInfo created: %+v", info)
}

func TestServiceInfoWithEndpoints(t *testing.T) {
	now := time.Now()
	listenAddr := &hanet.Endpoint{Host: "0.0.0.0", Port: 8080}
	probeAddr := &hanet.Endpoint{Host: "0.0.0.0", Port: 8081}

	info := ServiceInfo{
		ID:            "test-id",
		Name:          "test-service",
		Nice:          10,
		IPs:           []string{"127.0.0.1"},
		ListenAddress: listenAddr,
		ProbeEndpoint: probeAddr,
		StartTime:     now,
		Uptime:        "2h",
		UpdatedAt:     now,
	}

	if info.ListenAddress == nil {
		t.Fatal("ServiceInfo.ListenAddress should not be nil")
	}
	if info.ProbeEndpoint == nil {
		t.Fatal("ServiceInfo.ProbeEndpoint should not be nil")
	}
	if info.ListenAddress.Port != 8080 {
		t.Fatalf("ServiceInfo.ListenAddress.Port = %v, want 8080", info.ListenAddress.Port)
	}
	t.Logf("ServiceInfo with endpoints: %+v", info)
}

func TestServiceInfoJSONSerialization(t *testing.T) {
	now := time.Now()
	info := ServiceInfo{
		ID:        "json-test-id",
		Name:      "json-test-service",
		Nice:      5,
		IPs:       []string{"127.0.0.1"},
		StartTime: now,
		Uptime:    "30m",
		UpdatedAt: now,
	}

	data, err := json.Marshal(info)
	if err != nil {
		t.Fatalf("json.Marshal() error: %v", err)
	}
	t.Logf("ServiceInfo JSON: %s", string(data))

	var decoded ServiceInfo
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("json.Unmarshal() error: %v", err)
	}

	if decoded.ID != info.ID {
		t.Fatalf("decoded.ID = %v, want %v", decoded.ID, info.ID)
	}
	if decoded.Name != info.Name {
		t.Fatalf("decoded.Name = %v, want %v", decoded.Name, info.Name)
	}
	t.Logf("ServiceInfo deserialized: %+v", decoded)
}

func TestServiceInfoNilEndpoints(t *testing.T) {
	info := ServiceInfo{
		ID:   "nil-endpoint-test",
		Name: "test",
	}

	data, err := json.Marshal(info)
	if err != nil {
		t.Fatalf("json.Marshal() error: %v", err)
	}

	var decoded ServiceInfo
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("json.Unmarshal() error: %v", err)
	}

	if decoded.ListenAddress != nil {
		t.Fatal("decoded.ListenAddress should be nil")
	}
	if decoded.ProbeEndpoint != nil {
		t.Fatal("decoded.ProbeEndpoint should be nil")
	}
	t.Logf("ServiceInfo with nil endpoints handled correctly")
}
