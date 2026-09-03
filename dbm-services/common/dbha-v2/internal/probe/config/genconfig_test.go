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
	"reflect"
	"sort"
	"testing"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/dbtype"
	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	_ "dbm-services/common/dbha-v2/internal/provider/mysql/harvest"
	_ "dbm-services/common/dbha-v2/internal/provider/redis/harvest"

	"gopkg.in/yaml.v3"
)

// parsedYAML mirrors the on-the-wire layout emitted by GenProbeYAML so tests can
// round-trip the rendered yaml without depending on viper.
type parsedYAML struct {
	Name      string             `yaml:"name"`
	Version   string             `yaml:"version"`
	PidFile   string             `yaml:"pidFile"`
	Reporter  parsedReporterYAML `yaml:"reporter"`
	Harvester parsedHarvester    `yaml:"harvester"`
}

type parsedReporterYAML struct {
	Name        string `yaml:"name"`
	Endpoint    string `yaml:"endpoint"`
	DataID      uint64 `yaml:"dataID"`
	ConnTimeout string `yaml:"connTimeout"`
}

type parsedHarvester struct {
	MySQL           *parsedMySQLHarvester `yaml:"mysql,omitempty"`
	MySQLProxyAdmin *parsedMySQLHarvester `yaml:"mysqlProxyAdmin,omitempty"`
	Redis           *parsedRedisHarvester `yaml:"redis,omitempty"`
}

type parsedMySQLHarvester struct {
	User              string             `yaml:"user"`
	Password          string             `yaml:"password"`
	Interval          string             `yaml:"interval"`
	HeartbeatInterval string             `yaml:"heartbeatInterval"`
	ReplDelayInterval string             `yaml:"replDelayInterval"`
	Timeout           string             `yaml:"timeout"`
	Endpoints         []parsedDbEndpoint `yaml:"endpoints"`
}

type parsedRedisHarvester struct {
	User      string             `yaml:"user"`
	Password  string             `yaml:"password"`
	Interval  string             `yaml:"interval"`
	Timeout   string             `yaml:"timeout"`
	Endpoints []parsedDbEndpoint `yaml:"endpoints"`
}

type parsedDbEndpoint struct {
	Proto        string   `yaml:"proto"`
	ClusterType  string   `yaml:"clusterType"`
	MachineType  string   `yaml:"machineType"`
	InstanceRole string   `yaml:"instanceRole,omitempty"`
	AccessLayer  string   `yaml:"accessLayer"`
	Ip           string   `yaml:"ip"`
	Ports        []string `yaml:"ports,omitempty"`
	AdminPorts   []string `yaml:"adminPorts,omitempty"`
}

func renderAndParse(t *testing.T, payload probeconfig.ProbeConfigPayload) parsedYAML {
	t.Helper()
	out, err := config.GenProbeYAML(payload)
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	var got parsedYAML
	if err := yaml.Unmarshal([]byte(out), &got); err != nil {
		t.Fatalf("yaml unmarshal failed, errmsg: %s", err)
	}
	return got
}

func newPayload(metadata []probeconfig.ProbeMetadataItem) probeconfig.ProbeConfigPayload {
	return probeconfig.ProbeConfigPayload{
		Gse: probeconfig.GseConfig{
			Endpoint:    "127.0.0.1:1234",
			DataID:      1,
			ConnTimeout: "5s",
		},
		MySQL: &probeconfig.ProbeMySQLConfig{
			User:              "mysql_user",
			Password:          "mysql_pwd",
			Interval:          "20s",
			HeartbeatInterval: "3s",
			ReplDelayInterval: "20s",
			Timeout:           "5s",
		},
		Redis: &probeconfig.ProbeRedisConfig{
			User:     "redis_user",
			Password: "redis_pwd",
			Interval: "20s",
			Timeout:  "5s",
		},
		ProxyAdmin: &probeconfig.ProbeProxyAdminConfig{
			User:              "proxy_admin_user",
			Password:          "proxy_admin_pwd",
			Interval:          "20s",
			HeartbeatInterval: "3s",
			ReplDelayInterval: "20s",
			Timeout:           "5s",
		},
		Metadata: metadata,
	}
}

