package checkhealthjob

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"
)

func TestRemoveExcessMongoLogFiles(t *testing.T) {
	dir := t.TempDir()
	live := filepath.Join(dir, "mongo.log")
	require.NoError(t, os.WriteFile(live, []byte("live"), 0644))

	base := time.Now().Add(-time.Hour)
	var rotated []string
	for i := 0; i < 5; i++ {
		name := filepath.Join(dir, fmt.Sprintf("mongo.log.%d", i))
		require.NoError(t, os.WriteFile(name, []byte("rotated"), 0644))
		mtime := base.Add(time.Duration(i) * time.Minute)
		require.NoError(t, os.Chtimes(name, mtime, mtime))
		rotated = append(rotated, name)
	}

	logger := zap.NewNop()
	pattern := filepath.Join(dir, "mongo.log*")
	require.NoError(t, removeExcessMongoLogFiles(pattern, 3, logger))

	_, err := os.Stat(live)
	assert.NoError(t, err, "live mongo.log must be kept")

	remaining := 0
	for _, f := range rotated {
		if _, err := os.Stat(f); err == nil {
			remaining++
		}
	}
	// total cap 3 including live → 2 rotated remain (delete 3 oldest)
	assert.Equal(t, 2, remaining)
	for i := 0; i < 3; i++ {
		_, err := os.Stat(rotated[i])
		assert.True(t, os.IsNotExist(err), "rotated[%d] should be removed", i)
	}
	for i := 3; i < 5; i++ {
		_, err := os.Stat(rotated[i])
		assert.NoError(t, err, "rotated[%d] should be kept", i)
	}
}
