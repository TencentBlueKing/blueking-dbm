// Package tools TODO
package tools

import (
	"errors"
	"strconv"
)

// ChangeValueArrayToString TODO
func ChangeValueArrayToString(value []interface{}) ([]string, error) {
	results := []string{}
	for _, item := range value {
		result, err := ChangeValueToString(item)
		if err != nil {
			return results, err
		}
		results = append(results, result)
	}

	return results, nil
}

// ChangeValueToString TODO
func ChangeValueToString(value interface{}) (string, error) {

	var result string
	if item, ok := value.(string); ok {
		result = item
	} else if item1, ok := value.(int); ok {
		result = strconv.Itoa(item1)
	} else if item2, ok := value.(int64); ok {
		result = strconv.FormatInt(item2, 10)
	} else if item3, ok := value.(float64); ok {
		result = strconv.FormatFloat(item3, 'f', -1, 64)
	} else if item4, ok := value.(bool); ok {
		result = strconv.FormatBool(item4)
	} else {
		return result, errors.New("[ChangeValueToString]value type unknow,not in (string,int,int64,float64,bool)")
	}
	return result, nil
}
