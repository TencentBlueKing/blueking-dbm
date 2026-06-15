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
	"testing"

	"dbm-services/common/dbha-v2/tools/internal/bwmgr/handler"
)

func TestCommandOptionsDefaultBkCloudID(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		newCmd    func(*app) commandWithOptions
		cloudID   func(commandWithOptions) int
		wantValue int
	}{
		{
			name: "list",
			newCmd: func(a *app) commandWithOptions {
				cmd := newListCmd(a)
				opts, err := newListOptions(cmd)
				return commandWithOptions{err: err, listOptions: opts}
			},
			cloudID: func(result commandWithOptions) int {
				return result.listOptions.BkCloudID
			},
			wantValue: defaultIntValue,
		},
		{
			name: "update",
			newCmd: func(a *app) commandWithOptions {
				cmd := newUpdateCmd(a)
				opts, err := newUpdateOptions(cmd)
				return commandWithOptions{err: err, updateOptions: opts}
			},
			cloudID: func(result commandWithOptions) int {
				return result.updateOptions.BkCloudID
			},
			wantValue: defaultIntValue,
		},
		{
			name: "delete",
			newCmd: func(a *app) commandWithOptions {
				cmd := newDeleteCmd(a)
				opts, err := newDeleteOptions(cmd)
				return commandWithOptions{err: err, deleteOptions: opts}
			},
			cloudID: func(result commandWithOptions) int {
				return result.deleteOptions.BkCloudID
			},
			wantValue: defaultIntValue,
		},
		{
			name: "add",
			newCmd: func(a *app) commandWithOptions {
				cmd := newAddCmd(a)
				opts, err := newAddOptions(cmd)
				return commandWithOptions{err: err, addOptions: opts}
			},
			cloudID: func(result commandWithOptions) int {
				return result.addOptions.BkCloudID
			},
			wantValue: defaultIntValue,
		},
	}

	for _, tc := range tests {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			result := tc.newCmd(newApp())
			if result.err != nil {
				t.Fatalf("parse options failed: %s", result.err)
			}

			if got := tc.cloudID(result); got != tc.wantValue {
				t.Fatalf("bk cloud id = %d, want %d", got, tc.wantValue)
			}
		})
	}
}

func TestListCommandOutputOptions(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name           string
		flags          map[string]string
		wantOutput     string
		wantOutputFile string
	}{
		{
			name:       "default table",
			wantOutput: handler.OutputFormatTable,
		},
		{
			name: "json",
			flags: map[string]string{
				flagOutput: handler.OutputFormatJSON,
			},
			wantOutput: handler.OutputFormatJSON,
		},
		{
			name: "output file",
			flags: map[string]string{
				flagOutputFile: "list.jsonl",
			},
			wantOutput:     handler.OutputFormatTable,
			wantOutputFile: "list.jsonl",
		},
	}

	for _, tc := range tests {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			cmd := newListCmd(newApp())
			for name, value := range tc.flags {
				if err := cmd.Flags().Set(name, value); err != nil {
					t.Fatalf("set flag %s failed: %s", name, err)
				}
			}

			opts, err := newListOptions(cmd)
			if err != nil {
				t.Fatalf("parse options failed: %s", err)
			}

			if opts.Output != tc.wantOutput {
				t.Fatalf("output = %s, want %s", opts.Output, tc.wantOutput)
			}
			if opts.OutputFile != tc.wantOutputFile {
				t.Fatalf("output file = %s, want %s", opts.OutputFile, tc.wantOutputFile)
			}
		})
	}
}

