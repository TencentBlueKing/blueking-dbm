package components

import (
	"encoding/json"
	"fmt"
)

// WrapperOutputString TODO
func WrapperOutputString(output string) string {
	return fmt.Sprintf(`<ctx>%s</ctx>`, output)
}

// WrapperOutput TODO
func WrapperOutput(v interface{}) (string, error) {
	if b, e := json.Marshal(v); e != nil {
		return "<ctx></ctx>", e
	} else {
		return fmt.Sprintf(`<ctx>%s</ctx>`, string(b)), nil
	}
}

// PrintOutputCtx TODO
func PrintOutputCtx(v interface{}) error {
	if ss, err := WrapperOutput(v); err != nil {
		return err
	} else {
		fmt.Println(ss)
	}
	return nil
}

// ToPrettyJson TODO
func ToPrettyJson(v interface{}) string {
	if data, err := json.MarshalIndent(v, "", "    "); err == nil {
		// ss := "\n# use --helper to show explanations. example for payload:\n --payload-format raw --payload '%s'"
		return string(data)
	}
	return "未找到合法的 example "
}
