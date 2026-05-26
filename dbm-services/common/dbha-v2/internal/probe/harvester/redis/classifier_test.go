package redis

import (
	"errors"
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

func TestClassifyConnectionErrorAuthFailure(t *testing.T) {
	event, reason := ClassifyConnectionError(errors.New("WRONGPASS invalid username-password pair"))
	if event != haprobe.DbEventNameDetectRedisAuthFailureV1 {
		t.Fatalf("unexpected event: %s", event)
	}
	if reason != haprobe.DbEventNameReasonAuthException {
		t.Fatalf("unexpected reason: %d", reason)
	}
}

func TestClassifyConnectionErrorConnectionFailure(t *testing.T) {
	event, reason := ClassifyConnectionError(errors.New("dial tcp timeout"))
	if event != haprobe.DbEventNameDetectFailure {
		t.Fatalf("unexpected event: %s", event)
	}
	if reason != haprobe.DbEventNameReasonConnectionException {
		t.Fatalf("unexpected reason: %d", reason)
	}
}
