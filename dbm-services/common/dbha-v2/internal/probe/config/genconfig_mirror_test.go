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
	"reflect"
	"strings"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// newMirrorPayload is a minimal admin payload: these tests care about the locally owned blocks,
// not about what the harvester section renders to.
func newMirrorPayload() probeconfig.ProbeConfigPayload {
	return probeconfig.ProbeConfigPayload{
		Gse: probeconfig.GseConfig{Endpoint: "127.0.0.1:1234", DataID: 1, ConnTimeout: "5s"},
		MySQL: &probeconfig.ProbeMySQLConfig{
			User: "u", Password: "p", Interval: "20s", Timeout: "5s",
		},
		Metadata: []probeconfig.ProbeMetadataItem{
			{
				IP:          "127.0.0.1",
				Port:        3306,
				ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
				MachineType: string(haprobe.DbmMetadataMachineTypeBackend),
				AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
			},
		},
	}
}

// yamlKeys collects the yaml key of every field of t, ignoring options such as omitempty.
func yamlKeys(t *testing.T, typ reflect.Type) map[string]reflect.Type {
	t.Helper()

	keys := make(map[string]reflect.Type, typ.NumField())
	for i := 0; i < typ.NumField(); i++ {
		field := typ.Field(i)
		tag := field.Tag.Get("yaml")
		if tag == "" || tag == "-" {
			t.Fatalf("field without yaml tag, type: %s, field: %s", typ.Name(), field.Name)
		}
		keys[strings.Split(tag, ",")[0]] = field.Type
	}
	return keys
}

// assertMirrors checks that mirror covers exactly the yaml keys of source, and that the only
// type substitution is time.Duration rendered as a string.
func assertMirrors(t *testing.T, source, mirror reflect.Type) {
	t.Helper()

	sourceKeys := yamlKeys(t, source)
	mirrorKeys := yamlKeys(t, mirror)

	for key, sourceType := range sourceKeys {
		mirrorType, ok := mirrorKeys[key]
		if !ok {
			t.Errorf("mirror %s is missing key %q from %s; a config written through it would "+
				"drop that field", mirror.Name(), key, source.Name())
			continue
		}
		want := sourceType
		if sourceType == reflect.TypeOf(time.Duration(0)) {
			want = reflect.TypeOf("")
		}
		if mirrorType != want {
			t.Errorf("mirror %s key %q has type %s, want %s", mirror.Name(), key, mirrorType, want)
		}
	}

	for key := range mirrorKeys {
		if _, ok := sourceKeys[key]; !ok {
			t.Errorf("mirror %s has key %q that %s does not define", mirror.Name(), key, source.Name())
		}
	}
}

// TestMirrorStructsCoverSource is the guard that keeps the yaml mirror structs in step with the
// Configuration types they render. Without it, a field added to ClientConfig or AdminConfig
// would keep compiling and simply vanish from the file the next time periodic sync rewrites it.
func TestMirrorStructsCoverSource(t *testing.T) {
	assertMirrors(t, reflect.TypeOf(ClientConfig{}), reflect.TypeOf(probeClientYAML{}))
	assertMirrors(t, reflect.TypeOf(AdminConfig{}), reflect.TypeOf(probeAdminYAML{}))
}

// TestProbeYAMLCoversConfigurationKeys is the top-level counterpart of TestMirrorStructsCoverSource.
// Nested mirrors can differ in Go type (durations become strings, structs become pointers) and
// still be correct; this test only requires that every yaml key on Configuration exists on
// probeYAML, so a newly added locally owned field cannot vanish from rendered output unnoticed.
func TestProbeYAMLCoversConfigurationKeys(t *testing.T) {
	sourceKeys := yamlKeys(t, reflect.TypeOf(Configuration{}))
	mirrorKeys := yamlKeys(t, reflect.TypeOf(probeYAML{}))
	for key := range sourceKeys {
		if _, ok := mirrorKeys[key]; !ok {
			t.Errorf("probeYAML is missing key %q from Configuration", key)
		}
	}
	for key := range mirrorKeys {
		if _, ok := sourceKeys[key]; !ok {
			t.Errorf("probeYAML has key %q that Configuration does not define", key)
		}
	}
}

