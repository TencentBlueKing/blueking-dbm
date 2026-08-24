/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 */

package main

import "testing"

// Only arguments that fail before any RunE are used here: the root command
// carries RunE: probe.Run, so anything reaching it would start the service.
func TestRun(t *testing.T) {
	tests := []struct {
		name string
		args []string
		want int
	}{
		{name: "version", args: []string{"version"}, want: 0},
		{name: "unknown flag", args: []string{"--no-such-flag"}, want: 1},
		{name: "unknown command", args: []string{"no-such-command"}, want: 1},
		{name: "gen-config without admin endpoints", args: []string{"gen-config"}, want: 1},
		{name: "ping-http-addr without value", args: []string{"--ping-http-addr"}, want: 1},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := run(tt.args); got != tt.want {
				t.Errorf("run(%v), got: %d, want: %d", tt.args, got, tt.want)
			}
		})
	}
}
