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

package migrator

import (
	"fmt"
	"strings"
	"testing"
)

// TestNoUnpublishedSchemaSteps keeps every model change frozen in published_steps.go,
// so a later release can never shift the version of a step that already shipped.
func TestNoUnpublishedSchemaSteps(t *testing.T) {
	added, err := appendedSchemaSteps(publishedSchemaSteps())
	if err != nil {
		t.Fatal(err)
	}
	if len(added) == 0 {
		return
	}

	var b strings.Builder
	for _, step := range added {
		fmt.Fprintf(&b, "\t\t{\n\t\t\tVersion: %d,\n\t\t\tName:    %q,\n\t\t\tTable:   %q,\n\t\t\tKind:    %s,\n",
			step.Version, step.Name, step.Table, kindLiteral(step.Kind))
		if step.Column != "" {
			fmt.Fprintf(&b, "\t\t\tColumn:  %q,\n", step.Column)
		}
		if step.Index != "" {
			fmt.Fprintf(&b, "\t\t\tIndex:   %q,\n", step.Index)
		}
		fmt.Fprintf(&b, "\t\t\tApply:   %q,\n\t\t},\n", step.Apply)
	}
	t.Fatalf("unpublished schema steps, freeze them into published_steps.go:\n%s", b.String())
}

// kindLiteral renders a step kind as its Go identifier.
func kindLiteral(kind objectKind) string {
	switch kind {
	case objectTable:
		return "objectTable"
	case objectColumn:
		return "objectColumn"
	case objectIndex:
		return "objectIndex"
	case objectColumnDef:
		return "objectColumnDef"
	case objectPrimaryKey:
		return "objectPrimaryKey"
	default:
		return "objectKind(-1)"
	}
}

func TestPublishedStepsMatchModel(t *testing.T) {
	if err := validatePublishedSteps(); err != nil {
		t.Fatal(err)
	}
	published := publishedSchemaSteps()
	steps := schemaSteps()
	byVersion := map[int64]schemaStep{}
	var indexAt, keyAt = -1, -1
	for i, step := range steps {
		if previous, ok := byVersion[step.Version]; ok && (previous.Name != step.Name || previous.Kind != step.Kind) {
			t.Fatalf("duplicate step version, version: %d", step.Version)
		}
		byVersion[step.Version] = step
		if step.Table == "t_db_switching_strategy" && step.Index == "idx_biz_event_reason" {
			indexAt = i
		}
		if step.Table == "t_db_switching_strategy" && step.Kind == objectPrimaryKey {
			keyAt = i
		}
	}
	for _, step := range published {
		got, ok := byVersion[step.Version]
		if !ok || got.Name != step.Name || got.Apply != step.Apply || got.Kind != step.Kind {
			t.Fatalf("published step changed, version: %d, name: %s", step.Version, step.Name)
		}
	}
	if indexAt < 0 {
		t.Fatal("strategy event unique index step is missing")
	}
	indexStep := steps[indexAt]
	if indexStep.Version != 223 || indexStep.Kind != objectIndex ||
		indexStep.Name != "000223_t_db_switching_strategy_idx_biz_event_reason" {
		t.Fatalf("strategy event unique index step changed, version: %d, name: %s", indexStep.Version, indexStep.Name)
	}
	if !strings.Contains(indexStep.Apply, "UNIQUE INDEX `idx_biz_event_reason`") {
		t.Fatal("strategy event unique index sql changed")
	}
	if indexAt < 0 || keyAt < 0 || indexAt > keyAt {
		t.Fatalf("unique index must run before primary key convergence, index: %d, key: %d", indexAt, keyAt)
	}
}

func TestHistoricalTargetKeepsFrozenApply(t *testing.T) {
	spec, ok := tableByName("t_db_switching_snapshot_log")
	if !ok {
		t.Fatal("snapshot table is not managed")
	}
	spec.Columns = append([]columnSpec{}, spec.Columns...)
	for i := range spec.Columns {
		if spec.Columns[i].Name == "result" {
			spec.Columns[i].Target.DataType = "longtext"
		}
	}
	columns := publishedColumns()
	for _, step := range publishedSchemaSteps() {
		if step.Table != spec.Name || (step.Kind != objectTable && step.Column != "result") {
			continue
		}
		want, matched := expectedPublishedApply(spec, step, columns)
		if !matched || want != step.Apply {
			t.Fatalf("historical target changed published apply, version: %d", step.Version)
		}
	}
}