func TestListCommandOutputFileKeepsPathWithAnyOutputOrder(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		flags      []flagSetting
		wantOutput string
	}{
		{
			name:       "output file only",
			wantOutput: handler.OutputFormatTable,
			flags: []flagSetting{
				{name: flagOutputFile, value: "list.jsonl"},
			},
		},
		{
			name:       "json before output file",
			wantOutput: handler.OutputFormatJSON,
			flags: []flagSetting{
				{name: flagOutput, value: handler.OutputFormatJSON},
				{name: flagOutputFile, value: "list.jsonl"},
			},
		},
		{
			name:       "output file before json",
			wantOutput: handler.OutputFormatJSON,
			flags: []flagSetting{
				{name: flagOutputFile, value: "list.jsonl"},
				{name: flagOutput, value: handler.OutputFormatJSON},
			},
		},
		{
			name:       "table with output file",
			wantOutput: handler.OutputFormatTable,
			flags: []flagSetting{
				{name: flagOutput, value: handler.OutputFormatTable},
				{name: flagOutputFile, value: "list.jsonl"},
			},
		},
		{
			name:       "invalid output still parses",
			wantOutput: "yaml",
			flags: []flagSetting{
				{name: flagOutput, value: "yaml"},
				{name: flagOutputFile, value: "list.jsonl"},
			},
		},
	}

	for _, tc := range tests {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			cmd := newListCmd(newApp())
			for _, flag := range tc.flags {
				if err := cmd.Flags().Set(flag.name, flag.value); err != nil {
					t.Fatalf("set flag %s failed: %s", flag.name, err)
				}
			}

			opts, err := newListOptions(cmd)
			if err != nil {
				t.Fatalf("parse options failed: %s", err)
			}

			if opts.Output != tc.wantOutput {
				t.Fatalf("output = %s, want %s", opts.Output, tc.wantOutput)
			}
			if opts.OutputFile != "list.jsonl" {
				t.Fatalf("output file = %s, want list.jsonl", opts.OutputFile)
			}
		})
	}
}

func TestFilterCommandOptionsAllowExplicitDirectCloudID(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name    string
		newCmd  func(*app) commandWithOptions
		cloudID func(commandWithOptions) int
	}{
		{
			name: "list",
			newCmd: func(a *app) commandWithOptions {
				cmd := newListCmd(a)
				if err := cmd.Flags().Set(flagBkCloudID, "0"); err != nil {
					return commandWithOptions{err: err}
				}
				opts, err := newListOptions(cmd)
				return commandWithOptions{err: err, listOptions: opts}
			},
			cloudID: func(result commandWithOptions) int {
				return result.listOptions.BkCloudID
			},
		},
		{
			name: "update",
			newCmd: func(a *app) commandWithOptions {
				cmd := newUpdateCmd(a)
				if err := cmd.Flags().Set(flagBkCloudID, "0"); err != nil {
					return commandWithOptions{err: err}
				}
				opts, err := newUpdateOptions(cmd)
				return commandWithOptions{err: err, updateOptions: opts}
			},
			cloudID: func(result commandWithOptions) int {
				return result.updateOptions.BkCloudID
			},
		},
		{
			name: "delete",
			newCmd: func(a *app) commandWithOptions {
				cmd := newDeleteCmd(a)
				if err := cmd.Flags().Set(flagBkCloudID, "0"); err != nil {
					return commandWithOptions{err: err}
				}
				opts, err := newDeleteOptions(cmd)
				return commandWithOptions{err: err, deleteOptions: opts}
			},
			cloudID: func(result commandWithOptions) int {
				return result.deleteOptions.BkCloudID
			},
		},
	}

	for _, tc := range tests {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			result := tc.newCmd(newApp())
			if result.err != nil {
				t.Fatalf("parse options failed: %s", result.err)
			}

			if got := tc.cloudID(result); got != defaultIntValue {
				t.Fatalf("bk cloud id = %d, want %d", got, defaultIntValue)
			}
		})
	}
}

type commandWithOptions struct {
	err           error
	listOptions   handler.ListOptions
	addOptions    handler.AddOptions
	updateOptions handler.UpdateOptions
	deleteOptions handler.DeleteOptions
}

type flagSetting struct {
	name  string
	value string
}
