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

package handler

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/tools/internal/bwmgr"
)

func TestAddDefaultInsertsOnly(t *testing.T) {
	t.Parallel()

	service := &fakeBlackWhiteListService{insertID: 7}
	h := NewHandlerWithService(0, service)
	if _, err := h.addEntry(validAddOptions(false)); err != nil {
		t.Fatalf("add entry failed: %s", err)
	}

	if service.getCalls != 0 {
		t.Fatalf("get calls = %d, want 0", service.getCalls)
	}
	if len(service.insertRequests) != 1 || len(service.updateRequests) != 0 {
		t.Fatalf("insert/update calls = %d/%d, want 1/0", len(service.insertRequests), len(service.updateRequests))
	}
}

func TestAddUpsertUpdatesExisting(t *testing.T) {
	t.Parallel()

	service := &fakeBlackWhiteListService{getItems: []bwmgr.BlackWhiteListItem{{ID: 11}}}
	h := NewHandlerWithService(0, service)
	result, err := h.addEntry(validAddOptions(true))
	if err != nil {
		t.Fatalf("add entry failed: %s", err)
	}

	if !result.Updated || len(service.updateRequests) != 1 {
		t.Fatalf("updated = %v, update calls = %d, want true/1", result.Updated, len(service.updateRequests))
	}
	if got := service.updateRequests[0].SetArgs.ClusterName; got == nil || *got != "cluster-a" {
		t.Fatalf("cluster name set arg = %v, want cluster-a", got)
	}
}

func TestAddUpsertExplicitClusterNameDoesNotWriteDefaultFields(t *testing.T) {
	t.Parallel()

	service := &fakeBlackWhiteListService{getItems: []bwmgr.BlackWhiteListItem{{ID: 11}}}
	h := NewHandlerWithService(0, service)
	opts := validAddOptions(true)
	opts.SwitchVersionSet = false
	opts.StatusSet = false

	if _, err := h.addEntry(opts); err != nil {
		t.Fatalf("add entry failed: %s", err)
	}

	if len(service.updateRequests) != 1 {
		t.Fatalf("update calls = %d, want 1", len(service.updateRequests))
	}
	setArgs := service.updateRequests[0].SetArgs
	if setArgs.ClusterName == nil || *setArgs.ClusterName != "cluster-a" {
		t.Fatalf("cluster name set arg = %v, want cluster-a", setArgs.ClusterName)
	}
	if setArgs.SwitchVersion != nil || setArgs.Status != nil {
		t.Fatalf("switch/status set args = %v/%v, want nil/nil", setArgs.SwitchVersion, setArgs.Status)
	}
}

func TestAddUpsertRejectsEmptyClusterName(t *testing.T) {
	t.Parallel()

	service := &fakeBlackWhiteListService{getItems: []bwmgr.BlackWhiteListItem{{ID: 11}}}
	h := NewHandlerWithService(0, service)
	opts := validAddOptions(true)
	opts.ClusterName = ""
	opts.SwitchVersionSet = false
	opts.StatusSet = false

	err := func() error {
		_, err := h.addEntry(opts)
		return err
	}()
	if err == nil {
		t.Fatalf("add entry succeeded, want empty cluster name error")
	}
	if !strings.Contains(err.Error(), errClusterNameRequired) {
		t.Fatalf("add entry error = %s, want %s", err, errClusterNameRequired)
	}
	if len(service.updateRequests) != 0 {
		t.Fatalf("update calls = %d, want 0", len(service.updateRequests))
	}
}

func TestAddUpsertRequiresExplicitUpdateField(t *testing.T) {
	t.Parallel()

	service := &fakeBlackWhiteListService{getItems: []bwmgr.BlackWhiteListItem{{ID: 11}}}
	h := NewHandlerWithService(0, service)
	opts := validAddOptions(true)
	opts.ClusterNameSet = false
	opts.SwitchVersionSet = false
	opts.StatusSet = false

	err := func() error {
		_, err := h.addEntry(opts)
		return err
	}()
	if err == nil {
		t.Fatalf("add entry succeeded, want explicit update field error")
	}
	if !strings.Contains(err.Error(), errAddUpsertSetRequired) {
		t.Fatalf("add entry error = %s, want %s", err, errAddUpsertSetRequired)
	}
	if len(service.updateRequests) != 0 {
		t.Fatalf("update calls = %d, want 0", len(service.updateRequests))
	}
}

