package cc

import (
	"fmt"
	"log"
	"testing"
)

// TestHostLocation_Query
func TestHostLocation_Query(t *testing.T) {
	address := "http://127.0.0.1"

	client, err := NewClient(address, TestSecret)
	if err != nil {
		log.Fatal(err.Error())
	}

	h := NewHostLocation(client)
	param := []string{""}
	result, err := h.Query(param)
	if err != nil {
		log.Fatal(err.Error())
	}

	fmt.Println(result)
}