// TestLocalFields_SurviveRoundTrip is the end-to-end guarantee behind LocalFields: take a
// configuration carrying every locally owned field, render it with an admin payload, parse the
// result back, and every one of those fields must be unchanged. This is exactly what periodic
// sync does to the file on disk, so a regression here means unattended config loss.
func TestLocalFields_SurviveRoundTrip(t *testing.T) {
	local := Configuration{
		Version:   "v9",
		ServiceID: "svc-local",
		PidFile:   "/tmp/custom/probe.pid",
		Reporter:  &ReporterConfig{BkCloudID: 7},
		Client: ClientConfig{
			PingTime:                     30 * time.Second,
			PingTimeout:                  5 * time.Second,
			MaxReceiveMessageSize:        1024,
			MaxSendMessageSize:           2048,
			ReceiverReconnectInterval:    3 * time.Second,
			ReceiverMaxReconnectAttempts: 9,
		},
		Admin: AdminConfig{
			Endpoints:    []string{"127.0.0.1:19001", "127.0.0.1:19002"},
			BkCloudID:    7,
			LocalIP:      "127.0.0.1",
			SyncInterval: 90 * time.Second,
		},
		Log:        LogConfig{Path: "/tmp/custom/probe.log", Level: "debug", FileCount: 3, FileSize: 42},
		ClearPorts: []int{3307, 3306},
	}

	rendered, err := GenProbeYAML(newMirrorPayload(), LocalFields(local)...)
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	parsed, err := ParseBytes([]byte(rendered))
	if err != nil {
		t.Fatalf("rendered config does not parse, errmsg: %s", err)
	}

	if parsed.Version != local.Version {
		t.Errorf("version lost, got: %s", parsed.Version)
	}
	if parsed.ServiceID != local.ServiceID {
		t.Errorf("serviceID lost, got: %s", parsed.ServiceID)
	}
	if parsed.PidFile != local.PidFile {
		t.Errorf("pidFile lost, got: %s", parsed.PidFile)
	}
	if !reflect.DeepEqual(parsed.Client, local.Client) {
		t.Errorf("client block lost, got: %+v", parsed.Client)
	}
	if !reflect.DeepEqual(parsed.Admin, local.Admin) {
		t.Errorf("admin block lost, got: %+v", parsed.Admin)
	}
	if !reflect.DeepEqual(parsed.Log, local.Log) {
		t.Errorf("log block lost, got: %+v", parsed.Log)
	}
	if parsed.Reporter == nil || parsed.Reporter.BkCloudID != 7 {
		t.Errorf("reporter bkCloudID lost, got: %+v", parsed.Reporter)
	}
	if !reflect.DeepEqual(parsed.ClearPorts, []int{3306, 3307}) {
		t.Errorf("clearPorts lost or unsorted, got: %v", parsed.ClearPorts)
	}
}

// TestLocalFields_TolerateEmptyLocalConfig covers the upgrade path: a config predating these
// fields parses into empty values, and feeding those back must not blank out the rendered
// defaults or emit keys the probe cannot parse.
func TestLocalFields_TolerateEmptyLocalConfig(t *testing.T) {
	rendered, err := GenProbeYAML(newMirrorPayload(), LocalFields(Configuration{})...)
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	parsed, err := ParseBytes([]byte(rendered))
	if err != nil {
		t.Fatalf("rendered config does not parse, errmsg: %s", err)
	}

	if parsed.Version != defaultProbeConfigVersion {
		t.Errorf("empty version should keep the rendered default, got: %q", parsed.Version)
	}
	if parsed.PidFile != defaultPidFile {
		t.Errorf("empty pidFile should keep the rendered default, got: %q", parsed.PidFile)
	}
	if parsed.Log.Path == "" || parsed.Log.Level == "" {
		t.Errorf("empty log block should keep the rendered default, got: %+v", parsed.Log)
	}
	if !parsed.Admin.IsZero() {
		t.Errorf("no admin block was supplied, got: %+v", parsed.Admin)
	}
	if strings.Contains(rendered, "admin:") || strings.Contains(rendered, "client:") ||
		strings.Contains(rendered, "clearPorts:") {
		t.Error("zero-valued local blocks should not appear in the rendered config")
	}
}

// TestMirrorStructsOmitZeroValues pins the reason every mirror field carries omitempty: a zero
// duration renders to "" and viper rejects that, so a zero-valued block must produce no keys at
// all rather than keys the probe can no longer parse.
func TestMirrorStructsOmitZeroValues(t *testing.T) {
	cfg := probeYAML{}
	WithClient(ClientConfig{})(&cfg)
	WithAdmin(AdminConfig{})(&cfg)

	if cfg.Client != nil {
		t.Error("zero client block should not be rendered at all")
	}
	if cfg.Admin != nil {
		t.Error("zero admin block should not be rendered at all")
	}

	// A partially set block renders only the keys that carry a value.
	WithAdmin(AdminConfig{Endpoints: []string{"127.0.0.1:19001"}})(&cfg)
	if cfg.Admin == nil {
		t.Fatal("non-zero admin block should be rendered")
	}
	if cfg.Admin.SyncInterval != "" {
		t.Errorf("zero duration should render empty and be omitted, got: %q", cfg.Admin.SyncInterval)
	}
}