func TestGenProbeYAML_RegularMysql(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.1",
			Port:        3306,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeBackend),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
		},
	})

	got := renderAndParse(t, payload)

	if got.Harvester.MySQL == nil {
		t.Fatal("expected MySQL harvester to be present")
	}
	if got.Harvester.MySQLProxyAdmin != nil {
		t.Fatal("expected MySQLProxyAdmin to be absent")
	}
	if got.Harvester.Redis != nil {
		t.Fatal("expected Redis to be absent")
	}
	if got.Harvester.MySQL.User != "mysql_user" {
		t.Errorf("unexpected user, got: %s", got.Harvester.MySQL.User)
	}
	if got.Harvester.MySQL.Timeout != "5s" {
		t.Errorf("unexpected timeout, got: %s", got.Harvester.MySQL.Timeout)
	}
	if got.Harvester.MySQL.HeartbeatInterval != "3s" {
		t.Errorf("unexpected heartbeatInterval, got: %s", got.Harvester.MySQL.HeartbeatInterval)
	}
	if got.Harvester.MySQL.ReplDelayInterval != "20s" {
		t.Errorf("unexpected replDelayInterval, got: %s", got.Harvester.MySQL.ReplDelayInterval)
	}
	if len(got.Harvester.MySQL.Endpoints) != 1 {
		t.Fatalf("expected 1 endpoint, got: %d", len(got.Harvester.MySQL.Endpoints))
	}
	ep := got.Harvester.MySQL.Endpoints[0]
	if !reflect.DeepEqual(ep.Ports, []string{"3306"}) {
		t.Errorf("unexpected ports, got: %v", ep.Ports)
	}
	if len(ep.AdminPorts) != 0 {
		t.Errorf("expected no admin ports, got: %v", ep.AdminPorts)
	}
}

func TestGenProbeYAML_RegularRedis(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.10",
			Port:        6379,
			ClusterType: string(haprobe.DbmMetadataClusterTypeRedis),
			MachineType: string(haprobe.DbmMetadataMachineTypeTendisCache),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
		},
	})

	got := renderAndParse(t, payload)

	if got.Harvester.Redis == nil {
		t.Fatal("expected Redis harvester to be present")
	}
	if got.Harvester.MySQL != nil {
		t.Fatal("expected MySQL to be absent")
	}
	if got.Harvester.MySQLProxyAdmin != nil {
		t.Fatal("expected MySQLProxyAdmin to be absent")
	}
	if got.Harvester.Redis.User != "redis_user" {
		t.Errorf("unexpected user, got: %s", got.Harvester.Redis.User)
	}
}

func TestGenProbeYAML_MysqlProxyOnly(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.2",
			Port:        10000,
			AdminPort:   4001,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeProxy),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeProxy),
		},
	})

	got := renderAndParse(t, payload)

	if got.Harvester.MySQLProxyAdmin == nil {
		t.Fatal("expected MySQLProxyAdmin harvester to be present")
	}
	// With the dual-produce change, a mysql-proxy carrying a data port additionally emits a
	// mysql block for the lightweight data-port probe.
	if got.Harvester.MySQL == nil {
		t.Fatal("expected MySQL harvester to be present for the proxy data port")
	}
	if got.Harvester.MySQLProxyAdmin.User != "proxy_admin_user" {
		t.Errorf("unexpected user, got: %s", got.Harvester.MySQLProxyAdmin.User)
	}
	if got.Harvester.MySQLProxyAdmin.Timeout != "5s" {
		t.Errorf("unexpected timeout, got: %s", got.Harvester.MySQLProxyAdmin.Timeout)
	}
	if got.Harvester.MySQLProxyAdmin.HeartbeatInterval != "3s" {
		t.Errorf("unexpected heartbeatInterval, got: %s", got.Harvester.MySQLProxyAdmin.HeartbeatInterval)
	}
	if got.Harvester.MySQLProxyAdmin.ReplDelayInterval != "20s" {
		t.Errorf("unexpected replDelayInterval, got: %s", got.Harvester.MySQLProxyAdmin.ReplDelayInterval)
	}
	if len(got.Harvester.MySQLProxyAdmin.Endpoints) != 1 {
		t.Fatalf("expected 1 endpoint, got: %d", len(got.Harvester.MySQLProxyAdmin.Endpoints))
	}
	adminEp := got.Harvester.MySQLProxyAdmin.Endpoints[0]
	if len(adminEp.Ports) != 0 {
		t.Errorf("mysql-proxy admin endpoint must not carry Ports, got: %v", adminEp.Ports)
	}
	if !reflect.DeepEqual(adminEp.AdminPorts, []string{"4001"}) {
		t.Errorf("unexpected admin ports, got: %v", adminEp.AdminPorts)
	}

	// The data-port endpoint goes to the mysql block with probeMysql creds, only Ports, no AdminPorts.
	if got.Harvester.MySQL.User != "mysql_user" {
		t.Errorf("data-port endpoint must use probeMysql user, got: %s", got.Harvester.MySQL.User)
	}
	if len(got.Harvester.MySQL.Endpoints) != 1 {
		t.Fatalf("expected 1 mysql endpoint, got: %d", len(got.Harvester.MySQL.Endpoints))
	}
	dataEp := got.Harvester.MySQL.Endpoints[0]
	if !reflect.DeepEqual(dataEp.Ports, []string{"10000"}) {
		t.Errorf("unexpected data ports, got: %v", dataEp.Ports)
	}
	if len(dataEp.AdminPorts) != 0 {
		t.Errorf("mysql-proxy data endpoint must not carry AdminPorts, got: %v", dataEp.AdminPorts)
	}
	if dataEp.MachineType != string(haprobe.DbmMetadataMachineTypeProxy) {
		t.Errorf("unexpected data endpoint machine type, got: %s", dataEp.MachineType)
	}
}

