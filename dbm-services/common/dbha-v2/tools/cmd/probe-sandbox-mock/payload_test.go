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
	"strconv"
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/probeconfig"

	_ "dbm-services/common/dbha-v2/internal/provider/allprobe"
)

func TestDefaultPayloadJSON_RoundTrip(t *testing.T) {
	raw, err := defaultPayloadJSON()
	if err != nil {
		t.Fatalf("marshal payload failed, errmsg: %s", err)
	}
	var payload probeconfig.ProbeConfigPayload
	if err := json.Unmarshal(raw, &payload); err != nil {
		t.Fatalf("unmarshal payload failed, errmsg: %s", err)
	}
	if payload.MySQL == nil || payload.Redis == nil || payload.ProxyAdmin == nil {
		t.Fatal("expected mysql, redis, and proxy_admin blocks")
	}
	if got := len(payload.Metadata); got != 3 {
		t.Fatalf("metadata count: %d, want 3", got)
	}
}

func TestDefaultPayload_GenProbeYAMLContainsSandboxEndpoints(t *testing.T) {
	yamlStr, err := config.GenProbeYAML(defaultPayload())
	if err != nil {
		t.Fatalf("render probe yaml failed, errmsg: %s", err)
	}
	needles := []string{
		strconv.Itoa(mockMySQLPort),
		strconv.Itoa(mockRedisPort),
		strconv.Itoa(mockProxyDataPort),
		strconv.Itoa(mockProxyAdminPort),
		"mysqlProxyAdmin",
		"tendiscache",
		"name: gse",
	}
	for _, n := range needles {
		if !strings.Contains(yamlStr, n) {
			t.Errorf("rendered yaml missing: %s", n)
		}
	}
}
