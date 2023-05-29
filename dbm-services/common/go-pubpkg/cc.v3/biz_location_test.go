package cc

import (
	"fmt"
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestBizLocationQuery
func TestBizLocationQuery(t *testing.T) {
	cases := struct {
		param        BizLocationParam
		expectResult []BizLocationInfo
	}{
		param: BizLocationParam{
			BKBizIds: []int{100605, 690},
		},
		expectResult: []BizLocationInfo{
			{
				BkBizID:    10065,
				BkLocation: "v3.0",
			},
			{
				BkBizID:    690,
				BkLocation: "v1.0",
			},
		},
	}

	client, err := NewClient("http://127.0.0.1", TestSecret)
	if err != nil {
		t.Fatal(err)
	}
	h := NewBizLocation(client)
	result, err := h.Query([]int{100605, 690})
	if err != nil {
		t.Fatal(err)
	}
	assert.Equal(t, cases.expectResult, result, fmt.Sprintf("case: %+v", cases.param))
}
