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
	"errors"
	"strings"
	"testing"
)

func TestApplySchemaErrorKeepsCauseAndEndpoint(t *testing.T) {
	store := newTrackedStore("127.0.0.1:3306", testIdentity("u1"), &[]string{})
	cause := errors.New("load failed")
	store.loadErr = cause

	err := applySchema(store, Options{Type: MigrateTypeSchema})
	if !errors.Is(err, cause) {
		t.Fatalf("schema load error did not preserve cause, errmsg: %s", err)
	}
	assertErrorFields(t, err, "load schema snapshot failed", "endpoint: 127.0.0.1:3306")
}

func TestApplyStepErrorKeepsCauseEndpointAndVersion(t *testing.T) {
	store := newTrackedStore("127.0.0.1:3306", testIdentity("u1"), &[]string{})
	cause := errors.New("ddl failed")
	store.ddlErr = cause
	step := schemaSteps()[0]

	err := applyStep(store, Options{Type: MigrateTypeSchema}, step, false, false)
	if !errors.Is(err, cause) {
		t.Fatalf("schema DDL error did not preserve cause, errmsg: %s", err)
	}
	assertErrorFields(
		t,
		err,
		"apply schema DDL failed",
		"endpoint: 127.0.0.1:3306",
		"version: 1",
	)
}

func TestApplyStepRecordErrorKeepsCauseEndpointAndVersion(t *testing.T) {
	store := newTrackedStore("127.0.0.1:3306", testIdentity("u1"), &[]string{})
	step := schemaSteps()[0]
	if err := store.memStore.ExecDDL(step.Apply); err != nil {
		t.Fatal(err)
	}
	cause := errors.New("record failed")
	store.recordErr = cause

	err := applyStep(store, Options{Type: MigrateTypeSchema}, step, false, false)
	if !errors.Is(err, cause) {
		t.Fatalf("schema ledger error did not preserve cause, errmsg: %s", err)
	}
	assertErrorFields(
		t,
		err,
		"record schema ledger failed",
		"endpoint: 127.0.0.1:3306",
		"version: 1",
	)
}

func TestVerifyStepLoadErrorIsSingleLayer(t *testing.T) {
	store := newTrackedStore("127.0.0.1:3306", testIdentity("u1"), &[]string{})
	cause := errors.New("load failed")
	store.loadErr = cause
	step := schemaSteps()[0]

	err := verifyStep(store, step)
	if !errors.Is(err, cause) {
		t.Fatalf("verify load error did not preserve cause, errmsg: %s", err)
	}
	if strings.Count(err.Error(), "load schema snapshot failed") != 1 {
		t.Fatalf("verify load error wrapped more than once, errmsg: %s", err)
	}
	assertErrorFields(t, err, "endpoint: 127.0.0.1:3306", "version: 1", "errmsg: load failed")
}

func TestVerifyStepReportsMissingAndConflict(t *testing.T) {
	store := newTrackedStore("127.0.0.1:3306", testIdentity("u1"), &[]string{})
	step := schemaSteps()[0]
	err := verifyStep(store, step)
	assertErrorFields(t, err, "verify schema DDL failed", "endpoint: 127.0.0.1:3306", "result: missing")

	store.snap.Schema[step.Version] = Ledger{Version: step.Version, Name: "other"}
	err = verifyStep(store, step)
	assertErrorFields(t, err, "verify schema DDL failed", "result: conflict")
	if strings.Contains(err.Error(), "errmsg:") {
		t.Fatalf("verify conflict invented an error cause, errmsg: %s", err)
	}
}

func assertErrorFields(t *testing.T, err error, fields ...string) {
	t.Helper()
	for _, field := range fields {
		if !strings.Contains(err.Error(), field) {
			t.Fatalf("error missing field, field: %s, errmsg: %s", field, err)
		}
	}
}