func TestAddUpsertRiskyUpdateRequiresConfirmation(t *testing.T) {
	t.Parallel()

	confirmed := false
	service := &fakeBlackWhiteListService{getItems: []bwmgr.BlackWhiteListItem{{ID: 11}}}
	h := NewHandlerWithService(0, service)
	opts := validAddOptions(true)
	opts.Status = string(bwmgr.StatusDisabled)
	opts.ClusterNameSet = false
	opts.SwitchVersionSet = false
	opts.Confirm = func(string) bool {
		confirmed = true
		return false
	}

	if _, err := h.addEntry(opts); err == nil {
		t.Fatalf("add entry succeeded, want confirmation error")
	}
	if !confirmed {
		t.Fatalf("confirm was not called for risky upsert")
	}
	if len(service.updateRequests) != 0 {
		t.Fatalf("update calls = %d, want 0", len(service.updateRequests))
	}
}

func TestAddUpsertRiskyUpdateSkipsConfirmationWithYes(t *testing.T) {
	t.Parallel()

	service := &fakeBlackWhiteListService{getItems: []bwmgr.BlackWhiteListItem{{ID: 11}}}
	h := NewHandlerWithService(0, service)
	opts := validAddOptions(true)
	opts.Status = string(bwmgr.StatusDisabled)
	opts.ClusterNameSet = false
	opts.SwitchVersionSet = false
	opts.Yes = true
	opts.Confirm = func(string) bool {
		t.Fatalf("confirm should not be called when yes is true")
		return false
	}

	if _, err := h.addEntry(opts); err != nil {
		t.Fatalf("add entry failed: %s", err)
	}
	if len(service.updateRequests) != 1 {
		t.Fatalf("update calls = %d, want 1", len(service.updateRequests))
	}
}

func TestAddUpsertSwitchVersionV1RequiresConfirmation(t *testing.T) {
	t.Parallel()

	confirmed := false
	service := &fakeBlackWhiteListService{getItems: []bwmgr.BlackWhiteListItem{{ID: 11}}}
	h := NewHandlerWithService(0, service)
	opts := validAddOptions(true)
	opts.SwitchVersion = string(bwmgr.SwitchVersionV1)
	opts.ClusterNameSet = false
	opts.StatusSet = false
	opts.Confirm = func(string) bool {
		confirmed = true
		return false
	}

	if _, err := h.addEntry(opts); err == nil {
		t.Fatalf("add entry succeeded, want confirmation error")
	}
	if !confirmed {
		t.Fatalf("confirm was not called for risky switch version")
	}
	if len(service.updateRequests) != 0 {
		t.Fatalf("update calls = %d, want 0", len(service.updateRequests))
	}
}

func TestAddUpsertNonRiskyUpdateDoesNotConfirm(t *testing.T) {
	t.Parallel()

	service := &fakeBlackWhiteListService{getItems: []bwmgr.BlackWhiteListItem{{ID: 11}}}
	h := NewHandlerWithService(0, service)
	opts := validAddOptions(true)
	opts.SwitchVersionSet = false
	opts.StatusSet = false
	opts.Confirm = func(string) bool {
		t.Fatalf("confirm should not be called for non-risky upsert")
		return false
	}

	if _, err := h.addEntry(opts); err != nil {
		t.Fatalf("add entry failed: %s", err)
	}
	if len(service.updateRequests) != 1 {
		t.Fatalf("update calls = %d, want 1", len(service.updateRequests))
	}
}

func TestAddUpsertConflict(t *testing.T) {
	t.Parallel()

	service := &fakeBlackWhiteListService{
		getItems: []bwmgr.BlackWhiteListItem{{ID: 11}, {ID: 12}},
	}
	h := NewHandlerWithService(0, service)
	if _, err := h.addEntry(validAddOptions(true)); err == nil {
		t.Fatalf("add entry succeeded, want conflict error")
	}
}

