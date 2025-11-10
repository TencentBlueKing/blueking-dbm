package tools

import (
	"encoding/json"
)

type toolsDefinition struct {
	Name             string          `json:"name"`
	Description      string          `json:"description"`
	InputJsonSchema  json.RawMessage `json:"input_schema"`
	OutputJsonSchema json.RawMessage `json:"output_schema"`
}

func (c *toolsDefinition) String() string {
	b, _ := json.Marshal(c)
	return string(b)
}
