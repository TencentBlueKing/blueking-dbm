package mymongo

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"time"

	"go.mongodb.org/mongo-driver/mongo"
)

// MongoVersion mongo version struct
type MongoVersion struct {
	Version string `json:"version"`
	Major   int    `json:"major"`
	Minor   int    `json:"minor"`
	Patch   int    `json:"patch"`
}

// ParseMongoVersion parse mongo version
func ParseMongoVersion(version string) (*MongoVersion, error) {
	versionArray := strings.Split(version, ".")
	if len(versionArray) != 3 {
		return nil, fmt.Errorf("bad version:%s", version)
	}
	major, err := strconv.ParseInt(versionArray[0], 10, 32)
	if err != nil {
		return nil, fmt.Errorf("bad version:%s", version)
	}
	minor, err := strconv.ParseInt(versionArray[1], 10, 32)
	if err != nil {
		return nil, fmt.Errorf("bad version:%s", version)
	}
	return &MongoVersion{
		Version: version,
		Major:   int(major),
		Minor:   int(minor),
		Patch:   0,
	}, nil
}

// GetMongoServerVersion get mongo server version
func GetMongoServerVersion(client *mongo.Client) (*MongoVersion, error) {
	return ParseMongoVersion(GetMongoServerVersionString(client))
}

// GetMongoServerVersionString get mongo server version string
func GetMongoServerVersionString(client *mongo.Client) string {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	serverVersion, err := client.Database("admin").RunCommand(ctx, map[string]interface{}{"buildinfo": 1}).DecodeBytes()
	if err != nil {
		return ""
	}
	return serverVersion.Lookup("version").StringValue()
}

func getSysDbList() []string {
	return []string{"admin", "config", "local"}
}

// IsSysDb check if db is system db
func IsSysDb(db string) bool {
	for _, v := range getSysDbList() {
		if v == db {
			return true
		}
	}
	return false
}
