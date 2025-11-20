package logical

import (
	"os"
	"strings"
	"testing"
)

// TestGetDbCollection 测试获取db和collection.
func TestGetDbCollection(t *testing.T) {
	MONGO_HOST := os.Getenv("MONGO_SERVER_2_HOST")
	MONGO_PORT := os.Getenv("MONGO_SERVER_2_PORT")
	MONGO_USER := os.Getenv("MONGO_SERVER_2_USER")
	MONGO_PASS := os.Getenv("MONGO_SERVER_2_PASS")
	MONGO_AUTHDB := os.Getenv("MONGO_SERVER_2_AUTHDB")

	if MONGO_HOST == "" || MONGO_PORT == "" || MONGO_USER == "" || MONGO_PASS == "" || MONGO_AUTHDB == "" {
		t.Fatal("MONGO_SERVER_2_HOST, MONGO_SERVER_2_PORT, MONGO_SERVER_2_USER, MONGO_SERVER_2_PASS, " +
			"MONGO_SERVER_2_AUTHDB is not set")
	}

	t.Logf("MONGO_SERVER_2_HOST: %s, MONGO_SERVER_2_PORT: %s, MONGO_SERVER_2_USER: %s, "+
		"MONGO_SERVER_2_PASS: %s, MONGO_SERVER_2_AUTHDB: %s",
		MONGO_HOST, MONGO_PORT, MONGO_USER, MONGO_PASS, MONGO_AUTHDB)

	dbColList, err := GetDbCollection(MONGO_HOST, MONGO_PORT, MONGO_USER, MONGO_PASS, MONGO_AUTHDB, false)
	if err != nil {
		t.Fatal(err)
	} else {
		for _, dbCol := range dbColList {
			t.Logf("\n\tdb: %s, col: %s", dbCol.Db, strings.Join(dbCol.Col, ", "))
		}
	}

	// check if admin in dbColList and col is not empty
	for _, dbCol := range dbColList {
		if dbCol.Db == "admin" && len(dbCol.Col) > 0 {
			t.Logf("admin in dbColList and col is not empty")
		}
	}

}
