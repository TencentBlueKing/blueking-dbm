package common

import (
	"bytes"
	"fmt"
	"os"
	"strconv"
	"strings"
)

const (
	slowOpThresholdKey = "slowOpThresholdMs"
	slowOpBlockName    = "operationProfiling"
	slowOpThresholdMin = 10
	slowOpThresholdMax = 20000
)

// ValidateSlowOpThresholdMs checks the dbconfig range [10, 20000].
func ValidateSlowOpThresholdMs(value int) error {
	if value < slowOpThresholdMin || value > slowOpThresholdMax {
		return fmt.Errorf("%s (%d) must be in [%d,%d]", slowOpThresholdKey, value, slowOpThresholdMin, slowOpThresholdMax)
	}
	return nil
}

// DescribeSlowOpThresholdChange reports slowOpThresholdMs old -> new.
// An empty string means the file already has this value.
func DescribeSlowOpThresholdChange(content []byte, value int) (string, error) {
	if err := ValidateSlowOpThresholdMs(value); err != nil {
		return "", err
	}
	current, present, rawText, err := readSlowOpThreshold(content)
	if err != nil {
		return "", err
	}
	if present && current == value && rawText == strconv.Itoa(value) {
		return "", nil
	}
	if present && current == value && rawText == "" {
		return "", nil
	}
	old := "unset"
	if present {
		if rawText != "" && !isNumericText(rawText) {
			old = rawText
		} else {
			old = strconv.Itoa(current)
		}
	}
	if old == strconv.Itoa(value) {
		return "", nil
	}
	return fmt.Sprintf("%s %s -> %d", slowOpThresholdKey, old, value), nil
}

// PatchSlowOpThresholdFile writes operationProfiling.slowOpThresholdMs into mongo.conf.
// When the value changes, the previous file is copied to path.bak.<timestamp> first.
// An empty backup path means the file was left unchanged. noauth.conf is not touched.
func PatchSlowOpThresholdFile(path string, value int) (string, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("read mongo config %s: %w", path, err)
	}
	changes, err := DescribeSlowOpThresholdChange(raw, value)
	if err != nil {
		return "", fmt.Errorf("%s: %w", path, err)
	}
	if changes == "" {
		return "", nil
	}
	out, err := patchSlowOpThresholdContent(raw, value)
	if err != nil {
		return "", fmt.Errorf("%s: %w", path, err)
	}
	if bytes.Equal(raw, out) {
		return "", nil
	}
	perm := os.FileMode(0644)
	if info, statErr := os.Stat(path); statErr == nil {
		perm = info.Mode().Perm()
	}
	backupPath, err := backupMongosConf(path, raw, perm)
	if err != nil {
		return "", err
	}
	if err = os.WriteFile(path, out, perm); err != nil {
		return "", fmt.Errorf("write mongo config %s: %w", path, err)
	}
	return backupPath, nil
}

func patchSlowOpThresholdContent(content []byte, value int) ([]byte, error) {
	if len(bytes.TrimSpace(content)) == 0 {
		return nil, fmt.Errorf("mongo config is empty")
	}
	newline := "\n"
	body := content
	if bytes.Contains(content, []byte("\r\n")) {
		newline = "\r\n"
		body = bytes.ReplaceAll(content, []byte("\r\n"), []byte("\n"))
	}
	lines := strings.Split(string(body), "\n")
	patched, err := patchSlowOpThresholdLines(lines, value)
	if err != nil {
		return nil, err
	}
	out := []byte(strings.Join(patched, "\n"))
	if newline != "\n" {
		out = bytes.ReplaceAll(out, []byte("\n"), []byte(newline))
	}
	return out, nil
}

