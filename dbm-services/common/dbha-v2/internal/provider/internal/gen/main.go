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

// Command gen produces provider/allprobe, provider/allanalysis, and provider/alldesc
// blank-import packages from the single manifest in package provider.
package main

import (
	"bytes"
	"fmt"
	"go/format"
	"os"
	"path/filepath"
	"sort"

	"dbm-services/common/dbha-v2/internal/provider"
)

type aggregateTarget int

const (
	targetProbe aggregateTarget = iota
	targetAnalysis
	targetDesc
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintf(os.Stderr, "provider gen failed: %v\n", err)
		os.Exit(1)
	}
}

func run() error {
	root, err := findProviderRoot()
	if err != nil {
		return err
	}

	specs := []struct {
		target  aggregateTarget
		dir     string
		pkg     string
		comment string
	}{
		{
			target:  targetProbe,
			dir:     "allprobe",
			pkg:     "allprobe",
			comment: "Blank-import all probe-side provider capabilities (dbtypedesc + harvest).",
		},
		{
			target:  targetAnalysis,
			dir:     "allanalysis",
			pkg:     "allanalysis",
			comment: "Blank-import all analysis-side provider capabilities (dbtypedesc + switch + parse).",
		},
		{
			target:  targetDesc,
			dir:     "alldesc",
			pkg:     "alldesc",
			comment: "Blank-import all CapDesc provider packages (dbtypedesc only).",
		},
	}

	for _, s := range specs {
		imports := collectImports(provider.Entries, s.target)
		path := filepath.Join(root, s.dir, s.dir+"_gen.go")
		if err := writeAggregate(path, s.pkg, s.comment, imports); err != nil {
			return err
		}
	}
	return nil
}

func collectImports(entries []provider.Entry, target aggregateTarget) []string {
	seen := map[string]struct{}{}
	var out []string
	add := func(path string) {
		if _, ok := seen[path]; ok {
			return
		}
		seen[path] = struct{}{}
		out = append(out, path)
	}

	for _, e := range entries {
		for _, cap := range e.Caps {
			switch cap {
			case provider.CapDesc:
				// Desc goes into every aggregate (probe, analysis, and desc-only).
				add(e.BasePath + "/dbtypedesc")
			case provider.CapHarvest:
				if target == targetProbe {
					add(e.BasePath + "/harvest")
				}
			case provider.CapSwitch:
				if target == targetAnalysis {
					add(e.BasePath + "/switch")
				}
			case provider.CapParse:
				if target == targetAnalysis {
					add(e.BasePath + "/parse")
				}
			}
		}
	}
	sort.Strings(out)
	return out
}

func writeAggregate(path, pkg, comment string, imports []string) error {
	var buf bytes.Buffer
	buf.WriteString("/**\n")
	buf.WriteString(" * MIT License\n")
	buf.WriteString(" *\n")
	buf.WriteString(" * Copyright (c) 2023 腾讯蓝鲸\n")
	buf.WriteString(" *\n")
	buf.WriteString(" * Permission is hereby granted, free of charge, to any person obtaining a copy\n")
	buf.WriteString(" * of this software and associated documentation files (the \"Software\"), to deal\n")
	buf.WriteString(" * in the Software without restriction, including without limitation the rights\n")
	buf.WriteString(" * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n")
	buf.WriteString(" * copies of the Software, and to permit persons to whom the Software is\n")
	buf.WriteString(" * furnished to do so, subject to the following conditions:\n")
	buf.WriteString(" *\n")
	buf.WriteString(" * The above copyright notice and this permission notice shall be included in all\n")
	buf.WriteString(" * copies or substantial portions of the Software.\n")
	buf.WriteString(" *\n")
	buf.WriteString(" * THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n")
	buf.WriteString(" * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n")
	buf.WriteString(" * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n")
	buf.WriteString(" * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n")
	buf.WriteString(" * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n")
	buf.WriteString(" * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\n")
	buf.WriteString(" * SOFTWARE.\n")
	buf.WriteString(" */\n\n")
	buf.WriteString("// Code generated by provider/internal/gen; DO NOT EDIT.\n\n")
	buf.WriteString("package " + pkg + "\n\n")
	if comment != "" {
		buf.WriteString("// " + comment + "\n")
	}
	if len(imports) == 0 {
		buf.WriteString("// No provider capabilities registered for this aggregate yet.\n")
	} else {
		buf.WriteString("import (\n")
		for _, imp := range imports {
			buf.WriteString("\t_ \"" + imp + "\"\n")
		}
		buf.WriteString(")\n")
	}

	formatted, err := format.Source(buf.Bytes())
	if err != nil {
		return fmt.Errorf("format %s: %w\nsource:\n%s", path, err, buf.String())
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return os.WriteFile(path, formatted, 0o644)
}

func findProviderRoot() (string, error) {
	// When invoked via go:generate from provider/, cwd is the provider package dir.
	cwd, err := os.Getwd()
	if err != nil {
		return "", err
	}
	// Prefer cwd if it looks like the provider root (has manifest.go).
	if _, err := os.Stat(filepath.Join(cwd, "manifest.go")); err == nil {
		return cwd, nil
	}
	// Fallback: walk up looking for internal/provider/manifest.go.
	dir := cwd
	for i := 0; i < 6; i++ {
		candidate := filepath.Join(dir, "internal", "provider")
		if _, err := os.Stat(filepath.Join(candidate, "manifest.go")); err == nil {
			return candidate, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return "", fmt.Errorf("cannot locate provider root from cwd %s", cwd)
}
