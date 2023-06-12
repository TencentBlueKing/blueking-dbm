package cmutil

import "encoding/json"

// CleanStrMap TODO
func CleanStrMap(data map[string]string) map[string]string {
	for key := range data {
		if IsEmpty(key) {
			delete(data, key)
		}
	}
	return data
}

// ConverMapToJsonStr TODO
func ConverMapToJsonStr(m map[string]string) (string, error) {
	b, err := json.Marshal(m)
	if err != nil {
		return "{}", err
	}
	return string(b), nil
}
