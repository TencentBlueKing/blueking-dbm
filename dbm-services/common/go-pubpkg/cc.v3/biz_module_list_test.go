package cc

import (
	"testing"
)

// TestBizModuleQuery
func TestBizModuleQuery(t *testing.T) {
	client, err := NewClient("http://127.0.0.1", TestSecret)
	if err != nil {
		t.Fatal(err)
	}
	h := NewBizModuleList(client)
	result, err := h.Query(312, 7823, TestPage)
	if err != nil {
		t.Fatal(err)
	}
	if len(result.Info) != 1 {
		t.Fatalf("Biz module query result not eq 1[%d]", len(result.Info))
	}
}