func TestImportCreateTemplate(t *testing.T) {
	t.Parallel()

	outputFile := filepath.Join(t.TempDir(), "template.jsonl")
	h := NewHandlerWithService(0, &fakeBlackWhiteListService{})
	if err := h.Import(ImportOptions{CreateTemplate: outputFile}); err != nil {
		t.Fatalf("create template failed: %s", err)
	}

	content, err := os.ReadFile(outputFile)
	if err != nil {
		t.Fatalf("read template failed: %s", err)
	}
	if got := string(content); !strings.Contains(got, `"action":"add"`) ||
		!strings.Contains(got, `"action":"update"`) || !strings.Contains(got, `"action":"delete"`) {
		t.Fatalf("template content = %q, want add/update/delete examples", got)
	}

	lines := strings.Split(strings.TrimSpace(string(content)), "\n")
	if len(lines) != 3 {
		t.Fatalf("template line count = %d, want 3", len(lines))
	}
	for _, line := range lines {
		var record map[string]any
		if err := json.Unmarshal([]byte(line), &record); err != nil {
			t.Fatalf("parse template line %q failed: %s", line, err)
		}
		if record["action"] == "" {
			t.Fatalf("template line %q missing action", line)
		}
	}
}

func TestImportCreateTemplateFromList(t *testing.T) {
	t.Parallel()

	outputFile := filepath.Join(t.TempDir(), "template-from-list.jsonl")
	service := &fakeBlackWhiteListService{getItems: sampleBlackWhiteListItems()}
	h := NewHandlerWithService(0, service)
	if err := h.Import(ImportOptions{CreateTemplateFromList: outputFile}); err != nil {
		t.Fatalf("create template from list failed: %s", err)
	}

	if service.getCalls != 1 {
		t.Fatalf("get calls = %d, want 1", service.getCalls)
	}
	if len(service.insertRequests) != 0 || len(service.updateRequests) != 0 || len(service.deleteRequests) != 0 {
		t.Fatalf(
			"insert/update/delete calls = %d/%d/%d, want 0/0/0",
			len(service.insertRequests),
			len(service.updateRequests),
			len(service.deleteRequests),
		)
	}

	content, err := os.ReadFile(outputFile)
	if err != nil {
		t.Fatalf("read template failed: %s", err)
	}

	lines := strings.Split(strings.TrimSpace(string(content)), "\n")
	if len(lines) != 2 {
		t.Fatalf("template line count = %d, want 2", len(lines))
	}

	var record importExportUpdateRecord
	if err := json.Unmarshal([]byte(lines[0]), &record); err != nil {
		t.Fatalf("parse template line failed: %s", err)
	}
	if record.Action != importActionUpdate || record.ID != 11 || record.ClusterName != "cluster-a" {
		t.Fatalf("first record = %+v, want update id 11 cluster-a", record)
	}
	if record.SwitchVersion != string(bwmgr.SwitchVersionV2) || record.Status != string(bwmgr.StatusEnabled) {
		t.Fatalf("first record switch/status = %s/%s, want v2/enabled", record.SwitchVersion, record.Status)
	}
}

func TestImportCreateTemplateFromListEmpty(t *testing.T) {
	t.Parallel()

	outputFile := filepath.Join(t.TempDir(), "empty-template.jsonl")
	service := &fakeBlackWhiteListService{}
	h := NewHandlerWithService(0, service)
	if err := h.Import(ImportOptions{CreateTemplateFromList: outputFile}); err != nil {
		t.Fatalf("create empty template from list failed: %s", err)
	}

	content, err := os.ReadFile(outputFile)
	if err != nil {
		t.Fatalf("read template failed: %s", err)
	}
	if len(content) != 0 {
		t.Fatalf("template content = %q, want empty file", string(content))
	}
}

