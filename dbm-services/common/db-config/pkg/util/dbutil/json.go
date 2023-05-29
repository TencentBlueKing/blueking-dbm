package util

import (
	"bytes"
	"database/sql/driver"
	"errors"
	"fmt"
)

// JSON TODO
type JSON []byte

// Value TODO
func (j JSON) Value() (driver.Value, error) {
	fmt.Println("Value()")
	if j.IsNull() {
		return nil, nil
	}
	return string(j), nil
}

// Scan TODO
func (j *JSON) Scan(value interface{}) error {
	fmt.Println("Scan()")
	if value == nil {
		*j = nil
		return nil
	}
	s, ok := value.([]byte)
	if !ok {
		return errors.New("Invalid Scan Source")
	}
	*j = append((*j)[0:0], s...)
	return nil
}

// MarshalJSON TODO
func (m JSON) MarshalJSON() ([]byte, error) {
	fmt.Println("MarshalJSON()")
	if m == nil {
		return []byte("null"), nil
	}
	return m, nil
}

// UnmarshalJSON TODO
func (m *JSON) UnmarshalJSON(data []byte) error {
	fmt.Println("MarshalJSON()")
	if m == nil {
		return errors.New("null point exception")
	}
	*m = append((*m)[0:0], data...)
	return nil
}

// IsNull TODO
func (j JSON) IsNull() bool {
	return len(j) == 0 || string(j) == "null"
}

// Equals TODO
func (j JSON) Equals(j1 JSON) bool {
	return bytes.Equal([]byte(j), []byte(j1))
}
