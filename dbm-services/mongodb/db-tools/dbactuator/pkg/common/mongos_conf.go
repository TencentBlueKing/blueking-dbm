package common

import (
	"bytes"
	"fmt"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"

	"gopkg.in/yaml.v2"
)

// indentedKeyRE matches one indented "key: value" line. Quotes around the key are kept.
var indentedKeyRE = regexp.MustCompile(`^([ \t]+)("?)([A-Za-z_][A-Za-z0-9_]*)("?)([ \t]*:)(.*)$`)

// MongosExecutorPoolUnset means the parameter is not written into mongos.conf.
const MongosExecutorPoolUnset = -1

const (
	// ParamTaskExecutorPoolSize is mongos setParameter.taskExecutorPoolSize.
	ParamTaskExecutorPoolSize = "taskExecutorPoolSize"
	// ParamShardingTaskExecutorPoolMinSize is mongos setParameter.ShardingTaskExecutorPoolMinSize.
	ParamShardingTaskExecutorPoolMinSize = "ShardingTaskExecutorPoolMinSize"
	// ParamShardingTaskExecutorPoolMaxSize is mongos setParameter.ShardingTaskExecutorPoolMaxSize.
	ParamShardingTaskExecutorPoolMaxSize = "ShardingTaskExecutorPoolMaxSize"
)

var mongosExecutorPoolKeyOrder = []string{
	ParamTaskExecutorPoolSize,
	ParamShardingTaskExecutorPoolMinSize,
	ParamShardingTaskExecutorPoolMaxSize,
}

const mongosExecutorPoolMax = 1024

// YamlMongoSConf 4.0及以上配置文件
type YamlMongoSConf struct {
	Sharding struct {
		ConfigDB string `yaml:"configDB"`
	} `yaml:"sharding"`
	SystemLog struct {
		LogAppend   bool   `yaml:"logAppend"`
		Path        string `yaml:"path"`
		Destination string `yaml:"destination"`
	} `yaml:"systemLog"`
	ProcessManagement struct {
		Fork        bool   `yaml:"fork"`
		PidFilePath string `yaml:"pidFilePath"`
	} `yaml:"processManagement"`
	Net struct {
		Port            int    `yaml:"port"`
		BindIp          string `yaml:"bindIp"`
		WireObjectCheck bool   `yaml:"wireObjectCheck"`
	} `yaml:"net"`
	OperationProfiling struct {
		SlowOpThresholdMs int `yaml:"slowOpThresholdMs,omitempty"`
	} `yaml:"operationProfiling,omitempty"`
	Security struct {
		KeyFile string `yaml:"keyFile,omitempty"`
	} `yaml:"security,omitempty"`
	// SetParameter holds mongos runtime parameters. Nil or empty is omitted.
	SetParameter map[string]int `yaml:"setParameter,omitempty"`
}

// NewYamlMongoSConf 生成结构体
func NewYamlMongoSConf() *YamlMongoSConf {
	return &YamlMongoSConf{}
}

// GetConfContent 获取配置文件内容
func (y *YamlMongoSConf) GetConfContent() ([]byte, error) {
	out, err := yaml.Marshal(y)
	if err != nil {
		return nil, err
	}
	return out, nil
}

// BuildMongosExecutorPool returns setParameter entries. -1 (or unset) is omitted.
func BuildMongosExecutorPool(taskExecutorPoolSize, minSize, maxSize int) map[string]int {
	pool := map[string]int{}
	if taskExecutorPoolSize != MongosExecutorPoolUnset {
		pool[ParamTaskExecutorPoolSize] = taskExecutorPoolSize
	}
	if minSize != MongosExecutorPoolUnset {
		pool[ParamShardingTaskExecutorPoolMinSize] = minSize
	}
	if maxSize != MongosExecutorPoolUnset {
		pool[ParamShardingTaskExecutorPoolMaxSize] = maxSize
	}
	if len(pool) == 0 {
		return nil
	}
	return pool
}

