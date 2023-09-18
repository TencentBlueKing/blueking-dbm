package utils

import (
	"fmt"
	"reflect"
	"testing"

	"github.com/stretchr/testify/assert"
)

type testObject struct {
	c1 string            `json:"c1,omitempty"`
	c2 int               `json:"c2"`
	c3 *c3               `json:"c3,omitempty"`
	c4 map[string]string `json:"c4"`
	c5 []int             `json:"c5"`
}

type c3 struct {
	x1 string   `json:"x1"`
	x2 []x2     `json:"x2,omitempty"`
	x3 []string `json:"x3"`
}

type x2 struct {
	y1 string         `json:"y1"`
	y2 map[string]int `json:"y2,omitempty"`
	y3 *int           `json:"y3"`
}

func TestGetStructTagName(t *testing.T) {
	cases := []struct {
		name           string
		object         interface{}
		expectedResult []string
	}{
		{
			name:           "ptr",
			object:         &testObject{},
			expectedResult: []string{"c1", "c2", "x1", "y1", "y2", "y3", "x2", "x3", "c3", "c4", "c5"},
		},
		{
			name:           "struct",
			object:         testObject{},
			expectedResult: []string{"c1", "c2", "x1", "y1", "y2", "y3", "x2", "x3", "c3", "c4", "c5"},
		},
	}
	for _, tc := range cases {
		fields := GetStructTagName(reflect.TypeOf(tc.object))
		assert.Equal(t, tc.expectedResult, fields, fmt.Sprintf("case: %+v", tc.name))
	}
}
