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

import "testing"

func TestAddCommandUpsertOption(t *testing.T) {
	t.Parallel()

	cmd := newAddCmd(newApp())
	for _, flag := range []flagSetting{
		{name: flagClusterID, value: "1"},
		{name: flagYes, value: "true"},
		{name: flagUpsert, value: "true"},
		{name: flagBkBizID, value: "2"},
	} {
		if err := cmd.Flags().Set(flag.name, flag.value); err != nil {
			t.Fatalf("set flag %s failed: %s", flag.name, err)
		}
	}

	opts, err := newAddOptions(cmd)
	if err != nil {
		t.Fatalf("parse add options failed: %s", err)
	}
	if !opts.Upsert {
		t.Fatalf("upsert = false, want true")
	}
	if !opts.Yes {
		t.Fatalf("yes = false, want true")
	}
	if opts.Confirm == nil {
		t.Fatalf("confirm is nil, want default confirm function")
	}
	if opts.ClusterNameSet || opts.SwitchVersionSet || opts.StatusSet {
		t.Fatalf(
			"explicit flags cluster/switch/status = %v/%v/%v, want false/false/false",
			opts.ClusterNameSet,
			opts.SwitchVersionSet,
			opts.StatusSet,
		)
	}
}

func TestAddCommandExplicitFieldOptions(t *testing.T) {
	t.Parallel()

	cmd := newAddCmd(newApp())
	for _, flag := range []flagSetting{
		{name: flagClusterName, value: "cluster-a"},
		{name: flagSwitchVersion, value: "v1"},
		{name: flagStatus, value: "disabled"},
	} {
		if err := cmd.Flags().Set(flag.name, flag.value); err != nil {
			t.Fatalf("set flag %s failed: %s", flag.name, err)
		}
	}

	opts, err := newAddOptions(cmd)
	if err != nil {
		t.Fatalf("parse add options failed: %s", err)
	}
	if !opts.ClusterNameSet || !opts.SwitchVersionSet || !opts.StatusSet {
		t.Fatalf(
			"explicit flags cluster/switch/status = %v/%v/%v, want true/true/true",
			opts.ClusterNameSet,
			opts.SwitchVersionSet,
			opts.StatusSet,
		)
	}
}

func TestImportCommandOptions(t *testing.T) {
	t.Parallel()

	cmd := newImportCmd(newApp())
	for _, flag := range []flagSetting{
		{name: flagYes, value: "true"},
		{name: flagFile, value: "import.jsonl"},
		{name: flagUpsert, value: "true"},
		{name: flagDryRun, value: "true"},
		{name: flagCreateTmpl, value: "template.jsonl"},
	} {
		if err := cmd.Flags().Set(flag.name, flag.value); err != nil {
			t.Fatalf("set flag %s failed: %s", flag.name, err)
		}
	}

	opts, err := newImportOptions(cmd)
	if err != nil {
		t.Fatalf("parse import options failed: %s", err)
	}
	if opts.File != "import.jsonl" || opts.CreateTemplate != "template.jsonl" {
		t.Fatalf("import paths = %s/%s, want import.jsonl/template.jsonl", opts.File, opts.CreateTemplate)
	}
	if !opts.DryRun || !opts.Upsert || !opts.Yes {
		t.Fatalf("flags dry-run/upsert/yes = %v/%v/%v, want true/true/true", opts.DryRun, opts.Upsert, opts.Yes)
	}
	if opts.Confirm == nil {
		t.Fatalf("confirm is nil, want default confirm function")
	}
}

func TestImportCommandCreateTemplateFromListOption(t *testing.T) {
	t.Parallel()

	cmd := newImportCmd(newApp())
	if err := cmd.Flags().Set(flagCreateTmplFromList, "from-list.jsonl"); err != nil {
		t.Fatalf("set flag %s failed: %s", flagCreateTmplFromList, err)
	}

	opts, err := newImportOptions(cmd)
	if err != nil {
		t.Fatalf("parse import options failed: %s", err)
	}
	if opts.CreateTemplateFromList != "from-list.jsonl" {
		t.Fatalf("create template from list = %s, want from-list.jsonl", opts.CreateTemplateFromList)
	}
}
