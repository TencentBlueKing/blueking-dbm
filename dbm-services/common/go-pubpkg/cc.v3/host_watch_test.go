package cc

import (
	"testing"
)

// TestHostWatchList
func TestHostWatchList(t *testing.T) {
	client, err := NewClient("http://127.0.0.1", TestSecret)
	if err != nil {
		t.Fatal(err)
	}
	w, _ := HostWatchList(client)
	event := <-w.ResultChan()
	_, ok := event.Object.(*Host)
	if !ok {
		t.Fatalf("Object not Host: %+v", event.Object)
	}
}
