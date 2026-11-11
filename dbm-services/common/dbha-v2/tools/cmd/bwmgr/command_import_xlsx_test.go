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
	"archive/zip"
	"bytes"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

const (
	testCmdXlsxName       = "mapleleaf(591)mysql_cluster_20261104101251.xlsx"
	testCmdMalformedYAML  = "api: [\n"
	testCmdMutualXlsx     = "--create-template-from-xlsx cannot be used with"
	testCmdMutualOriginal = "create-template and create-template-from-list cannot be used together"
)

func writeCmdTestXlsx(t *testing.T, filePath string) {
	t.Helper()

	cell := func(ref string, value string) string {
		return `<c r="` + ref + `" t="inlineStr"><is><t>` + value + `</t></is></c>`
	}
	entries := map[string]string{
		"xl/workbook.xml": `<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" ` +
			`xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">` +
			`<sheets><sheet name="Sheet" sheetId="1" r:id="rId1"/></sheets></workbook>`,
		"xl/_rels/workbook.xml.rels": `<Relationships ` +
			`xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
			`<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>`,
		"xl/worksheets/sheet1.xml": `<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">` +
			`<sheetData><row r="1">` + cell("A1", "集群 ID") + cell("B1", "主域名") + cell("C1", "管控区域") +
			`</row><row r="2"><c r="A2"><v>1001</v></c>` + cell("B2", "a.example.db") +
			`<c r="C2"><v>0</v></c></row></sheetData></worksheet>`,
	}

	var buf bytes.Buffer
	writer := zip.NewWriter(&buf)
	for name, content := range entries {
		entry, err := writer.Create(name)
		if err != nil {
			t.Fatalf("create zip entry %s failed: %s", name, err)
		}
		if _, err := entry.Write([]byte(content)); err != nil {
			t.Fatalf("write zip entry %s failed: %s", name, err)
		}
	}
	if err := writer.Close(); err != nil {
		t.Fatalf("close zip failed: %s", err)
	}
	if err := os.WriteFile(filePath, buf.Bytes(), 0o644); err != nil {
		t.Fatalf("write xlsx failed: %s", err)
	}
}

func writeCmdMalformedConfig(t *testing.T, dir string) string {
	t.Helper()

	configPath := filepath.Join(dir, "bad.yaml")
	if err := os.WriteFile(configPath, []byte(testCmdMalformedYAML), 0o644); err != nil {
		t.Fatalf("write config failed: %s", err)
	}

	return configPath
}

func executeCmdTestRoot(t *testing.T, args ...string) (string, error) {
	t.Helper()

	var out bytes.Buffer
	rootCmd := newApp().newRootCmd()
	rootCmd.SetOut(&out)
	rootCmd.SetErr(io.Discard)
	rootCmd.SetArgs(args)
	err := rootCmd.Execute()

	return out.String(), err
}

func assertCmdError(t *testing.T, err error, want string) {
	t.Helper()

	if err == nil {
		t.Fatalf("error = nil, want %s", want)
	}
	if !strings.Contains(err.Error(), want) {
		t.Fatalf("error = %s, want contains %s", err, want)
	}
}

func TestImportCommandXlsxOptions(t *testing.T) {
	t.Parallel()

	cmd := newImportCmd(newApp())
	if xlsxFlagsChanged(cmd) {
		t.Fatalf("xlsx flags changed = true, want false")
	}
	for _, flag := range []flagSetting{
		{name: flagCreateTmplFromXlsx, value: "out.jsonl"},
		{name: flagXlsxFile, value: "in.xlsx"},
		{name: flagXlsxBkBizID, value: "7"},
		{name: flagXlsxSwitchVersion, value: "v1"},
		{name: flagXlsxStatus, value: "disabled"},
		{name: flagXlsxReport, value: "r.json"},
	} {
		if err := cmd.Flags().Set(flag.name, flag.value); err != nil {
			t.Fatalf("set flag %s failed: %s", flag.name, err)
		}
	}

	opts, err := newXlsxTemplateOptions(cmd)
	if err != nil {
		t.Fatalf("parse xlsx options failed: %s", err)
	}
	if opts.Output != "out.jsonl" || opts.XlsxFile != "in.xlsx" || opts.Report != "r.json" {
		t.Fatalf("paths = %s/%s/%s, want out.jsonl/in.xlsx/r.json", opts.Output, opts.XlsxFile, opts.Report)
	}
	if opts.BkBizID != 7 || !opts.BkBizIDSet || opts.SwitchVersion != "v1" || opts.Status != "disabled" {
		t.Fatalf("options = %+v, want biz 7 set, v1, disabled", opts)
	}
	if opts.Out == nil {
		t.Fatalf("out is nil, want command output")
	}
}