// ValidateMongosExecutorPool validates the three mongos executor-pool parameters
// before a config file is written. -1 means unset.
func ValidateMongosExecutorPool(taskExecutorPoolSize, minSize, maxSize int) error {
	values := map[string]int{
		ParamTaskExecutorPoolSize:            taskExecutorPoolSize,
		ParamShardingTaskExecutorPoolMinSize: minSize,
		ParamShardingTaskExecutorPoolMaxSize: maxSize,
	}
	for _, name := range mongosExecutorPoolKeyOrder {
		value := values[name]
		if value < MongosExecutorPoolUnset || value > mongosExecutorPoolMax {
			return fmt.Errorf("%s must be in [%d,%d], got %d", name, MongosExecutorPoolUnset, mongosExecutorPoolMax, value)
		}
	}
	if minSize != MongosExecutorPoolUnset && maxSize != MongosExecutorPoolUnset && minSize > maxSize {
		return fmt.Errorf(
			"%s (%d) must not exceed %s (%d)",
			ParamShardingTaskExecutorPoolMinSize,
			minSize,
			ParamShardingTaskExecutorPoolMaxSize,
			maxSize,
		)
	}
	return nil
}

// PatchMongosExecutorPoolContent edits only the three executor-pool keys inside setParameter.
// -1 removes that key. Comments, quotes, and every other line stay as they were.
func PatchMongosExecutorPoolContent(content []byte, taskExecutorPoolSize, minSize, maxSize int) ([]byte, error) {
	if len(bytes.TrimSpace(content)) == 0 {
		return nil, fmt.Errorf("mongos config is empty")
	}
	if err := ValidateMongosExecutorPool(taskExecutorPoolSize, minSize, maxSize); err != nil {
		return nil, err
	}
	values := map[string]int{
		ParamTaskExecutorPoolSize:            taskExecutorPoolSize,
		ParamShardingTaskExecutorPoolMinSize: minSize,
		ParamShardingTaskExecutorPoolMaxSize: maxSize,
	}
	newline := "\n"
	body := content
	if bytes.Contains(content, []byte("\r\n")) {
		newline = "\r\n"
		body = bytes.ReplaceAll(content, []byte("\r\n"), []byte("\n"))
	}
	lines := strings.Split(string(body), "\n")
	patched, err := patchSetParameterLines(lines, values)
	if err != nil {
		return nil, err
	}
	out := []byte(strings.Join(patched, "\n"))
	if newline != "\n" {
		out = bytes.ReplaceAll(out, []byte("\n"), []byte(newline))
	}
	return out, nil
}

// PatchMongosExecutorPoolFile updates one mongos yaml file in place.
// When the content changes, the previous file is copied to path.bak.<timestamp> first.
// An empty backup path means the file was left unchanged.
func PatchMongosExecutorPoolFile(path string, taskExecutorPoolSize, minSize, maxSize int) (string, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("read mongos config %s: %w", path, err)
	}
	out, err := PatchMongosExecutorPoolContent(raw, taskExecutorPoolSize, minSize, maxSize)
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
		return "", fmt.Errorf("write mongos config %s: %w", path, err)
	}
	return backupPath, nil
}

// backupMongosConf writes the previous config next to the original file.
func backupMongosConf(path string, content []byte, perm os.FileMode) (string, error) {
	stamp := time.Now().Format("20060102150405")
	backupPath := fmt.Sprintf("%s.bak.%s", path, stamp)
	for n := 0; ; n++ {
		if n > 0 {
			backupPath = fmt.Sprintf("%s.bak.%s.%d", path, stamp, n)
		}
		_, statErr := os.Stat(backupPath)
		if os.IsNotExist(statErr) {
			break
		}
		if statErr != nil {
			return "", fmt.Errorf("stat mongos config backup %s: %w", backupPath, statErr)
		}
		if n == 100 {
			return "", fmt.Errorf("mongos config backup %s already exists", backupPath)
		}
	}
	if err := os.WriteFile(backupPath, content, perm); err != nil {
		return "", fmt.Errorf("backup mongos config %s: %w", backupPath, err)
	}
	return backupPath, nil
}

