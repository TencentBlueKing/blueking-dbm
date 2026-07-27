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

package config

import (
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/probeconfig"
)

func TestApplyAllHarvesterPayloadNormalizesKeys(t *testing.T) {
	orig := Cfg.ProbeHarvesters
	t.Cleanup(func() { Cfg.ProbeHarvesters = orig })

	Cfg.ProbeMysql = ProbeMysqlConfig{User: "m", Password: "p", Interval: time.Second, Timeout: time.Second}
	Cfg.ProbeRedis = ProbeRedisConfig{User: "r", Password: "p", Interval: time.Second, Timeout: time.Second}
	Cfg.ProbeProxyAdmin = ProbeProxyAdminConfig{User: "a", Password: "p", Interval: time.Second, Timeout: time.Second}
	Cfg.ProbeHarvesters = map[string]ProbeHarvesterCred{
		"MyNewDb": {User: "u", Password: "p", Interval: 20 * time.Second, Timeout: 5 * time.Second},
	}

	payload := probeconfig.ProbeConfigPayload{}
	applyAllHarvesterPayload(&payload)

	if _, ok := payload.Harvesters["mynewdb"]; !ok {
		t.Fatalf("expected normalized key mynewdb, got: %#v", payload.Harvesters)
	}
	if _, ok := payload.Harvesters["MyNewDb"]; ok {
		t.Fatal("raw camelCase key should not be present after normalization")
	}
}