func TestImportCreateTemplateFromListDryRunImportable(t *testing.T) {
	t.Parallel()

	outputFile := filepath.Join(t.TempDir(), "template-from-list.jsonl")
	service := &fakeBlackWhiteListService{getItems: sampleBlackWhiteListItems()}
	h := NewHandlerWithService(0, service)
	if err := h.Import(ImportOptions{CreateTemplateFromList: outputFile}); err != nil {
		t.Fatalf("create template from list failed: %s", err)
	}

	if err := h.Import(ImportOptions{File: outputFile, DryRun: true}); err != nil {
		t.Fatalf("dry run imported exported template failed: %s", err)
	}
}

func TestImportCreateTemplateMutualExclusion(t *testing.T) {
	t.Parallel()

	h := NewHandlerWithService(0, &fakeBlackWhiteListService{})
	err := h.Import(ImportOptions{
		CreateTemplate:         "empty.jsonl",
		CreateTemplateFromList: "from-list.jsonl",
	})
	if err == nil {
		t.Fatalf("import succeeded, want mutual exclusion error")
	}
	if !strings.Contains(err.Error(), errImportTemplateMutualExclusive) {
		t.Fatalf("import error = %s, want %s", err, errImportTemplateMutualExclusive)
	}
}

func TestImportDryRunDoesNotCallService(t *testing.T) {
	t.Parallel()

	service := &fakeBlackWhiteListService{}
	h := NewHandlerWithService(0, service)
	if err := h.Import(ImportOptions{File: writeImportFile(t), DryRun: true}); err != nil {
		t.Fatalf("dry run import failed: %s", err)
	}

	if service.totalCalls() != 0 {
		t.Fatalf("service calls = %d, want 0", service.totalCalls())
	}
}

func TestImportDispatchesRecords(t *testing.T) {
	t.Parallel()

	service := &fakeBlackWhiteListService{insertID: 7, updateRows: 2, deleteRows: 3}
	h := NewHandlerWithService(0, service)
	if err := h.Import(ImportOptions{File: writeImportFile(t), Yes: true}); err != nil {
		t.Fatalf("import failed: %s", err)
	}

	if len(service.insertRequests) != 1 || len(service.updateRequests) != 1 || len(service.deleteRequests) != 1 {
		t.Fatalf(
			"insert/update/delete calls = %d/%d/%d, want 1/1/1",
			len(service.insertRequests),
			len(service.updateRequests),
			len(service.deleteRequests),
		)
	}
}

func TestImportUpsertAddUpdatesExisting(t *testing.T) {
	t.Parallel()

	service := &fakeBlackWhiteListService{getItems: []bwmgr.BlackWhiteListItem{{ID: 9}}, updateRows: 1}
	h := NewHandlerWithService(0, service)
	if err := h.Import(ImportOptions{File: writeImportAddFile(t), Upsert: true, Yes: true}); err != nil {
		t.Fatalf("upsert import failed: %s", err)
	}

	if len(service.insertRequests) != 0 || len(service.updateRequests) != 1 {
		t.Fatalf("insert/update calls = %d/%d, want 0/1", len(service.insertRequests), len(service.updateRequests))
	}
	setArgs := service.updateRequests[0].SetArgs
	if setArgs.ClusterName == nil || setArgs.SwitchVersion == nil || setArgs.Status == nil {
		t.Fatalf("import add set args = %+v, want all add fields", setArgs)
	}
}

func TestImportUpsertRejectsEmptyClusterName(t *testing.T) {
	t.Parallel()

	service := &fakeBlackWhiteListService{getItems: []bwmgr.BlackWhiteListItem{{ID: 9}}, updateRows: 1}
	h := NewHandlerWithService(0, service)
	err := h.Import(ImportOptions{File: writeImportAddEmptyClusterFile(t), Upsert: true, Yes: true})
	if err == nil {
		t.Fatalf("upsert import succeeded, want empty cluster name error")
	}
	if !strings.Contains(err.Error(), "cluster_name is required") {
		t.Fatalf("upsert import error = %s, want cluster_name is required", err)
	}
	if len(service.updateRequests) != 0 {
		t.Fatalf("update calls = %d, want 0", len(service.updateRequests))
	}
}