// TestGenProbeYAML_MysqlProxyDataPortOnly asserts a mysql-proxy that carries only a data port
// (no admin port) is skipped entirely: without admin capability we do not emit either block.
func TestGenProbeYAML_MysqlProxyDataPortOnly(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.21",
			Port:        10000,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeProxy),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeProxy),
		},
	})

	got := renderAndParse(t, payload)

	if got.Harvester.MySQLProxyAdmin != nil {
		t.Fatal("expected MySQLProxyAdmin to be absent when proxy has no admin port")
	}
	if got.Harvester.MySQL != nil {
		t.Fatal("expected MySQL to be absent when proxy has no admin port")
	}
}

// TestGenProbeYAML_MysqlProxyDualPortFallback covers the fallback path (payload.ProxyAdmin==nil)
// for a mysql-proxy that has BOTH a data port and an admin port. The data-port endpoint and the
// fallback admin-port endpoint share an identical 5-tuple key and both land in the mysql block;
// output must remain deterministic (validated by the secondary tie-break in sortEndpoints).
func TestGenProbeYAML_MysqlProxyDualPortFallback(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.22",
			Port:        10000,
			AdminPort:   4001,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeProxy),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeProxy),
		},
	})
	payload.ProxyAdmin = nil

	got := renderAndParse(t, payload)

	if got.Harvester.MySQLProxyAdmin != nil {
		t.Fatal("expected MySQLProxyAdmin absent when payload.ProxyAdmin is nil")
	}
	if got.Harvester.MySQL == nil {
		t.Fatal("expected MySQL harvester to carry both data and fallback admin endpoints")
	}
	if got.Harvester.MySQL.User != "mysql_user" {
		t.Errorf("fallback should use probeMysql creds, got: %s", got.Harvester.MySQL.User)
	}
	if len(got.Harvester.MySQL.Endpoints) != 2 {
		t.Fatalf("expected 2 mysql endpoints (data + fallback admin), got: %d", len(got.Harvester.MySQL.Endpoints))
	}

	var sawData, sawAdmin bool
	for _, ep := range got.Harvester.MySQL.Endpoints {
		switch {
		case reflect.DeepEqual(ep.Ports, []string{"10000"}) && len(ep.AdminPorts) == 0:
			sawData = true
		case reflect.DeepEqual(ep.AdminPorts, []string{"4001"}) && len(ep.Ports) == 0:
			sawAdmin = true
		default:
			t.Errorf("unexpected endpoint shape, ports: %v, adminPorts: %v", ep.Ports, ep.AdminPorts)
		}
	}
	if !sawData {
		t.Error("expected a data-port endpoint with Ports=[10000] and no AdminPorts")
	}
	if !sawAdmin {
		t.Error("expected a fallback admin-port endpoint with AdminPorts=[4001] and no Ports")
	}

	// Determinism: identical 5-tuple keys must render in a stable order across runs.
	first, err := config.GenProbeYAML(payload)
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	for i := 0; i < 10; i++ {
		out, err := config.GenProbeYAML(payload)
		if err != nil {
			t.Fatalf("GenProbeYAML failed on iter %d, errmsg: %s", i, err)
		}
		if out != first {
			t.Fatalf("GenProbeYAML output not deterministic on iter %d", i)
		}
	}
}

