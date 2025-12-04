package tools

import (
	"encoding/json"
)

type toolsDefinition struct {
	Path             string          `json:"path"`
	OperationId      string          `json:"operation_id"`
	Description      string          `json:"description"`
	InputJsonSchema  json.RawMessage `json:"request_schema"`
	OutputJsonSchema json.RawMessage `json:"response_schema"`
}

func (c *toolsDefinition) String() string {
	b, _ := json.Marshal(c)
	return string(b)
}