func patchSlowOpThresholdLines(lines []string, value int) ([]string, error) {
	body := lines
	trailingNewline := false
	if len(body) > 0 && body[len(body)-1] == "" {
		trailingNewline = true
		body = body[:len(body)-1]
	}
	header := -1
	for i, line := range body {
		ok, err := isYAMLBlockHeader(line, slowOpBlockName)
		if err != nil {
			return nil, err
		}
		if ok {
			header = i
			break
		}
	}
	var out []string
	if header < 0 {
		out = appendSlowOpSection(body, value)
	} else {
		blockEnd := header + 1
		for blockEnd < len(body) && !isTopLevelContent(body[blockEnd]) {
			blockEnd++
		}
		kept := editSlowOpBlock(body[header+1:blockEnd], value)
		out = append(out, body[:header+1]...)
		out = append(out, kept...)
		out = append(out, body[blockEnd:]...)
	}
	if trailingNewline {
		out = append(out, "")
	}
	return out, nil
}

func editSlowOpBlock(block []string, value int) []string {
	kept := make([]string, 0, len(block)+1)
	seen := false
	childIndent := "  "
	foundIndent := false
	for _, line := range block {
		if isBlank(line) || isComment(line) {
			kept = append(kept, line)
			continue
		}
		indent, quote, key, colon, comment, ok := parseIndentedKey(line)
		if !ok {
			kept = append(kept, line)
			continue
		}
		if !foundIndent {
			childIndent = indent
			foundIndent = true
		}
		if key != slowOpThresholdKey {
			kept = append(kept, line)
			continue
		}
		seen = true
		kept = append(kept, formatParamLine(indent, quote, key, colon, comment, value))
	}
	if !seen {
		kept = append(kept, formatParamLine(childIndent, "", slowOpThresholdKey, ":", "", value))
	}
	return kept
}

func appendSlowOpSection(lines []string, value int) []string {
	insertAt := len(lines)
	if insertAt > 0 && lines[insertAt-1] == "" {
		insertAt--
	}
	block := []string{
		slowOpBlockName + ":",
		formatParamLine("  ", "", slowOpThresholdKey, ":", "", value),
	}
	out := make([]string, 0, len(lines)+len(block))
	out = append(out, lines[:insertAt]...)
	out = append(out, block...)
	out = append(out, lines[insertAt:]...)
	return out
}

func readSlowOpThreshold(content []byte) (value int, present bool, rawText string, err error) {
	body := content
	if bytes.Contains(content, []byte("\r\n")) {
		body = bytes.ReplaceAll(content, []byte("\r\n"), []byte("\n"))
	}
	lines := strings.Split(string(body), "\n")
	if len(lines) > 0 && lines[len(lines)-1] == "" {
		lines = lines[:len(lines)-1]
	}
	header := -1
	for i, line := range lines {
		ok, headerErr := isYAMLBlockHeader(line, slowOpBlockName)
		if headerErr != nil {
			return 0, false, "", headerErr
		}
		if ok {
			header = i
			break
		}
	}
	if header < 0 {
		return 0, false, "", nil
	}
	for i := header + 1; i < len(lines) && !isTopLevelContent(lines[i]); i++ {
		line := lines[i]
		if isBlank(line) || isComment(line) {
			continue
		}
		_, _, key, _, _, ok := parseIndentedKey(line)
		if !ok || key != slowOpThresholdKey {
			continue
		}
		text := displayIndentedValue(line)
		if text == "unset" {
			return 0, true, "", nil
		}
		n, convErr := strconv.Atoi(text)
		if convErr != nil {
			return 0, true, text, nil
		}
		return n, true, text, nil
	}
	return 0, false, "", nil
}

func isYAMLBlockHeader(line, name string) (bool, error) {
	if isBlank(line) || isComment(line) || lineIndent(line) != 0 {
		return false, nil
	}
	code, _ := splitYAMLComment(line)
	code = strings.TrimSpace(code)
	if !strings.HasPrefix(code, name) {
		return false, nil
	}
	rest := strings.TrimSpace(code[len(name):])
	if rest == "" || !strings.HasPrefix(rest, ":") {
		return false, nil
	}
	val := strings.TrimSpace(rest[1:])
	if val != "" {
		return false, fmt.Errorf("%s must be a block, got %q", name, val)
	}
	return true, nil
}

func isNumericText(text string) bool {
	_, err := strconv.Atoi(text)
	return err == nil
}
