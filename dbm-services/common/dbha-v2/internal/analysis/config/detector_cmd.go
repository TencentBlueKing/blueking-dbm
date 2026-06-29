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
	"fmt"
	"strings"
	"unicode"
)

const defaultCheckProbeProcessCmd = "cd /usr/local/dbha-v2 && ./bin/dbha-probe health -j"

var allowedProbeHealthTokens = []string{"./bin/dbha-probe", "health", "-j"}

func validateCheckProbeProcessCmd(cmd string) error {
	trimmed := strings.TrimSpace(cmd)
	if trimmed == "" {
		return fmt.Errorf("invalid detector checkProbeProcessCmd: empty command")
	}

	if err := rejectUnsafeShellPatterns(trimmed); err != nil {
		return err
	}

	workdir, probeCmd, err := parseProbeProcessCmdParts(trimmed)
	if err != nil {
		return err
	}

	if err := validateProbeWorkdir(workdir); err != nil {
		return err
	}

	return validateProbeHealthSubcmd(probeCmd)
}

func rejectUnsafeShellPatterns(trimmed string) error {
	if strings.ContainsAny(trimmed, "\n\r") {
		return fmt.Errorf("invalid detector checkProbeProcessCmd: multiline command")
	}

	if strings.Contains(trimmed, "$") {
		return fmt.Errorf("invalid detector checkProbeProcessCmd: shell variable expansion")
	}

	lower := strings.ToLower(trimmed)
	if strings.Contains(lower, "$(") || strings.Contains(trimmed, "`") {
		return fmt.Errorf("invalid detector checkProbeProcessCmd: command substitution")
	}

	if strings.Contains(trimmed, ";") {
		return fmt.Errorf("invalid detector checkProbeProcessCmd: semicolon chain")
	}

	if strings.Contains(trimmed, "|") {
		return fmt.Errorf("invalid detector checkProbeProcessCmd: pipe chain")
	}

	withoutAnd := strings.ReplaceAll(lower, "&&", "")
	if strings.Contains(withoutAnd, "&") {
		return fmt.Errorf("invalid detector checkProbeProcessCmd: background execution")
	}

	return nil
}

func parseProbeProcessCmdParts(cmd string) (workdir string, probeCmd string, err error) {
	parts := strings.Split(cmd, "&&")
	if len(parts) != 2 {
		return "", "", fmt.Errorf("invalid detector checkProbeProcessCmd: command structure")
	}

	cdPart := strings.TrimSpace(parts[0])
	probePart := strings.TrimSpace(parts[1])
	if !strings.HasPrefix(cdPart, "cd ") {
		return "", "", fmt.Errorf("invalid detector checkProbeProcessCmd: command structure")
	}

	workdir = strings.TrimSpace(strings.TrimPrefix(cdPart, "cd "))
	if workdir == "" {
		return "", "", fmt.Errorf("invalid detector checkProbeProcessCmd: empty workdir")
	}

	return workdir, probePart, nil
}

func validateProbeWorkdir(workdir string) error {
	if strings.Contains(workdir, "..") {
		return fmt.Errorf("invalid detector checkProbeProcessCmd: path traversal")
	}

	if !strings.HasPrefix(workdir, "~") && !strings.HasPrefix(workdir, "/") && !strings.HasPrefix(workdir, ".") {
		return fmt.Errorf("invalid detector checkProbeProcessCmd: invalid workdir")
	}

	for _, r := range workdir {
		if unicode.IsLetter(r) || unicode.IsDigit(r) || strings.ContainsRune("_./~-", r) {
			continue
		}
		return fmt.Errorf("invalid detector checkProbeProcessCmd: invalid workdir character")
	}

	return nil
}

func validateProbeHealthSubcmd(probeCmd string) error {
	tokens := strings.Fields(probeCmd)
	if len(tokens) != len(allowedProbeHealthTokens) {
		return fmt.Errorf("invalid detector checkProbeProcessCmd: probe subcommand")
	}

	for i, want := range allowedProbeHealthTokens {
		if tokens[i] != want {
			return fmt.Errorf("invalid detector checkProbeProcessCmd: probe subcommand")
		}
	}

	return nil
}