func TestGenProbeYAML_MixedProxyAndStorage(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.3",
			Port:        3306,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeBackend),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
		},
		{
			IP:          "127.0.0.3",
			AdminPort:   4001,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeProxy),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeProxy),
		},
	})

	got := renderAndParse(t, payload)

	if got.Harvester.MySQL == nil {
		t.Fatal("expected MySQL harvester to be present for backend endpoint")
	}
	if got.Harvester.MySQLProxyAdmin == nil {
		t.Fatal("expected MySQLProxyAdmin harvester to be present for proxy endpoint")
	}
	if got.Harvester.MySQL.User != "mysql_user" {
		t.Errorf("MySQL harvester must use probeMysql user, got: %s", got.Harvester.MySQL.User)
	}
	if got.Harvester.MySQLProxyAdmin.User != "proxy_admin_user" {
		t.Errorf("MySQLProxyAdmin harvester must use proxyAdmin user, got: %s", got.Harvester.MySQLProxyAdmin.User)
	}

	if len(got.Harvester.MySQL.Endpoints) != 1 {
		t.Fatalf("expected 1 mysql endpoint, got: %d", len(got.Harvester.MySQL.Endpoints))
	}
	mysqlEp := got.Harvester.MySQL.Endpoints[0]
	if !reflect.DeepEqual(mysqlEp.Ports, []string{"3306"}) {
		t.Errorf("unexpected mysql ports, got: %v", mysqlEp.Ports)
	}
	if mysqlEp.MachineType != string(haprobe.DbmMetadataMachineTypeBackend) {
		t.Errorf("unexpected mysql machine type, got: %s", mysqlEp.MachineType)
	}

	if len(got.Harvester.MySQLProxyAdmin.Endpoints) != 1 {
		t.Fatalf("expected 1 proxy admin endpoint, got: %d", len(got.Harvester.MySQLProxyAdmin.Endpoints))
	}
	proxyEp := got.Harvester.MySQLProxyAdmin.Endpoints[0]
	if !reflect.DeepEqual(proxyEp.AdminPorts, []string{"4001"}) {
		t.Errorf("unexpected proxy admin ports, got: %v", proxyEp.AdminPorts)
	}
	if len(proxyEp.Ports) != 0 {
		t.Errorf("proxy admin endpoint must not carry Ports, got: %v", proxyEp.Ports)
	}
}

func TestGenProbeYAML_MultiFamily(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.4",
			Port:        3306,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeBackend),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
		},
		{
			IP:          "127.0.0.5",
			AdminPort:   4001,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeProxy),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeProxy),
		},
		{
			IP:          "127.0.0.6",
			Port:        6379,
			ClusterType: string(haprobe.DbmMetadataClusterTypeRedis),
			MachineType: string(haprobe.DbmMetadataMachineTypeTendisCache),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
		},
	})

	got := renderAndParse(t, payload)

	if got.Harvester.MySQL == nil || got.Harvester.MySQLProxyAdmin == nil || got.Harvester.Redis == nil {
		t.Fatalf(
			"expected all three harvester blocks to be present, got: mysql=%v mysqlProxyAdmin=%v redis=%v",
			got.Harvester.MySQL != nil,
			got.Harvester.MySQLProxyAdmin != nil,
			got.Harvester.Redis != nil,
		)
	}
}

func TestGenProbeYAML_FallbackWhenProxyAdminMissing(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.7",
			AdminPort:   4001,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeProxy),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeProxy),
		},
	})
	payload.ProxyAdmin = nil

	got := renderAndParse(t, payload)

	if got.Harvester.MySQLProxyAdmin != nil {
		t.Fatal("expected MySQLProxyAdmin absent when payload.ProxyAdmin is nil")
	}
	if got.Harvester.MySQL == nil {
		t.Fatal("expected MySQL harvester to receive fallback proxy-admin endpoint")
	}
	if got.Harvester.MySQL.User != "mysql_user" {
		t.Errorf("fallback should use probeMysql creds, got: %s", got.Harvester.MySQL.User)
	}
	if got.Harvester.MySQL.Timeout != "5s" {
		t.Errorf("fallback should inherit probeMysql timeout, got: %s", got.Harvester.MySQL.Timeout)
	}
	if len(got.Harvester.MySQL.Endpoints) != 1 {
		t.Fatalf("expected 1 endpoint in fallback mysql block, got: %d", len(got.Harvester.MySQL.Endpoints))
	}
	ep := got.Harvester.MySQL.Endpoints[0]
	if !reflect.DeepEqual(ep.AdminPorts, []string{"4001"}) {
		t.Errorf("unexpected admin ports in fallback, got: %v", ep.AdminPorts)
	}
}

