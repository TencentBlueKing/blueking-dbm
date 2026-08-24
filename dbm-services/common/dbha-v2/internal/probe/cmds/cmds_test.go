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

package cmds

import (
	"net"
	"testing"

	"dbm-services/common/dbha-v2/pkg/probeconfig"
)

func TestResolveGenConfigLocalIP_FallbackToOutbound(t *testing.T) {
	ip, err := resolveGenConfigLocalIP(
		"__no_such_interface_for_genconfig_test__",
		"127.0.0.1:19999",
	)
	if err != nil {
		t.Fatalf("resolveGenConfigLocalIP failed, errmsg: %s", err)
	}
	parsed := net.ParseIP(ip)
	if parsed == nil || parsed.To4() == nil {
		t.Fatalf("expected valid IPv4, got: %q", ip)
	}
}

func TestParseAdminEndpoints(t *testing.T) {
	tests := []struct {
		name  string
		input string
		want  []string
	}{
		{
			name:  "semicolon separated",
			input: "127.0.0.1:8080;127.0.0.2:8080",
			want:  []string{"127.0.0.1:8080", "127.0.0.2:8080"},
		},
		{
			name:  "space separated",
			input: "127.0.0.1:8080 127.0.0.2:8080",
			want:  []string{"127.0.0.1:8080", "127.0.0.2:8080"},
		},
		{
			name:  "mixed delimiters",
			input: "127.0.0.1:8080; 127.0.0.2:8080 127.0.0.3:8080",
			want:  []string{"127.0.0.1:8080", "127.0.0.2:8080", "127.0.0.3:8080"},
		},
		{
			name:  "newline separated",
			input: "127.0.0.1:8080\n127.0.0.2:8080",
			want:  []string{"127.0.0.1:8080", "127.0.0.2:8080"},
		},
		{
			name:  "mixed with newline",
			input: "127.0.0.1:8080; 127.0.0.2:8080\n127.0.0.3:8080",
			want:  []string{"127.0.0.1:8080", "127.0.0.2:8080", "127.0.0.3:8080"},
		},
		{
			name:  "crlf separated",
			input: "127.0.0.1:8080\r\n127.0.0.2:8080",
			want:  []string{"127.0.0.1:8080", "127.0.0.2:8080"},
		},
		{
			name:  "trim and skip empty",
			input: " ; 127.0.0.1:8080;; ",
			want:  []string{"127.0.0.1:8080"},
		},
		{
			name:  "empty input",
			input: "",
			want:  nil,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := parseAdminEndpoints(tt.input)
			if len(got) != len(tt.want) {
				t.Fatalf("parseAdminEndpoints(%q) len = %d, want %d, got: %v", tt.input, len(got), len(tt.want), got)
			}
			for i := range tt.want {
				if got[i] != tt.want[i] {
					t.Fatalf("parseAdminEndpoints(%q)[%d] = %q, want %q", tt.input, i, got[i], tt.want[i])
				}
			}
		})
	}
}

func TestParseClearPorts(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    []int
		wantErr bool
	}{
		{name: "comma and semicolon", input: "100,200;300;400", want: []int{100, 200, 300, 400}},
		{name: "single port", input: "10000", want: []int{10000}},
		{name: "empty input", input: "", want: nil},
		{name: "whitespace only input", input: "  \t ", want: nil},
		{name: "trim around token", input: "100; 200, 300 ", want: []int{100, 200, 300}},
		{name: "skip empty segments", input: "100,,200;;300", want: []int{100, 200, 300}},
		{name: "skip leading and trailing separators", input: ",100;200;", want: []int{100, 200}},
		{name: "dedup keeps order", input: "100,100;200", want: []int{100, 200}},
		{name: "boundary ports", input: "1;65535", want: []int{1, 65535}},
		{name: "separators only", input: ",,;", wantErr: true},
		{name: "single separator", input: ",", wantErr: true},
		{name: "zero port", input: "0", wantErr: true},
		{name: "port above range", input: "70000", wantErr: true},
		{name: "negative port", input: "-1", wantErr: true},
		{name: "not a number", input: "abc", wantErr: true},
		{name: "one bad token", input: "100,abc", wantErr: true},
		{name: "space is not a separator", input: "100 200", wantErr: true},
		{name: "full width comma", input: "100，200", wantErr: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := parseClearPorts(tt.input)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("parseClearPorts(%q) expected error, got: %v", tt.input, got)
				}
				if got != nil {
					t.Fatalf("parseClearPorts(%q) must not return ports on error, got: %v", tt.input, got)
				}
				return
			}
			if err != nil {
				t.Fatalf("parseClearPorts(%q) failed, errmsg: %s", tt.input, err)
			}
			if len(got) != len(tt.want) {
				t.Fatalf("parseClearPorts(%q) len: %d, want: %d, got: %v", tt.input, len(got), len(tt.want), got)
			}
			for i := range tt.want {
				if got[i] != tt.want[i] {
					t.Fatalf("parseClearPorts(%q)[%d]: %d, want: %d", tt.input, i, got[i], tt.want[i])
				}
			}
		})
	}
}

