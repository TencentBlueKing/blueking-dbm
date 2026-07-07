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

package client

import (
	"testing"

	"dbm-services/common/dbha-v2/internal/probe/config"

	agentreport "github.com/TencentBlueKing/bk-gse-sdk/go/service/agent-report"
)

// applyOptions runs the option functions against a fresh Config so we can assert
// exactly which SDK fields each option set.
func applyOptions(opts []agentreport.OptionFn) agentreport.Config {
	var c agentreport.Config
	for _, opt := range opts {
		opt(&c)
	}
	return c
}

// TestBuildGSEOptions_NoLocalSocketPort verifies the Linux path: the domain
// socket path is always set and LocalSocketPort stays zero when unset. This is
// the zero-regression guard for E2 (never drop the domain socket).
func TestBuildGSEOptions_NoLocalSocketPort(t *testing.T) {
	cfg := config.ReporterConfig{Endpoint: "/var/run/gse/data.sock"}

	got := applyOptions(buildGSEOptions(cfg, nil))

	if got.DomainSocketPath != cfg.Endpoint {
		t.Fatalf("DomainSocketPath = %q, want %q", got.DomainSocketPath, cfg.Endpoint)
	}
	if got.LocalSocketPort != 0 {
		t.Fatalf("LocalSocketPort = %d, want 0", got.LocalSocketPort)
	}
}

// TestBuildGSEOptions_WithLocalSocketPort verifies the Windows path: when a port
// is configured, LocalSocketPort is set AND the domain socket path is still
// present (non-exclusive), so Linux is unaffected by a stray port value.
func TestBuildGSEOptions_WithLocalSocketPort(t *testing.T) {
	cfg := config.ReporterConfig{Endpoint: "/var/run/gse/data.sock", LocalSocketPort: 18100}

	got := applyOptions(buildGSEOptions(cfg, nil))

	if got.DomainSocketPath != cfg.Endpoint {
		t.Fatalf("DomainSocketPath = %q, want %q", got.DomainSocketPath, cfg.Endpoint)
	}
	if got.LocalSocketPort != 18100 {
		t.Fatalf("LocalSocketPort = %d, want 18100", got.LocalSocketPort)
	}
}