func TestImportCommandXlsxDefaults(t *testing.T) {
	t.Parallel()

	cmd := newImportCmd(newApp())
	if err := cmd.Flags().Set(flagCreateTmplFromXlsx, "out.jsonl"); err != nil {
		t.Fatalf("set flag failed: %s", err)
	}
	if !xlsxFlagsChanged(cmd) {
		t.Fatalf("xlsx flags changed = false, want true")
	}

	opts, err := newXlsxTemplateOptions(cmd)
	if err != nil {
		t.Fatalf("parse xlsx options failed: %s", err)
	}
	if opts.BkBizIDSet || opts.SwitchVersion != defaultSwitchVersion || opts.Status != defaultStatus {
		t.Fatalf("defaults = %+v, want biz unset, v2, enabled", opts)
	}
}

func TestImportCommandXlsxMutualExclusive(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	configPath := writeCmdMalformedConfig(t, dir)
	input := filepath.Join(dir, testCmdXlsxName)
	output := filepath.Join(dir, "out.jsonl")

	for _, other := range []string{flagCreateTmpl, flagCreateTmplFromList} {
		_, err := executeCmdTestRoot(t, "-c", configPath, "import", "--"+flagCreateTmplFromXlsx, output,
			"--"+flagXlsxFile, input, "--"+other, filepath.Join(dir, "other.jsonl"))
		assertCmdError(t, err, testCmdMutualXlsx)
	}

	_, err := executeCmdTestRoot(t, "-c", configPath, "import", "--"+flagCreateTmplFromXlsx, output,
		"--"+flagCreateTmpl, filepath.Join(dir, "a.jsonl"), "--"+flagCreateTmplFromList, filepath.Join(dir, "b.jsonl"))
	assertCmdError(t, err, testCmdMutualOriginal)
}

func TestImportCommandXlsxFlagsRequireTemplate(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	configPath := writeCmdMalformedConfig(t, dir)
	for _, args := range [][]string{
		{"--" + flagXlsxFile, "x.xlsx"},
		{"--" + flagXlsxReport, "r.json"},
		{"--" + flagXlsxBkBizID, "1"},
		{"--" + flagCreateTmplFromXlsx, ""},
	} {
		_, err := executeCmdTestRoot(t, append([]string{"-c", configPath, "import"}, args...)...)
		assertCmdError(t, err, errXlsxFlagsRequireTemplate)
	}
}

func TestImportCommandXlsxFileRequired(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	configPath := writeCmdMalformedConfig(t, dir)
	_, err := executeCmdTestRoot(t, "-c", configPath, "import", "--"+flagCreateTmplFromXlsx,
		filepath.Join(dir, "out.jsonl"))
	assertCmdError(t, err, "--xlsx-file is required")
}

func TestImportCommandXlsxOutputIsInput(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	configPath := writeCmdMalformedConfig(t, dir)
	input := filepath.Join(dir, testCmdXlsxName)
	writeCmdTestXlsx(t, input)
	before, err := os.ReadFile(input)
	if err != nil {
		t.Fatalf("read input failed: %s", err)
	}

	_, err = executeCmdTestRoot(t, "-c", configPath, "import", "--"+flagCreateTmplFromXlsx, input,
		"--"+flagXlsxFile, input)
	assertCmdError(t, err, "xlsx paths conflict")

	after, err := os.ReadFile(input)
	if err != nil || !bytes.Equal(before, after) {
		t.Fatalf("input changed = %v, want unchanged", err)
	}
}

func TestXlsxAcceptanceE6RootSkipsConfig(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	configPath := writeCmdMalformedConfig(t, dir)
	input := filepath.Join(dir, testCmdXlsxName)
	output := filepath.Join(dir, "out.jsonl")
	writeCmdTestXlsx(t, input)

	out, err := executeCmdTestRoot(t, "-c", configPath, "import", "--"+flagCreateTmplFromXlsx, output,
		"--"+flagXlsxFile, input)
	if err != nil {
		t.Fatalf("xlsx generation failed: %s", err)
	}
	if !strings.Contains(out, "result: PASS") {
		t.Fatalf("output = %s, want result: PASS", out)
	}

	content, err := os.ReadFile(output)
	want := `{"action":"add","bk_biz_id":591,"bk_cloud_id":0,"cluster_id":1001,` +
		`"cluster_name":"a.example.db","switch_version":"v2","status":"enabled"}` + "\n"
	if err != nil || string(content) != want {
		t.Fatalf("output file = %q/%v, want %q", content, err, want)
	}
}

func TestImportCommandWithoutXlsxLoadsConfig(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	configPath := writeCmdMalformedConfig(t, dir)
	template := filepath.Join(dir, "template.jsonl")

	_, err := executeCmdTestRoot(t, "-c", configPath, "import", "--"+flagCreateTmpl, template)
	assertCmdError(t, err, "failed to load config: failed to parse config")
	if _, statErr := os.Stat(template); !os.IsNotExist(statErr) {
		t.Fatalf("template exists = %v, want not created", statErr)
	}
}