func TestGenProbeYAML_DropsZeroPort(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.8",
			Port:        0,
			AdminPort:   4001,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeBackend),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
		},
	})

	got := renderAndParse(t, payload)

	if got.Harvester.MySQL == nil {
		t.Fatal("expected MySQL harvester to be present")
	}
	if len(got.Harvester.MySQL.Endpoints) != 1 {
		t.Fatalf("expected 1 endpoint, got: %d", len(got.Harvester.MySQL.Endpoints))
	}
	ep := got.Harvester.MySQL.Endpoints[0]
	if len(ep.Ports) != 0 {
		t.Errorf("expected no Ports when m.Port==0, got: %v", ep.Ports)
	}
	if !reflect.DeepEqual(ep.AdminPorts, []string{"4001"}) {
		t.Errorf("unexpected admin ports, got: %v", ep.AdminPorts)
	}
}

// TestGenProbeYAML_ProxyAccessButNonMysqlClusterIsNotProxyAdmin asserts that a malformed
// metadata entry with (machine_type=proxy, access_layer=proxy) but a non-mysql cluster_type
// is NOT routed to harvester.mysqlProxyAdmin. The redis-cluster-typed entry falls through
// to the redis block via the Redis HarvestBlock fallback (its only known route).
func TestGenProbeYAML_ProxyAccessButNonMysqlClusterIsNotProxyAdmin(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.99",
			AdminPort:   4001,
			ClusterType: string(haprobe.DbmMetadataClusterTypeRedis),
			MachineType: string(haprobe.DbmMetadataMachineTypeProxy),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeProxy),
		},
	})

	got := renderAndParse(t, payload)

	if got.Harvester.MySQLProxyAdmin != nil {
		t.Fatal("expected MySQLProxyAdmin to be absent for non-mysql clusterType")
	}
	if got.Harvester.MySQL != nil {
		t.Fatal("expected MySQL to be absent for non-mysql clusterType")
	}
	if got.Harvester.Redis == nil {
		t.Fatal("expected Redis harvester to receive the redis-cluster-typed entry")
	}
	if len(got.Harvester.Redis.Endpoints) != 1 {
		t.Fatalf("expected 1 redis endpoint, got: %d", len(got.Harvester.Redis.Endpoints))
	}
	ep := got.Harvester.Redis.Endpoints[0]
	if !reflect.DeepEqual(ep.AdminPorts, []string{"4001"}) {
		t.Errorf("unexpected admin ports, got: %v", ep.AdminPorts)
	}
}

// TestGenProbeYAML_OptionsDoNotChangeDefaultRendering keeps the options mechanism from shifting
// what existing callers get: no options, and a no-op option, must render exactly as before.
func TestGenProbeYAML_OptionsDoNotChangeDefaultRendering(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{storageItem(3306, 0)})

	base, err := GenProbeYAML(payload)
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	// An empty version is the shape a config predating the version field parses to.
	withEmpty, err := GenProbeYAML(payload, WithVersion(""), nil)
	if err != nil {
		t.Fatalf("GenProbeYAML with options failed, errmsg: %s", err)
	}
	if withEmpty != base {
		t.Fatal("empty version option changed the rendered output")
	}

	withVersion, err := GenProbeYAML(payload, WithVersion("v9"))
	if err != nil {
		t.Fatalf("GenProbeYAML with version failed, errmsg: %s", err)
	}
	var parsed parsedYAML
	if err := yaml.Unmarshal([]byte(withVersion), &parsed); err != nil {
		t.Fatalf("yaml unmarshal failed, errmsg: %s", err)
	}
	if parsed.Version != "v9" {
		t.Fatalf("version option not applied, got: %s", parsed.Version)
	}
}

// storageItem builds a TendbHA storage metadata item on the loopback address, used by the
// port-ordering tests where only the ports differ between items.
func storageItem(port, adminPort int) probeconfig.ProbeMetadataItem {
	return probeconfig.ProbeMetadataItem{
		IP:          "127.0.0.1",
		Port:        port,
		AdminPort:   adminPort,
		ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
		MachineType: string(haprobe.DbmMetadataMachineTypeBackend),
		AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
	}
}

