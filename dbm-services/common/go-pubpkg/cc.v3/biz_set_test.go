package cc

import (
	"testing"
)

// TestBizCreateSet
func TestBizCreateSet(t *testing.T) {
	client, err := NewClient("http://127.0.0.1", TestSecret)
	if err != nil {
		t.Fatal(err)
	}
	h := NewBizSet(client)
	result, err := h.Create(100781, "cephoooooxx", 5000235)
	if err != nil {
		t.Fatal(err)
	}
	if result.BkSetName != "cephoooooxx" {
		t.Fatalf("Biz module create set %+v", result)
	}
}

// TestBizDeleteSet
func TestBizDeleteSet(t *testing.T) {
	client, err := NewClient("http://127.0.0.1", TestSecret)
	if err != nil {
		t.Fatal(err)
	}
	h := NewBizSet(client)
	err = h.Delete(100781, 5004495)
	if err != nil {
		t.Fatal(err)
	}
}
