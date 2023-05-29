package subcmd

import "encoding/json"

// ToPrettyJson TODO
func ToPrettyJson(v interface{}) string {
	if data, err := json.MarshalIndent(v, "", "    "); err == nil {
		// ss := "\n# use --helper to show explanations. example for payload:\n --payload-format raw --payload '%s'"
		return string(data)
	}
	return "未找到合法的 example "
}
