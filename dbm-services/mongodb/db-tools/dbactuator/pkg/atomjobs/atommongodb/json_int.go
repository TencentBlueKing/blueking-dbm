package atommongodb

import (
	"bytes"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"

	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
)

// JSONInt accepts a JSON number or a numeric string. A missing field stays unset (-1).
type JSONInt struct {
	Set   bool
	Value int
}

// UnmarshalJSON decodes a number or a numeric string. null and "" stay unset.
func (n *JSONInt) UnmarshalJSON(data []byte) error {
	data = bytes.TrimSpace(data)
	if len(data) == 0 || string(data) == "null" {
		n.Set = false
		n.Value = 0
		return nil
	}
	if data[0] == '"' {
		var text string
		if err := json.Unmarshal(data, &text); err != nil {
			return err
		}
		text = strings.TrimSpace(text)
		if text == "" {
			n.Set = false
			n.Value = 0
			return nil
		}
		value, err := strconv.Atoi(text)
		if err != nil {
			return fmt.Errorf("invalid int %q", text)
		}
		n.Value = value
		n.Set = true
		return nil
	}
	var value int
	if err := json.Unmarshal(data, &value); err != nil {
		return err
	}
	n.Value = value
	n.Set = true
	return nil
}

// OrUnset returns the value, or -1 when the field was absent or empty.
func (n JSONInt) OrUnset() int {
	if !n.Set {
		return common.MongosExecutorPoolUnset
	}
	return n.Value
}