// DescribeMongosExecutorPoolChanges lists executor-pool keys whose value would change.
// Missing keys are "unset". An empty string means every managed value already matches.
func DescribeMongosExecutorPoolChanges(content []byte, taskExecutorPoolSize, minSize, maxSize int) (string, error) {
	current, err := readMongosExecutorPool(content)
	if err != nil {
		return "", err
	}
	next := map[string]int{
		ParamTaskExecutorPoolSize:            taskExecutorPoolSize,
		ParamShardingTaskExecutorPoolMinSize: minSize,
		ParamShardingTaskExecutorPoolMaxSize: maxSize,
	}
	var parts []string
	for _, key := range mongosExecutorPoolKeyOrder {
		newText := poolValueText(next[key])
		if current[key] == newText {
			continue
		}
		parts = append(parts, fmt.Sprintf("%s %s -> %s", key, current[key], newText))
	}
	return strings.Join(parts, ", "), nil
}

func readMongosExecutorPool(content []byte) (map[string]string, error) {
	found := map[string]string{}
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
		ok, err := isSetParameterHeader(line)
		if err != nil {
			return nil, err
		}
		if ok {
			header = i
			break
		}
	}
	if header >= 0 {
		for i := header + 1; i < len(lines) && !isTopLevelContent(lines[i]); i++ {
			line := lines[i]
			if isBlank(line) || isComment(line) {
				continue
			}
			_, _, key, _, _, ok := parseIndentedKey(line)
			if !ok || !isMongosExecutorPoolKey(key) {
				continue
			}
			found[key] = displayIndentedValue(line)
		}
	}
	out := make(map[string]string, len(mongosExecutorPoolKeyOrder))
	for _, key := range mongosExecutorPoolKeyOrder {
		if v, ok := found[key]; ok {
			out[key] = v
			continue
		}
		out[key] = "unset"
	}
	return out, nil
}

func isMongosExecutorPoolKey(key string) bool {
	for _, name := range mongosExecutorPoolKeyOrder {
		if name == key {
			return true
		}
	}
	return false
}

func displayIndentedValue(line string) string {
	m := indentedKeyRE.FindStringSubmatch(line)
	if m == nil {
		return "unset"
	}
	code, _ := splitYAMLComment(m[6])
	code = strings.TrimSpace(code)
	if len(code) >= 2 {
		if (code[0] == '"' && code[len(code)-1] == '"') || (code[0] == '\'' && code[len(code)-1] == '\'') {
			code = code[1 : len(code)-1]
		}
	}
	if code == "" {
		return "unset"
	}
	n, err := strconv.Atoi(code)
	if err != nil {
		return code
	}
	return poolValueText(n)
}

func poolValueText(v int) string {
	if v == MongosExecutorPoolUnset {
		return "unset"
	}
	return strconv.Itoa(v)
}

func patchSetParameterLines(lines []string, values map[string]int) ([]string, error) {
	// strings.Split keeps a trailing "" for a final newline. That marker is not a config line.
	body := lines
	trailingNewline := false
	if len(body) > 0 && body[len(body)-1] == "" {
		trailingNewline = true
		body = body[:len(body)-1]
	}
	header := -1
	for i, line := range body {
		ok, err := isSetParameterHeader(line)
		if err != nil {
			return nil, err
		}
		if ok {
			header = i
			break
		}
	}
	if header < 0 {
		out := appendExecutorPoolSection(body, values)
		if trailingNewline {
			out = append(out, "")
		}
		return out, nil
	}

	blockEnd := header + 1
	for blockEnd < len(body) && !isTopLevelContent(body[blockEnd]) {
		blockEnd++
	}
	kept := editExecutorPoolBlock(body[header+1:blockEnd], values)
	var out []string
	out = append(out, body[:header]...)
	if blockHasContent(kept) {
		out = append(out, body[header])
		out = append(out, kept...)
	}
	out = append(out, body[blockEnd:]...)
	if trailingNewline {
		out = append(out, "")
	}
	return out, nil
}

