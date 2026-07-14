package atommongodb

import (
	"fmt"
	"strconv"
	"strings"
)

type mongoVersionTuple struct {
	major    int
	minor    int
	patch    int
	hasPatch bool
}

func stripMongoDBPrefix(version string) string {
	return strings.TrimPrefix(strings.TrimPrefix(version, "mongodb-"), "MongoDB-")
}

func parseMongoVersionTuple(version string) (mongoVersionTuple, error) {
	raw := stripMongoDBPrefix(strings.TrimSpace(version))
	if raw == "" {
		return mongoVersionTuple{}, fmt.Errorf("empty version")
	}
	numeric := strings.SplitN(raw, "-", 2)[0]
	parts := strings.Split(numeric, ".")
	if len(parts) < 2 {
		return mongoVersionTuple{}, fmt.Errorf("invalid version: %s", version)
	}
	major, err := strconv.Atoi(parts[0])
	if err != nil {
		return mongoVersionTuple{}, fmt.Errorf("invalid major in version %s: %w", version, err)
	}
	minor, err := strconv.Atoi(parts[1])
	if err != nil {
		return mongoVersionTuple{}, fmt.Errorf("invalid minor in version %s: %w", version, err)
	}
	if len(parts) < 3 {
		return mongoVersionTuple{major: major, minor: minor, hasPatch: false}, nil
	}
	patch, err := strconv.Atoi(parts[2])
	if err != nil {
		return mongoVersionTuple{}, fmt.Errorf("invalid patch in version %s: %w", version, err)
	}
	return mongoVersionTuple{major: major, minor: minor, patch: patch, hasPatch: true}, nil
}

func compareMongoVersionTuples(left, right mongoVersionTuple) int {
	leftKey := []int{left.major, left.minor}
	rightKey := []int{right.major, right.minor}
	for i := 0; i < 2; i++ {
		if leftKey[i] < rightKey[i] {
			return -1
		}
		if leftKey[i] > rightKey[i] {
			return 1
		}
	}
	leftPatch := 0
	if left.hasPatch {
		leftPatch = left.patch
	}
	rightPatch := 0
	if right.hasPatch {
		rightPatch = right.patch
	}
	if leftPatch < rightPatch {
		return -1
	}
	if leftPatch > rightPatch {
		return 1
	}
	return 0
}
