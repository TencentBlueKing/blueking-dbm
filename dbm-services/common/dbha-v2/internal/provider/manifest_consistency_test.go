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

package provider_test

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/internal/provider"
)

func TestManifestMatchesProviderDirs(t *testing.T) {
	root := providerRootDir(t)

	byName := map[string]provider.Entry{}
	for _, e := range provider.Entries {
		byName[e.Name] = e
	}

	entries, err := os.ReadDir(root)
	if err != nil {
		t.Fatalf("read provider root failed, errmsg: %s", err)
	}

	skipDirs := map[string]struct{}{
		"allprobe":    {},
		"allanalysis": {},
		"alldesc":     {},
		"internal":    {},
	}

	for _, ent := range entries {
		if !ent.IsDir() {
			continue
		}
		name := ent.Name()
		if _, skip := skipDirs[name]; skip {
			continue
		}
		entry, ok := byName[name]
		if !ok {
			t.Errorf("provider dir %q exists but is missing from manifest.Entries", name)
			continue
		}
		for _, cap := range entry.Caps {
			sub := capSubdir(cap)
			if sub == "" {
				t.Errorf("unknown capability %q on provider %q", cap, name)
				continue
			}
			subPath := filepath.Join(root, name, sub)
			if st, err := os.Stat(subPath); err != nil || !st.IsDir() {
				t.Errorf("provider %q declares Cap %q but missing subdir %s", name, cap, sub)
			}
		}
		delete(byName, name)
	}

	for name := range byName {
		t.Errorf("manifest entry %q has no matching provider directory", name)
	}
}

func capSubdir(cap provider.Capability) string {
	switch cap {
	case provider.CapDesc:
		return "dbtypedesc"
	case provider.CapHarvest:
		return "harvest"
	case provider.CapSwitch:
		return "switch"
	case provider.CapParse:
		return "parse"
	case provider.CapMetrics:
		return "metrics"
	default:
		return ""
	}
}

func providerRootDir(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller failed")
	}
	dir := filepath.Dir(file)
	// This test file lives in internal/provider/.
	if !strings.HasSuffix(filepath.ToSlash(dir), "/internal/provider") {
		t.Fatalf("unexpected test location: %s", dir)
	}
	return dir
}
