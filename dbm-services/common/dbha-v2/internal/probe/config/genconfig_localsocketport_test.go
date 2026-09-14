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

package config_test

import (
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/probeconfig"

	_ "dbm-services/common/dbha-v2/internal/provider/mysql/harvest"
	_ "dbm-services/common/dbha-v2/internal/provider/redis/harvest"
)

// TestGenProbeYAML_OmitsLocalSocketPortWhenUnset is the R2 zero-regression guard:
// when Gse.LocalSocketPort is unset, the generated YAML must NOT contain a
// localSocketPort line (byte-identical to the pre-change Linux output).
func TestGenProbeYAML_OmitsLocalSocketPortWhenUnset(t *testing.T) {
	payload := newPayload(nil)

	out, err := config.GenProbeYAML(payload)
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	if strings.Contains(out, "localSocketPort") {
		t.Fatalf("expected no localSocketPort line when unset, got:\n%s", out)
	}
}

// TestGenProbeYAML_EmitsLocalSocketPortWhenSet verifies the Windows path: a
// non-zero LocalSocketPort is plumbed through to the generated YAML.
func TestGenProbeYAML_EmitsLocalSocketPortWhenSet(t *testing.T) {
	payload := newPayload(nil)
	payload.Gse = probeconfig.GseConfig{
		Endpoint:        "127.0.0.1:1234",
		DataID:          1,
		ConnTimeout:     "5s",
		LocalSocketPort: 18100,
	}

	out, err := config.GenProbeYAML(payload)
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	if !strings.Contains(out, "localSocketPort: 18100") {
		t.Fatalf("expected localSocketPort: 18100 in output, got:\n%s", out)
	}
}
