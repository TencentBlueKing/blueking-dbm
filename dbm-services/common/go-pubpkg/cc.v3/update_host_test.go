package cc

import (
	"testing"
)

// TestUpdate
func TestUpdate(t *testing.T) {
	client, err := NewClient("http://127.0.0.1", TestSecret)
	if err != nil {
		t.Fatal(err)
	}
	h := NewUpdateHost(client)
	err = h.Update(&UpdateHostParam{
		InnerIPs: []string{"1.1.1.1"},
		Data: Host{
			Operator:    "abc",
			BakOperator: "ddd",
		},
	})
	if err != nil {
		t.Fatal(err)
	}
}
