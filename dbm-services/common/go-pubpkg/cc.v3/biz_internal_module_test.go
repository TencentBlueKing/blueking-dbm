package cc

import (
	"testing"
)

// Test BizInternalModule
func TestBizInternalModule(t *testing.T) {
	client, err := NewClient("http://127.0.0.1", TestSecret)
	if err != nil {
		t.Fatal(err)
	}
	w := NewBizInternalModule(client)
	response, err := w.Query(295)
	if err != nil {
		t.Fatalf("query biz internal modules failed, err: %+v", err)
	}
	t.Logf("query biz internal modules output: %+v", response)
}