// TestGenProbeYAML_PortOrderIndependentOfInput covers a machine hosting several instances.
// The rendered ports must not depend on the order the metadata arrived in: admin returns rows
// without ORDER BY and may serve them either from its local cache or from the DBM API, so an
// input-dependent rendering would make periodic sync rewrite the file whenever the source
// switches, rebuilding every harvester on that machine each time.
func TestGenProbeYAML_PortOrderIndependentOfInput(t *testing.T) {
	ascending := []probeconfig.ProbeMetadataItem{
		storageItem(3306, 13306),
		storageItem(3307, 13307),
		storageItem(3308, 13308),
	}
	shuffled := []probeconfig.ProbeMetadataItem{
		storageItem(3308, 13308),
		storageItem(3306, 13306),
		storageItem(3307, 13307),
	}

	want, err := GenProbeYAML(newPayload(ascending))
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	got, err := GenProbeYAML(newPayload(shuffled))
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	if got != want {
		t.Fatalf("rendered yaml depends on metadata input order")
	}

	parsed := renderAndParse(t, newPayload(shuffled))
	if parsed.Harvester.MySQL == nil || len(parsed.Harvester.MySQL.Endpoints) != 1 {
		t.Fatalf("expected a single mysql endpoint, got: %+v", parsed.Harvester.MySQL)
	}
	ep := parsed.Harvester.MySQL.Endpoints[0]
	if !reflect.DeepEqual(ep.Ports, []string{"3306", "3307", "3308"}) {
		t.Errorf("ports not sorted, got: %v", ep.Ports)
	}
	if !reflect.DeepEqual(ep.AdminPorts, []string{"13306", "13307", "13308"}) {
		t.Errorf("adminPorts not sorted, got: %v", ep.AdminPorts)
	}
}

// TestGenProbeYAML_PortsSortedNumerically pins the ordering to port value rather than string
// order: lexically "3306" sorts before "800", numerically it does not.
func TestGenProbeYAML_PortsSortedNumerically(t *testing.T) {
	parsed := renderAndParse(t, newPayload([]probeconfig.ProbeMetadataItem{
		storageItem(3306, 0),
		storageItem(800, 0),
	}))

	if parsed.Harvester.MySQL == nil || len(parsed.Harvester.MySQL.Endpoints) != 1 {
		t.Fatalf("expected a single mysql endpoint, got: %+v", parsed.Harvester.MySQL)
	}
	if got := parsed.Harvester.MySQL.Endpoints[0].Ports; !reflect.DeepEqual(got, []string{"800", "3306"}) {
		t.Errorf("expected numeric port order, got: %v", got)
	}
}

func TestGenProbeYAML_DeterministicOrder(t *testing.T) {
	metadata := []probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.20",
			Port:        3306,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeBackend),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
		},
		{
			IP:          "127.0.0.10",
			Port:        3306,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeBackend),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
		},
		{
			IP:          "127.0.0.15",
			Port:        3306,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeBackend),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
		},
	}
	payload := newPayload(metadata)

	first, err := config.GenProbeYAML(payload)
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	for i := 0; i < 10; i++ {
		out, err := config.GenProbeYAML(payload)
		if err != nil {
			t.Fatalf("GenProbeYAML failed on iter %d, errmsg: %s", i, err)
		}
		if out != first {
			t.Fatalf("GenProbeYAML output not deterministic on iter %d", i)
		}
	}

	got := renderAndParse(t, payload)
	if got.Harvester.MySQL == nil {
		t.Fatal("expected MySQL harvester to be present")
	}
	ips := make([]string, 0, len(got.Harvester.MySQL.Endpoints))
	for _, ep := range got.Harvester.MySQL.Endpoints {
		ips = append(ips, ep.Ip)
	}
	expected := []string{"127.0.0.10", "127.0.0.15", "127.0.0.20"}
	if !reflect.DeepEqual(ips, expected) {
		t.Errorf("expected sorted endpoints, got: %v", ips)
	}
	sorted := make([]string, len(ips))
	copy(sorted, ips)
	sort.Strings(sorted)
	if !reflect.DeepEqual(ips, sorted) {
		t.Errorf("endpoint order not sorted, got: %v", ips)
	}
}

func ensureKafkaHarvestBlockForTest(t *testing.T) {
	t.Helper()
	if _, ok := dbtype.HarvestBlockByName("kafka"); ok {
		return
	}
	dbtype.RegisterHarvestBlock(dbtype.HarvestBlock{
		BlockName:  "kafka",
		DbType:     haprobe.DbTypeKafka,
		PayloadKey: "kafka",
	})
}