func TestImportUpsertAddDoesNotRepeatConfirmation(t *testing.T) {
	t.Parallel()

	confirmCalls := 0
	service := &fakeBlackWhiteListService{getItems: []bwmgr.BlackWhiteListItem{{ID: 9}}, updateRows: 1}
	h := NewHandlerWithService(0, service)
	opts := ImportOptions{
		File:   writeImportAddDisabledFile(t),
		Upsert: true,
		Confirm: func(string) bool {
			confirmCalls++
			return true
		},
	}

	if err := h.Import(opts); err != nil {
		t.Fatalf("upsert import failed: %s", err)
	}
	if confirmCalls != 1 {
		t.Fatalf("confirm calls = %d, want 1", confirmCalls)
	}
	if len(service.updateRequests) != 1 {
		t.Fatalf("update calls = %d, want 1", len(service.updateRequests))
	}
}

func TestImportUpdateSetsClusterName(t *testing.T) {
	t.Parallel()

	service := &fakeBlackWhiteListService{}
	h := NewHandlerWithService(0, service)
	if err := h.Import(ImportOptions{File: writeImportUpdateClusterFile(t), Yes: true}); err != nil {
		t.Fatalf("import update failed: %s", err)
	}

	if len(service.updateRequests) != 1 {
		t.Fatalf("update calls = %d, want 1", len(service.updateRequests))
	}
	if got := service.updateRequests[0].SetArgs.ClusterName; got == nil || *got != "cluster-b" {
		t.Fatalf("set cluster name = %v, want cluster-b", got)
	}
	if got := service.updateRequests[0].QueryArgs.ClusterName; got != nil {
		t.Fatalf("query cluster name = %v, want nil", got)
	}
}

func TestImportRequiresConfirmation(t *testing.T) {
	t.Parallel()

	service := &fakeBlackWhiteListService{}
	h := NewHandlerWithService(0, service)
	opts := ImportOptions{File: writeImportFile(t), Confirm: func(string) bool { return false }}
	err := h.Import(opts)
	if err == nil {
		t.Fatalf("import succeeded, want confirmation error")
	}
	if !strings.Contains(err.Error(), errImportCancelled) {
		t.Fatalf("import error = %s, want %s", err, errImportCancelled)
	}

	if service.totalCalls() != 0 {
		t.Fatalf("service calls = %d, want 0", service.totalCalls())
	}
}

func TestImportInvalidInput(t *testing.T) {
	t.Parallel()

	h := NewHandlerWithService(0, &fakeBlackWhiteListService{})
	if err := h.Import(ImportOptions{File: writeImportFileWithLines(t, `{"action":"noop"}`), DryRun: true}); err == nil {
		t.Fatalf("import succeeded, want invalid action error")
	}
}

func TestImportValidationErrorIncludesLineNumber(t *testing.T) {
	t.Parallel()

	h := NewHandlerWithService(0, &fakeBlackWhiteListService{})
	err := h.Import(ImportOptions{
		File:   writeImportFileWithLines(t, `{"action":"update","id":11}`),
		DryRun: true,
	})
	if err == nil {
		t.Fatalf("import succeeded, want validation error")
	}
	if !strings.Contains(err.Error(), "import line 1") {
		t.Fatalf("import error = %s, want line number", err)
	}
}

func validAddOptions(upsert bool) AddOptions {
	return AddOptions{
		BkBizID:          1,
		BkCloudID:        0,
		ClusterID:        100,
		ClusterName:      "cluster-a",
		SwitchVersion:    string(bwmgr.SwitchVersionV2),
		Status:           string(bwmgr.StatusEnabled),
		Upsert:           upsert,
		ClusterNameSet:   true,
		SwitchVersionSet: true,
		StatusSet:        true,
	}
}

func writeImportFile(t *testing.T) string {
	t.Helper()

	return writeImportFileWithLines(
		t,
		`{"action":"add","bk_biz_id":1,"bk_cloud_id":0,"cluster_id":100,`+
			`"cluster_name":"cluster-a","switch_version":"v2","status":"enabled"}`,
		`{"action":"update","id":11,"switch_version":"v1","status":"disabled"}`,
		`{"action":"delete","id":12}`,
	)
}

