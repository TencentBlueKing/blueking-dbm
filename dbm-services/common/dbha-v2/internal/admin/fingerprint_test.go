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

package admin

import (
	"reflect"
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/internal/admin/config"
)

var (
	snapshotOnlyFields = []string{
		"Discovery.ServiceTimerInterval",
		"Discovery.ServiceUpdateTimeout",
		"DbmApis",
		"ProbeGse",
		"ProbeMysql",
		"ProbeRedis",
		"ProbeProxyAdmin",
		"ProbeHarvesters",
		"ProbeMetadata",
		"ProbeHealth",
	}
	pushFields       = []string{"Log.Level"}
	restartFields    = []string{"Log.Path", "Log.FileCount", "Log.FileSize"}
	frozenIdentities = []string{"Name", "Version", "PidFile"}
)

func TestConfigurationFingerprintCoverage(t *testing.T) {
	fingerprints := slotFingerprintFuncs()
	for _, path := range configurationLeafPaths(fingerprintBaseConfig()) {
		base := fingerprintBaseConfig()
		before := fingerprintValues(fingerprints, base)
		mutateConfigPath(reflect.ValueOf(&base).Elem(), strings.Split(path, "."))
		after := fingerprintValues(fingerprints, base)

		slotChanged := !reflect.DeepEqual(before, after)
		hits := 0
		if isWhitelisted(path, snapshotOnlyFields) {
			hits++
		}
		if isWhitelisted(path, pushFields) {
			hits++
		}
		if isWhitelisted(path, restartFields) {
			hits++
		}
		if isWhitelisted(path, frozenIdentities) {
			hits++
		}

		if slotChanged && hits != 0 {
			t.Errorf("leaf must not be both a slot fingerprint and a whitelist class, path: %s", path)
			continue
		}
		if !slotChanged && hits != 1 {
			t.Errorf(
				"leaf must fall into exactly one class, path: %s, slot_changed: %t, whitelist_hits: %d",
				path, slotChanged, hits,
			)
		}
	}
}

func TestSlotFingerprintsAreValueTypes(t *testing.T) {
	cfg := fingerprintBaseConfig()
	for _, fingerprint := range slotFingerprintFuncs() {
		assertValueFingerprint(t, fingerprint(cfg))
	}
}

func TestRetainIdentityRestoresProcessIdentityNotLogPath(t *testing.T) {
	old := config.Configuration{
		Name:    "admin",
		Version: "1.0.0",
		PidFile: "/tmp/admin.pid",
		Log:     config.LogConfig{Path: "/tmp/old.log"},
	}
	next := config.Configuration{
		Name:    "other",
		Version: "2.0.0",
		PidFile: "/tmp/other.pid",
		Log:     config.LogConfig{Path: "/tmp/new.log"},
	}
	got := config.RetainIdentity(old, next)
	if got.Name != old.Name || got.Version != old.Version || got.PidFile != old.PidFile {
		t.Fatalf(
			"identity not retained, name: %s, version: %s, pidFile: %s",
			got.Name, got.Version, got.PidFile,
		)
	}
	if got.Log.Path != next.Log.Path {
		t.Fatalf("log.path must not be retained, got: %s", got.Log.Path)
	}
}

func fingerprintValues(fns []func(config.Configuration) any, cfg config.Configuration) []any {
	values := make([]any, 0, len(fns))
	for _, fn := range fns {
		values = append(values, fn(cfg))
	}
	return values
}

func assertValueFingerprint(t *testing.T, value any) {
	t.Helper()
	walk := []reflect.Value{reflect.ValueOf(value)}
	for len(walk) > 0 {
		current := walk[0]
		walk = walk[1:]
		for current.Kind() == reflect.Interface {
			if current.IsNil() {
				t.Fatal("fingerprint contains nil interface")
			}
			current = current.Elem()
		}
		switch current.Kind() {
		case reflect.Map, reflect.Slice, reflect.Ptr, reflect.Interface:
			t.Fatalf("fingerprint contains reference type, kind: %s", current.Kind())
		case reflect.Struct:
			for index := 0; index < current.NumField(); index++ {
				walk = append(walk, current.Field(index))
			}
		}
	}
}

func fingerprintBaseConfig() config.Configuration {
	cfg := config.Configuration{
		DbmApis:         []config.DbmApi{{Name: "dbm"}},
		ProbeHarvesters: map[string]config.ProbeHarvesterCred{"mysql": {User: "u"}},
		ProbeHealth:     config.ProbeHealthConfig{DiskWriteDirs: []string{"/tmp"}},
	}
	return cfg
}

func configurationLeafPaths(cfg config.Configuration) []string {
	var paths []string
	walkConfigLeaves(reflect.ValueOf(cfg), "", &paths)
	return paths
}

func walkConfigLeaves(value reflect.Value, path string, paths *[]string) {
	switch value.Kind() {
	case reflect.Struct:
		for index := 0; index < value.NumField(); index++ {
			name := value.Type().Field(index).Name
			walkConfigLeaves(value.Field(index), joinPath(path, name), paths)
		}
	case reflect.Slice:
		if value.Len() == 0 {
			*paths = append(*paths, path)
			return
		}
		walkConfigLeaves(value.Index(0), joinPath(path, "[]"), paths)
	case reflect.Map:
		if value.Len() == 0 {
			*paths = append(*paths, path)
			return
		}
		key := value.MapKeys()[0]
		walkConfigLeaves(value.MapIndex(key), joinPath(path, "{}"), paths)
	default:
		*paths = append(*paths, path)
	}
}

func mutateConfigPath(value reflect.Value, path []string) {
	if len(path) == 0 {
		mutateScalar(value)
		return
	}
	switch path[0] {
	case "[]":
		mutateConfigPath(value.Index(0), path[1:])
	case "{}":
		key := value.MapKeys()[0]
		item := reflect.New(value.Type().Elem()).Elem()
		item.Set(value.MapIndex(key))
		mutateConfigPath(item, path[1:])
		value.SetMapIndex(key, item)
	default:
		mutateConfigPath(value.FieldByName(path[0]), path[1:])
	}
}

func mutateScalar(value reflect.Value) {
	switch value.Kind() {
	case reflect.String:
		value.SetString(value.String() + "x")
	case reflect.Bool:
		value.SetBool(!value.Bool())
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		value.SetInt(value.Int() + 1)
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		value.SetUint(value.Uint() + 1)
	case reflect.Slice:
		value.Set(reflect.Append(value, reflect.Zero(value.Type().Elem())))
	case reflect.Map:
		keyType := value.Type().Key()
		newKey := reflect.New(keyType).Elem()
		if keyType.Kind() == reflect.String {
			newKey.SetString("mutated-key")
			if value.MapIndex(newKey).IsValid() {
				newKey.SetString("mutated-key-2")
			}
		}
		value.SetMapIndex(newKey, reflect.Zero(value.Type().Elem()))
	}
}

func isWhitelisted(path string, whitelist []string) bool {
	normalized := strings.ReplaceAll(strings.ReplaceAll(path, ".[]", ""), ".{}", "")
	for _, entry := range whitelist {
		if normalized == entry || strings.HasPrefix(normalized, entry+".") {
			return true
		}
	}
	return false
}

func joinPath(prefix, part string) string {
	if prefix == "" {
		return part
	}
	return prefix + "." + part
}
