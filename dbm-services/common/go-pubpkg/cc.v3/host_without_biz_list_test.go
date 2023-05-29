package cc

import (
	"fmt"
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestQueryWithFilter
func TestQueryWithFilter(t *testing.T) {
	cases := []struct {
		filter         HostPropertyFilter
		expectedResult int
	}{
		{
			filter: HostPropertyFilter{
				Condition: "AND",
				Rules: []Rule{
					{
						Field:    "bk_host_innerip",
						Operator: "in",
						Value:    []string{"x.x.x.x"},
					},
				},
			},
			expectedResult: 0,
		},
		{
			filter: HostPropertyFilter{
				Condition: "AND",
				Rules: []Rule{
					{
						Field:    "bk_host_innerip",
						Operator: "in",
						Value:    []string{"1.1.1.1"},
					},
				},
			},
			expectedResult: 1,
		},
	}
	client, err := NewClient("http://127.0.0.1", TestSecret)
	if err != nil {
		t.Fatal(err)
	}
	h := NewHostWithoutBizList(client)
	for _, tc := range cases {
		result, err := h.QueryWithFilter(tc.filter, TestPage)
		if err != nil {
			t.Fatal(err)
		}
		assert.Equal(t, tc.expectedResult, len(result.Info), fmt.Sprintf("case: %+v", tc.filter))
	}
}