func editExecutorPoolBlock(block []string, values map[string]int) []string {
	kept := make([]string, 0, len(block)+len(mongosExecutorPoolKeyOrder))
	seen := map[string]bool{}
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
		val, managed := values[key]
		if !managed {
			kept = append(kept, line)
			continue
		}
		seen[key] = true
		if val == MongosExecutorPoolUnset {
			continue
		}
		kept = append(kept, formatParamLine(indent, quote, key, colon, comment, val))
	}
	for _, key := range mongosExecutorPoolKeyOrder {
		if seen[key] || values[key] == MongosExecutorPoolUnset {
			continue
		}
		kept = append(kept, formatParamLine(childIndent, "", key, ":", "", values[key]))
	}
	return kept
}

func appendExecutorPoolSection(lines []string, values map[string]int) []string {
	var keys []string
	for _, key := range mongosExecutorPoolKeyOrder {
		if values[key] == MongosExecutorPoolUnset {
			continue
		}
		keys = append(keys, formatParamLine("  ", "", key, ":", "", values[key]))
	}
	if len(keys) == 0 {
		return lines
	}
	insertAt := len(lines)
	if insertAt > 0 && lines[insertAt-1] == "" {
		insertAt--
	}
	block := append([]string{"setParameter:"}, keys...)
	out := make([]string, 0, len(lines)+len(block))
	out = append(out, lines[:insertAt]...)
	out = append(out, block...)
	out = append(out, lines[insertAt:]...)
	return out
}

func isSetParameterHeader(line string) (bool, error) {
	if isBlank(line) || isComment(line) || lineIndent(line) != 0 {
		return false, nil
	}
	code, _ := splitYAMLComment(line)
	code = strings.TrimSpace(code)
	if !strings.HasPrefix(code, "setParameter") {
		return false, nil
	}
	rest := strings.TrimSpace(code[len("setParameter"):])
	if rest == "" || !strings.HasPrefix(rest, ":") {
		return false, nil
	}
	val := strings.TrimSpace(rest[1:])
	if val != "" {
		return false, fmt.Errorf("setParameter must be a block, got %q", val)
	}
	return true, nil
}

func isTopLevelContent(line string) bool {
	return !isBlank(line) && !isComment(line) && lineIndent(line) == 0
}

func isBlank(line string) bool {
	return strings.TrimSpace(line) == ""
}

func isComment(line string) bool {
	return strings.HasPrefix(strings.TrimSpace(line), "#")
}

func lineIndent(line string) int {
	n := 0
	for _, r := range line {
		if r == ' ' || r == '\t' {
			n++
			continue
		}
		break
	}
	return n
}

func parseIndentedKey(line string) (indent, quote, key, colon, comment string, ok bool) {
	m := indentedKeyRE.FindStringSubmatch(line)
	if m == nil || m[2] != m[4] {
		return "", "", "", "", "", false
	}
	valuePart := m[6]
	_, comment = splitYAMLComment(valuePart)
	return m[1], m[2], m[3], m[5], comment, true
}

func splitYAMLComment(s string) (code, comment string) {
	inQuote := byte(0)
	for i := 0; i < len(s); i++ {
		c := s[i]
		if inQuote != 0 {
			if c == inQuote {
				inQuote = 0
			}
			continue
		}
		if c == '"' || c == '\'' {
			inQuote = c
			continue
		}
		if c == '#' {
			return s[:i], s[i:]
		}
	}
	return s, ""
}

func formatParamLine(indent, quote, key, colon, comment string, val int) string {
	line := indent + quote + key + quote + colon
	if !strings.HasSuffix(colon, " ") && !strings.HasSuffix(colon, "\t") {
		line += " "
	}
	line += strconv.Itoa(val)
	if comment != "" {
		if !strings.HasPrefix(comment, " ") && !strings.HasPrefix(comment, "\t") {
			line += " "
		}
		line += comment
	}
	return line
}

func blockHasContent(lines []string) bool {
	for _, line := range lines {
		if !isBlank(line) {
			return true
		}
	}
	return false
}

// LoadMongoSConfFromFile 从文件中加载配置
func LoadMongoSConfFromFile(filePath string) (*YamlMongoSConf, error) {
	content, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}
	var y YamlMongoSConf
	err = yaml.Unmarshal(content, &y)
	if err != nil {
		return nil, err
	}
	return &y, nil
}
