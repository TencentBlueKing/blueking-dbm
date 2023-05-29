package timeutil

import (
	"encoding/json"
	"fmt"
	"time"
)

// Duration TODO
type Duration struct {
	time.Duration
}

// UnmarshalJSON TODO
func (d *Duration) UnmarshalJSON(b []byte) error {
	var unmarshalledJson interface{}

	err := json.Unmarshal(b, &unmarshalledJson)
	if err != nil {
		return err
	}

	switch value := unmarshalledJson.(type) {
	case float64:
		d.Duration = time.Duration(value)
	case string:
		d.Duration, err = time.ParseDuration(value)
		if err != nil {
			return err
		}
	default:
		return fmt.Errorf("invalid duration: %#v", unmarshalledJson)
	}

	return nil
}

// String 用于打印
func (d *Duration) String() string {
	return fmt.Sprintf("%s", d.Duration)
}

// IsZeroDuration TODO
func (d *Duration) IsZeroDuration() bool {
	return d.Duration == 0
}

// Return TODO
func (d *Duration) Return() time.Duration {
	return d.Duration
}

// NewDuration TODO
func NewDuration(t time.Duration) Duration {
	return Duration{t}
}

// CompareDuration 1: t1>t2, -1: t1<t2, 0: t1=t2
func CompareDuration(t1, t2 Duration) int8 {
	if t1.Duration > t2.Duration {
		return 1
	} else if t1.Duration < t2.Duration {
		return -1
	} else {
		return 0
	}
}
