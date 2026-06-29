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

package config

import (
	"strings"
	"testing"
)

func TestValidateCheckProbeProcessCmd_Default(t *testing.T) {
	if err := validateCheckProbeProcessCmd(defaultCheckProbeProcessCmd); err != nil {
		t.Fatalf("default command should pass, errmsg: %s", err)
	}
}

func TestValidateCheckProbeProcessCmd_ValidCustom(t *testing.T) {
	cases := []string{
		"cd /opt/dbha-v2 && ./bin/dbha-probe health -j",
		"cd ~/dbha-v2 && ./bin/dbha-probe health -j",
	}

	for _, cmd := range cases {
		if err := validateCheckProbeProcessCmd(cmd); err != nil {
			t.Fatalf("valid custom command should pass, cmd: %s, errmsg: %s", cmd, err)
		}
	}
}

func TestValidateCheckProbeProcessCmd_Reject(t *testing.T) {
	cases := []struct {
		name string
		cmd  string
	}{
		{name: "empty", cmd: ""},
		{name: "whitespace", cmd: "   "},
		{name: "wrong_binary", cmd: "cd ~ && ./probe health -j"},
		{name: "wrong_subcommand", cmd: "cd ~ && ./bin/dbha-probe status -j"},
		{name: "extra_chain", cmd: "cd ~ && ./bin/dbha-probe health -j && echo x"},
		{name: "delete", cmd: "cd ~ && /bin/rm -rf /tmp/x"},
		{name: "python", cmd: "cd ~ && python -c \"import os\""},
		{name: "semicolon", cmd: "cd ~; touch /tmp/x"},
		{name: "substitution", cmd: "$(touch /tmp/x)"},
		{name: "dollar_var", cmd: "cd $HOME && ./bin/dbha-probe health -j"},
		{name: "dollar_brace", cmd: "cd ${HOME} && ./bin/dbha-probe health -j"},
		{name: "pipe_bash", cmd: "echo x | bash"},
		{name: "background", cmd: "cd ~ && sleep 1 &"},
		{name: "multiline", cmd: "cd ~\ntouch x"},
		{name: "path_traversal", cmd: "cd /tmp/../etc && ./bin/dbha-probe health -j"},
		{name: "invalid_structure", cmd: "cd /usr/local/dbha-v2"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if err := validateCheckProbeProcessCmd(tc.cmd); err == nil {
				t.Fatal("expected validation error")
			}
		})
	}
}

func TestInit_DefaultCheckProbeProcessCmd(t *testing.T) {
	if Cfg.Detector.CheckProbeProcessCmd != defaultCheckProbeProcessCmd {
		t.Fatalf("unexpected default, got: %s", Cfg.Detector.CheckProbeProcessCmd)
	}
	if strings.TrimSpace(Cfg.Detector.CheckProbeProcessCmd) == "" {
		t.Fatal("default command must not be empty")
	}
}