func TestGenProbeYAML_ExtraHarvesterBlock(t *testing.T) {
	ensureKafkaHarvestBlockForTest(t)

	payload := newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.31",
			Port:        9092,
			ClusterType: string(haprobe.DbmMetadataClusterTypeKafka),
			MachineType: string(haprobe.DbmMetadataMachineTypeBroker),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
		},
	})
	payload.Harvesters = map[string]probeconfig.ProbeHarvesterConfig{
		"kafka": {
			User:     "kafka_user",
			Password: "kafka_pwd",
			Interval: "20s",
			Timeout:  "5s",
		},
	}

	out, err := config.GenProbeYAML(payload)
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}

	var raw map[string]any
	if err := yaml.Unmarshal([]byte(out), &raw); err != nil {
		t.Fatalf("yaml unmarshal failed, errmsg: %s", err)
	}
	harvester, ok := raw["harvester"].(map[string]any)
	if !ok {
		t.Fatalf("harvester missing or wrong type: %#v", raw["harvester"])
	}
	kafka, ok := harvester["kafka"].(map[string]any)
	if !ok {
		t.Fatalf("expected kafka block, got keys: %v", harvester)
	}
	if kafka["user"] != "kafka_user" {
		t.Errorf("unexpected kafka user: %v", kafka["user"])
	}
	if harvester["mysql"] != nil || harvester["redis"] != nil {
		t.Errorf("named blocks should be absent for kafka-only metadata, got: %v", harvester)
	}
}

func ensureCamelEsHarvestBlockForTest(t *testing.T) {
	t.Helper()
	if _, ok := dbtype.HarvestBlockByName("camelEsTest"); ok {
		return
	}
	dbtype.RegisterHarvestBlock(dbtype.HarvestBlock{
		BlockName:  "camelEsTest",
		DbType:     haprobe.DbTypeEs,
		PayloadKey: "camelEsTest",
	})
}

func TestGenProbeYAML_ExtraHarvesterCamelCasePayloadKey(t *testing.T) {
	ensureCamelEsHarvestBlockForTest(t)

	payload := newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.32",
			Port:        9200,
			ClusterType: string(haprobe.DbmMetadataClusterTypeEs),
			MachineType: string(haprobe.DbmMetadataMachineTypeBroker),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
		},
	})
	// Simulate admin viper lowercasing of probeHarvesters keys.
	payload.Harvesters = map[string]probeconfig.ProbeHarvesterConfig{
		"camelestest": {
			User: "camel_user", Password: "pwd", Interval: "20s", Timeout: "5s",
		},
	}

	out, err := config.GenProbeYAML(payload)
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	var raw map[string]any
	if err := yaml.Unmarshal([]byte(out), &raw); err != nil {
		t.Fatalf("yaml unmarshal failed, errmsg: %s", err)
	}
	harvester := raw["harvester"].(map[string]any)
	block, ok := harvester["camelEsTest"].(map[string]any)
	if !ok {
		t.Fatalf("expected camelEsTest block from normalized payload key, keys: %v", harvester)
	}
	if block["user"] != "camel_user" {
		t.Errorf("unexpected user: %v", block["user"])
	}
}

func ensureDorisMatchBlocksForTest(t *testing.T) {
	t.Helper()
	if _, ok := dbtype.HarvestBlockByName("dorisProxyMatchTest"); ok {
		return
	}
	dbtype.RegisterHarvestBlock(dbtype.HarvestBlock{
		BlockName:  "dorisProxyMatchTest",
		DbType:     haprobe.DbTypeDoris,
		PayloadKey: "dorisproxymatchtest",
		Match: func(a dbtype.EndpointAttrs) bool {
			return a.AccessLayer == haprobe.DbmMetadataAccessLayerTypeProxy
		},
	})
	dbtype.RegisterHarvestBlock(dbtype.HarvestBlock{
		BlockName:  "dorisStorageMatchTest",
		DbType:     haprobe.DbTypeDoris,
		PayloadKey: "dorisstoragematchtest",
		Match:      nil, // fallback
	})
}

