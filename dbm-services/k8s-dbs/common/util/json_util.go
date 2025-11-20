package util

import (
	"encoding/json"
	"fmt"
	"log/slog"
)

// JSONStrToMap convert json string to map
func JSONStrToMap(value string) (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := json.Unmarshal([]byte(value), &result); err != nil {
		slog.Error("Failed to unmarshal chart values",
			"error", err,
			"value", value,
		)
		return nil, fmt.Errorf("unmarshal failed: %w", err)
	}
	return result, nil
}

// MapToJSONStr convert map to json string
func MapToJSONStr(value map[string]interface{}) (string, error) {
	jsonData, err := json.Marshal(value)
	if err != nil {
		slog.Error("Failed to marshal chart values", "value", value, "error", err)
		return "", fmt.Errorf("failed to marshal release values: %w", err)
	}
	return string(jsonData), nil
}