func writeImportAddFile(t *testing.T) string {
	t.Helper()

	return writeImportFileWithLines(
		t,
		`{"action":"add","bk_biz_id":1,"bk_cloud_id":0,"cluster_id":100,`+
			`"cluster_name":"cluster-a","switch_version":"v2","status":"enabled"}`,
	)
}

func writeImportAddEmptyClusterFile(t *testing.T) string {
	t.Helper()

	return writeImportFileWithLines(
		t,
		`{"action":"add","bk_biz_id":1,"bk_cloud_id":0,"cluster_id":100,`+
			`"cluster_name":"","switch_version":"v2","status":"enabled"}`,
	)
}

func writeImportAddDisabledFile(t *testing.T) string {
	t.Helper()

	return writeImportFileWithLines(
		t,
		`{"action":"add","bk_biz_id":1,"bk_cloud_id":0,"cluster_id":100,`+
			`"cluster_name":"cluster-a","switch_version":"v2","status":"disabled"}`,
	)
}

func writeImportUpdateClusterFile(t *testing.T) string {
	t.Helper()

	return writeImportFileWithLines(t, `{"action":"update","id":11,"set_cluster_name":"cluster-b"}`)
}

func writeImportFileWithLines(t *testing.T, lines ...string) string {
	t.Helper()

	filePath := filepath.Join(t.TempDir(), "import.jsonl")
	content := strings.Join(lines, "\n") + "\n"
	if err := os.WriteFile(filePath, []byte(content), 0o644); err != nil {
		t.Fatalf("write import file failed: %s", err)
	}

	return filePath
}

func sampleBlackWhiteListItems() []bwmgr.BlackWhiteListItem {
	return []bwmgr.BlackWhiteListItem{
		{
			ID:            11,
			BkBizID:       1,
			BkCloudID:     0,
			ClusterID:     100,
			ClusterName:   "cluster-a",
			SwitchVersion: bwmgr.SwitchVersionV2,
			Status:        bwmgr.StatusEnabled,
		},
		{
			ID:            12,
			BkBizID:       2,
			BkCloudID:     0,
			ClusterID:     200,
			ClusterName:   "cluster-b",
			SwitchVersion: bwmgr.SwitchVersionV1,
			Status:        bwmgr.StatusDisabled,
		},
	}
}

type fakeBlackWhiteListService struct {
	getItems       []bwmgr.BlackWhiteListItem
	insertID       uint
	updateRows     int
	deleteRows     int
	getCalls       int
	insertRequests []bwmgr.InsertBlackWhiteListRequest
	updateRequests []bwmgr.UpdateBlackWhiteListRequest
	deleteRequests []bwmgr.DeleteBlackWhiteListRequest
}

func (s *fakeBlackWhiteListService) GetBlackWhiteList(
	_ int,
	_ *bwmgr.GetBlackWhiteListRequest,
) ([]bwmgr.BlackWhiteListItem, error) {
	s.getCalls++
	return s.getItems, nil
}

func (s *fakeBlackWhiteListService) InsertBlackWhiteList(
	_ int,
	_ bwmgr.InsertBlackWhiteListRequest,
) (uint, error) {
	s.insertRequests = append(s.insertRequests, bwmgr.InsertBlackWhiteListRequest{})
	return s.insertID, nil
}

func (s *fakeBlackWhiteListService) UpdateBlackWhiteList(
	_ int,
	req bwmgr.UpdateBlackWhiteListRequest,
) (int, error) {
	s.updateRequests = append(s.updateRequests, req)
	if s.updateRows > 0 {
		return s.updateRows, nil
	}

	return 1, nil
}

func (s *fakeBlackWhiteListService) DeleteBlackWhiteList(
	_ int,
	req bwmgr.DeleteBlackWhiteListRequest,
) (int, error) {
	s.deleteRequests = append(s.deleteRequests, req)
	if s.deleteRows > 0 {
		return s.deleteRows, nil
	}

	return 1, nil
}

func (s *fakeBlackWhiteListService) totalCalls() int {
	return s.getCalls + len(s.insertRequests) + len(s.updateRequests) + len(s.deleteRequests)
}
