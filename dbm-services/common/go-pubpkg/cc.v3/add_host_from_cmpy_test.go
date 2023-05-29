package cc

import (
	"fmt"
	"log"
	"testing"
)

// TestHostLocation_Query
func TestAddHostInfoFromCmpy_Query(t *testing.T) {
	address := "http://127.0.0.1"

	client, err := NewClient(address, TestSecret)
	if err != nil {
		log.Fatal(err.Error())
	}

	h := NewAddHostInfoFromCmpy(client)
	param := []int{489462239}
	result, err := h.Query(param)
	if err != nil {
		log.Fatal(err.Error())
	}

	fmt.Printf("result: %#v", result)
}
