package psutil

import (
	"os"
	"strconv"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestGetPidByPort(t *testing.T) {
	port := os.Getenv("MONGO_PORT")
	portInt, err := strconv.Atoi(port)
	if err != nil {
		t.Fatal(err)
	}
	pid, err := GetPidByPort(portInt, nil)
	t.Logf("pid: %d, err: %v", pid, err)
	assert.NoError(t, err)
	assert.NotEqual(t, 0, pid)
}
