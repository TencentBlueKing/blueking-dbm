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
	"go/build"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

const (
	modulePrefix   = "dbm-services/common/dbha-v2"
	providerPrefix = modulePrefix + "/internal/provider/"
	receiverPkg    = modulePrefix + "/cmd/receiver"
)

// TestReceiverProviderDepsArePublicOnly locks the receiver boundary:
// it may blank-import provider public content (alldesc / */dbtypedesc), but must not
// pull concrete DB capability packages (harvest / switch / parse / metrics).
// Receiver only passthrough-persists probe payloads; DB-specific parsing belongs in analysis.
func TestReceiverProviderDepsArePublicOnly(t *testing.T) {
	moduleRoot := findModuleRoot(t)
	visited := map[string]struct{}{}
	parentOf := map[string]string{}
	queue := []string{receiverPkg}

	for len(queue) > 0 {
		cur := queue[0]
		queue = queue[1:]
		if _, ok := visited[cur]; ok {
			continue
		}
		visited[cur] = struct{}{}

		if !isAllowedProviderImport(cur) {
			t.Fatalf(
				"receiver transitively depends on concrete provider package %s\n"+
					"import path: %s\n"+
					"receiver may import alldesc / */dbtypedesc only; "+
					"harvest/switch/parse/metrics belong on the analysis/probe side",
				cur, formatImportChain(parentOf, cur),
			)
		}

		dir := importPathToDir(moduleRoot, cur)
		if dir == "" {
			continue
		}
		pkg, err := build.ImportDir(dir, 0)
		if err != nil {
			if _, ok := err.(*build.NoGoError); ok {
				continue
			}
			t.Fatalf("ImportDir(%s) failed, errmsg: %s", dir, err)
		}

		for _, imp := range pkg.Imports {
			if !strings.HasPrefix(imp, modulePrefix) {
				continue
			}
			if _, ok := visited[imp]; ok {
				continue
			}
			if _, ok := parentOf[imp]; !ok {
				parentOf[imp] = cur
			}
			queue = append(queue, imp)
		}
	}
}

func isAllowedProviderImport(importPath string) bool {
	if !strings.HasPrefix(importPath, providerPrefix) {
		return true
	}
	rest := strings.TrimPrefix(importPath, providerPrefix)
	if rest == "alldesc" {
		return true
	}
	return strings.HasSuffix(rest, "/dbtypedesc")
}

func importPathToDir(moduleRoot, importPath string) string {
	if importPath == modulePrefix {
		return moduleRoot
	}
	if !strings.HasPrefix(importPath, modulePrefix+"/") {
		return ""
	}
	return filepath.Join(moduleRoot, strings.TrimPrefix(importPath, modulePrefix+"/"))
}

func formatImportChain(parentOf map[string]string, leaf string) string {
	var parts []string
	cur := leaf
	for {
		parts = append(parts, cur)
		parent, ok := parentOf[cur]
		if !ok {
			break
		}
		cur = parent
	}
	for i, j := 0, len(parts)-1; i < j; i, j = i+1, j-1 {
		parts[i], parts[j] = parts[j], parts[i]
	}
	return strings.Join(parts, " -> ")
}

func findModuleRoot(t *testing.T) string {
	t.Helper()
	_, thisFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller failed")
	}
	dir := filepath.Dir(thisFile)
	for {
		if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			t.Fatal("cannot locate module root (go.mod)")
		}
		dir = parent
	}
}