func TestGenProbeYAML_MatchRoutesByAccessLayer(t *testing.T) {
	ensureDorisMatchBlocksForTest(t)

	payload := newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.33",
			Port:        8030,
			ClusterType: string(haprobe.DbmMetadataClusterTypeDoris),
			MachineType: string(haprobe.DbmMetadataMachineTypeBroker),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeProxy),
		},
		{
			IP:          "127.0.0.34",
			Port:        9050,
			ClusterType: string(haprobe.DbmMetadataClusterTypeDoris),
			MachineType: string(haprobe.DbmMetadataMachineTypeBroker),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
		},
	})
	payload.Harvesters = map[string]probeconfig.ProbeHarvesterConfig{
		"dorisproxymatchtest": {
			User: "proxy_u", Password: "p", Interval: "20s", Timeout: "5s",
		},
		"dorisstoragematchtest": {
			User: "store_u", Password: "p", Interval: "20s", Timeout: "5s",
		},
	}

	out, err := config.GenProbeYAML(payload)
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	var raw map[string]any
	if err := yaml.Unmarshal([]byte(out), &raw); err != nil {
		t.Fatalf("yaml unmarshal failed, errmsg: %s", err)
	}
	harvester := raw["harvester"].(map[string]any)
	proxyBlock, ok := harvester["dorisProxyMatchTest"].(map[string]any)
	if !ok {
		t.Fatalf("expected dorisProxyMatchTest block, keys: %v", harvester)
	}
	storeBlock, ok := harvester["dorisStorageMatchTest"].(map[string]any)
	if !ok {
		t.Fatalf("expected dorisStorageMatchTest block, keys: %v", harvester)
	}
	if proxyBlock["user"] != "proxy_u" || storeBlock["user"] != "store_u" {
		t.Fatalf("unexpected users: proxy=%v store=%v", proxyBlock["user"], storeBlock["user"])
	}
}

func TestGenProbeYAML_PortsSortedNumerically(t *testing.T) {
	parsed := renderAndParse(t, newPayload([]probeconfig.ProbeMetadataItem{
		mysqlItem("127.0.0.1", 3306, 0),
		mysqlItem("127.0.0.1", 800, 0),
	}))

	if parsed.Harvester.MySQL == nil || len(parsed.Harvester.MySQL.Endpoints) != 1 {
		t.Fatalf("expected a single mysql endpoint, got: %+v", parsed.Harvester.MySQL)
	}
	if got := parsed.Harvester.MySQL.Endpoints[0].Ports; !reflect.DeepEqual(got, []string{"800", "3306"}) {
		t.Errorf("expected numeric port order, got: %v", got)
	}
}

func TestGenProbeYAML_PortOrderIndependentOfInput(t *testing.T) {
	ascending := []probeconfig.ProbeMetadataItem{
		mysqlItem("127.0.0.1", 3306, 13306),
		mysqlItem("127.0.0.1", 3307, 13307),
		mysqlItem("127.0.0.1", 3308, 13308),
	}
	shuffled := []probeconfig.ProbeMetadataItem{
		mysqlItem("127.0.0.1", 3308, 13308),
		mysqlItem("127.0.0.1", 3306, 13306),
		mysqlItem("127.0.0.1", 3307, 13307),
	}

	want, err := config.GenProbeYAML(newPayload(ascending))
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	got, err := config.GenProbeYAML(newPayload(shuffled))
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	if got != want {
		t.Fatalf("rendered yaml depends on metadata input order")
	}

	parsed := renderAndParse(t, newPayload(shuffled))
	if parsed.Harvester.MySQL == nil || len(parsed.Harvester.MySQL.Endpoints) != 1 {
		t.Fatalf("expected a single mysql endpoint, got: %+v", parsed.Harvester.MySQL)
	}
	ep := parsed.Harvester.MySQL.Endpoints[0]
	if !reflect.DeepEqual(ep.Ports, []string{"3306", "3307", "3308"}) {
		t.Errorf("ports not sorted, got: %v", ep.Ports)
	}
	if !reflect.DeepEqual(ep.AdminPorts, []string{"13306", "13307", "13308"}) {
		t.Errorf("adminPorts not sorted, got: %v", ep.AdminPorts)
	}
}

func TestGenProbeYAML_OptionsDoNotChangeDefaultRendering(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{mysqlItem("127.0.0.1", 3306, 0)})

	base, err := config.GenProbeYAML(payload)
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	// An empty version is the shape a config predating the version field parses to.
	withEmpty, err := config.GenProbeYAML(payload, config.WithVersion(""), nil)
	if err != nil {
		t.Fatalf("GenProbeYAML with options failed, errmsg: %s", err)
	}
	if withEmpty != base {
		t.Fatal("empty version option changed the rendered output")
	}

	withVersion, err := config.GenProbeYAML(payload, config.WithVersion("v9"))
	if err != nil {
		t.Fatalf("GenProbeYAML with version failed, errmsg: %s", err)
	}
	var parsed parsedYAML
	if err := yaml.Unmarshal([]byte(withVersion), &parsed); err != nil {
		t.Fatalf("yaml unmarshal failed, errmsg: %s", err)
	}
	if parsed.Version != "v9" {
		t.Fatalf("version option not applied, got: %s", parsed.Version)
	}
}