func TestApplyClearPorts(t *testing.T) {
	tests := []struct {
		name     string
		ports    []int
		metadata []probeconfig.ProbeMetadataItem
		want     []probeconfig.ProbeMetadataItem
	}{
		{
			name:  "clears data port and keeps admin port",
			ports: []int{20000},
			metadata: []probeconfig.ProbeMetadataItem{
				{IP: "127.0.0.1", Port: 20000, AdminPort: 4001},
			},
			want: []probeconfig.ProbeMetadataItem{
				{IP: "127.0.0.1", Port: 0, AdminPort: 4001},
			},
		},
		{
			name:  "clears admin port and keeps data port",
			ports: []int{4001},
			metadata: []probeconfig.ProbeMetadataItem{
				{IP: "127.0.0.1", Port: 20000, AdminPort: 4001},
			},
			want: []probeconfig.ProbeMetadataItem{
				{IP: "127.0.0.1", Port: 20000, AdminPort: 0},
			},
		},
		{
			name:  "clears the same port on both fields",
			ports: []int{20000},
			metadata: []probeconfig.ProbeMetadataItem{
				{IP: "127.0.0.1", Port: 20000, AdminPort: 20000},
			},
			want: []probeconfig.ProbeMetadataItem{
				{IP: "127.0.0.1", Port: 0, AdminPort: 0},
			},
		},
		{
			name:  "clears across several items",
			ports: []int{20000, 4001},
			metadata: []probeconfig.ProbeMetadataItem{
				{IP: "127.0.0.1", Port: 20000, AdminPort: 0},
				{IP: "127.0.0.1", Port: 20001, AdminPort: 4001},
			},
			want: []probeconfig.ProbeMetadataItem{
				{IP: "127.0.0.1", Port: 0, AdminPort: 0},
				{IP: "127.0.0.1", Port: 20001, AdminPort: 0},
			},
		},
		{
			name:  "port not present is a no-op",
			ports: []int{30000},
			metadata: []probeconfig.ProbeMetadataItem{
				{IP: "127.0.0.1", Port: 20000, AdminPort: 4001},
			},
			want: []probeconfig.ProbeMetadataItem{
				{IP: "127.0.0.1", Port: 20000, AdminPort: 4001},
			},
		},
		{
			name:  "empty port list is a no-op",
			ports: nil,
			metadata: []probeconfig.ProbeMetadataItem{
				{IP: "127.0.0.1", Port: 20000, AdminPort: 4001},
			},
			want: []probeconfig.ProbeMetadataItem{
				{IP: "127.0.0.1", Port: 20000, AdminPort: 4001},
			},
		},
		{
			name:     "empty metadata is a no-op",
			ports:    []int{20000},
			metadata: nil,
			want:     nil,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			applyClearPorts(tt.metadata, tt.ports)
			for i := range tt.want {
				if tt.metadata[i].Port != tt.want[i].Port {
					t.Fatalf("metadata[%d].Port: %d, want: %d", i, tt.metadata[i].Port, tt.want[i].Port)
				}
				if tt.metadata[i].AdminPort != tt.want[i].AdminPort {
					t.Fatalf("metadata[%d].AdminPort: %d, want: %d", i, tt.metadata[i].AdminPort, tt.want[i].AdminPort)
				}
				if tt.metadata[i].IP != tt.want[i].IP {
					t.Fatalf("metadata[%d].IP: %q, want: %q", i, tt.metadata[i].IP, tt.want[i].IP)
				}
			}
		})
	}
}

// TestValidateGenConfigFlags covers the checks that must fail before gen-config dials
// admin, so an unusable invocation never touches the network.
func TestValidateGenConfigFlags(t *testing.T) {
	tests := []struct {
		name       string
		clearPort  string
		outputPath string
		reload     bool
		want       []int
		wantErr    bool
	}{
		{name: "no flags", want: nil},
		{name: "clear-port only", clearPort: "100;200", want: []int{100, 200}},
		{name: "reload with output", outputPath: "etc/probe.yaml", reload: true},
		{name: "reload without output", reload: true, wantErr: true},
		{name: "invalid clear-port", clearPort: "abc", wantErr: true},
		{name: "zero clear-port", clearPort: "0", wantErr: true},
		{name: "out of range clear-port", clearPort: "70000", wantErr: true},
		{name: "invalid clear-port wins over reload", clearPort: "abc", reload: true, wantErr: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := validateGenConfigFlags(tt.clearPort, tt.outputPath, tt.reload)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("validateGenConfigFlags expected error, got: %v", got)
				}
				return
			}
			if err != nil {
				t.Fatalf("validateGenConfigFlags failed, errmsg: %s", err)
			}
			if len(got) != len(tt.want) {
				t.Fatalf("ports len: %d, want: %d, got: %v", len(got), len(tt.want), got)
			}
			for i := range tt.want {
				if got[i] != tt.want[i] {
					t.Fatalf("ports[%d]: %d, want: %d", i, got[i], tt.want[i])
				}
			}
		})
	}
}

func TestResolveGenConfigLocalIP_ExplicitInterface(t *testing.T) {
	iface, err := net.InterfaceByName("lo")
	if err != nil {
		t.Skipf("loopback interface unavailable, errmsg: %s", err)
	}
	ip, err := resolveGenConfigLocalIP(iface.Name, "127.0.0.1:19999")
	if err != nil {
		t.Fatalf("resolveGenConfigLocalIP failed, errmsg: %s", err)
	}
	if ip == "" {
		t.Fatal("expected non-empty IP from loopback interface")
	}
}
