package dtstaskstatus

import (
	"testing"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

func TestMasterTasksURL(t *testing.T) {
	url, err := masterTasksURL("127.0.0.2", 18301)
	if err != nil {
		t.Fatal(err)
	}
	if url != "http://127.0.0.2:18301/api/v1/tasks?with_status=true" {
		t.Fatalf("got %s", url)
	}
}

func TestMasterTasksURL_Empty(t *testing.T) {
	if _, err := masterTasksURL("", 18301); err == nil {
		t.Fatal("empty ip should error")
	}
}

func TestCheckerRun_OpenAPIError(t *testing.T) {
	config.MonitorConfig = &config.Config{Ip: "127.0.0.2", Port: 18301}
	c := &Checker{httpGet: func(url string) ([]byte, error) {
		return nil, errOpenAPI
	}}
	_, _, err := c.Run()
	if err == nil {
		t.Fatal("openapi failure should return err")
	}
}

var errOpenAPI = errString("openapi down")

type errString string

func (e errString) Error() string { return string(e) }
