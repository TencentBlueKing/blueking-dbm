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
	"bytes"
	"strings"
	"testing"
)

func TestMigrateHelpUsesDataMode(t *testing.T) {
	var output bytes.Buffer
	MigrateCmd.SetOut(&output)
	MigrateCmd.SetErr(&output)
	t.Cleanup(func() {
		MigrateCmd.SetOut(nil)
		MigrateCmd.SetErr(nil)
	})

	if err := MigrateCmd.Help(); err != nil {
		t.Fatalf("render migrate help failed, errmsg: %s", err)
	}

	help := output.String()
	required := []string{
		"--type schema",
		"--type data",
		"--type all",
		"--inventory",
		"--inventory-full",
		"--repair-missing",
		"--repair-missing-schema",
		"--repair-missing-data",
	}
	for _, text := range required {
		if !strings.Contains(help, text) {
			t.Errorf("migrate help is missing %q", text)
		}
	}

	forbidden := []string{
		"--type strategy",
		"strategy (default global strategies only)",
		"only create default global strategies",
		"--repair-missing-tables",
		"--accept-missing-tables",
	}
	for _, text := range forbidden {
		if strings.Contains(help, text) {
			t.Errorf("migrate help still contains obsolete mode %q", text)
		}
	}
}

func TestMigrateRepairFlags(t *testing.T) {
	for _, name := range []string{"repair-missing", "repair-missing-schema", "repair-missing-data"} {
		if MigrateCmd.Flags().Lookup(name) == nil {
			t.Errorf("migrate flag is missing, flag: %s", name)
		}
	}
	for _, name := range []string{"repair-missing-tables", "accept-missing-tables"} {
		if MigrateCmd.Flags().Lookup(name) != nil {
			t.Errorf("migrate flag was not removed, flag: %s", name)
		}
	}
}

func TestInventoryFullHelpDoesNotRequireInventory(t *testing.T) {
	var output bytes.Buffer
	MigrateCmd.SetOut(&output)
	MigrateCmd.SetErr(&output)
	t.Cleanup(func() {
		MigrateCmd.SetOut(nil)
		MigrateCmd.SetErr(nil)
	})
	if err := MigrateCmd.Help(); err != nil {
		t.Fatal(err)
	}
	if strings.Contains(output.String(), "requires --inventory") {
		t.Fatal("help still requires --inventory together with --inventory-full")
	}
}
