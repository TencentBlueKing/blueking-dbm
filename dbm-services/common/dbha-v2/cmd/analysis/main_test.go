/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 */

package main

import "testing"

// Only arguments that fail before any RunE are used here: the root command
// carries RunE: analysis.Run, so anything reaching it would start the service.
func TestRun(t *testing.T) {
	tests := []struct {
		name string
		args []string
		want int
	}{
		{name: "version", args: []string{"version"}, want: 0},
		{name: "unknown flag", args: []string{"--no-such-flag"}, want: 1},
		{name: "unknown command", args: []string{"no-such-command"}, want: 1},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := run(tt.args); got != tt.want {
				t.Errorf("run(%v), got: %d, want: %d", tt.args, got, tt.want)
			}
		})
	}
}
