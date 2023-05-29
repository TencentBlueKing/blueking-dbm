package cc

import (
	"fmt"
	"log"
	"testing"
)

// TestHostLocation_Query
func TestSyncHostInfoFromCmpy_Query(t *testing.T) {
	address := "http://127.0.0.1"

	client, err := NewClient(address, TestSecret)
	if err != nil {
		log.Fatal(err.Error())
	}

	h := NewSyncHostInfoFromCmpy(client)
	param := []int{1147527}
	result, err := h.Query(param)
	fmt.Printf("result: %#v\n", result)
	if err != nil {
		fmt.Printf("err: %s\n", err)
		log.Fatal(err.Error())
	}
}
