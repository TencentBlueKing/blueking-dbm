package mymongo

import (
	"testing"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/event"
	"go.mongodb.org/mongo-driver/mongo/integration/mtest"
)

func runMockMongo(t *testing.T, name string, fn func(*mtest.T)) {
	t.Helper()

	mt := mtest.New(t, mtest.NewOptions().ClientType(mtest.Mock))
	t.Cleanup(mt.Close)
	mt.Run(name, fn)
}

func lastStartedEvent(t *testing.T, mt *mtest.T) *event.CommandStartedEvent {
	t.Helper()

	events := mt.GetAllStartedEvents()
	if len(events) == 0 {
		t.Fatal("expected command started event")
	}
	return events[len(events)-1]
}

func TestRunAdminCommand(t *testing.T) {
	runMockMongo(t, "success", func(mt *mtest.T) {
		mt.AddMockResponses(mtest.CreateSuccessResponse(bson.E{Key: "value", Value: "ok"}))

		var out struct {
			Value string `bson:"value"`
		}
		if err := RunAdminCommand(mt.Client, bson.M{"ping": 1}, 5, &out); err != nil {
			t.Fatalf("RunAdminCommand failed: %v", err)
		}
		if out.Value != "ok" {
			t.Fatalf("decoded value = %q, want %q", out.Value, "ok")
		}

		evt := lastStartedEvent(t, mt)
		if evt.DatabaseName != AdminDB {
			t.Fatalf("database = %q, want %q", evt.DatabaseName, AdminDB)
		}
		if evt.CommandName != "ping" {
			t.Fatalf("command = %q, want %q", evt.CommandName, "ping")
		}
	})
}

func TestRunAdminCommandD(t *testing.T) {
	runMockMongo(t, "success", func(mt *mtest.T) {
		mt.AddMockResponses(mtest.CreateSuccessResponse(bson.E{Key: "value", Value: "ok"}))

		var out struct {
			Value string `bson:"value"`
		}
		if err := RunAdminCommandD(mt.Client, bson.D{{Key: "hello", Value: 1}}, 5, &out); err != nil {
			t.Fatalf("RunAdminCommandD failed: %v", err)
		}
		if out.Value != "ok" {
			t.Fatalf("decoded value = %q, want %q", out.Value, "ok")
		}

		evt := lastStartedEvent(t, mt)
		if evt.DatabaseName != AdminDB {
			t.Fatalf("database = %q, want %q", evt.DatabaseName, AdminDB)
		}
		if evt.CommandName != "hello" {
			t.Fatalf("command = %q, want %q", evt.CommandName, "hello")
		}
	})
}

func TestRunCommandWithVal(t *testing.T) {
	runMockMongo(t, "success", func(mt *mtest.T) {
		mt.AddMockResponses(mtest.CreateSuccessResponse(bson.E{Key: "value", Value: "ok"}))

		var out struct {
			Value string `bson:"value"`
		}
		if err := RunCommandWithVal(mt.Client, "custom_db", "customCommand", "customValue", 5, &out); err != nil {
			t.Fatalf("RunCommandWithVal failed: %v", err)
		}
		if out.Value != "ok" {
			t.Fatalf("decoded value = %q, want %q", out.Value, "ok")
		}

		evt := lastStartedEvent(t, mt)
		if evt.DatabaseName != "custom_db" {
			t.Fatalf("database = %q, want %q", evt.DatabaseName, "custom_db")
		}
		if evt.CommandName != "customCommand" {
			t.Fatalf("command = %q, want %q", evt.CommandName, "customCommand")
		}
		if got, ok := evt.Command.Lookup("customCommand").StringValueOK(); !ok || got != "customValue" {
			t.Fatalf("customCommand value = %q, ok = %t, want %q", got, ok, "customValue")
		}
	})
}

func TestRunCommand(t *testing.T) {
	runMockMongo(t, "success", func(mt *mtest.T) {
		mt.AddMockResponses(mtest.CreateSuccessResponse(bson.E{Key: "value", Value: "ok"}))

		var out struct {
			Value string `bson:"value"`
		}
		if err := RunCommand(mt.Client, "custom_db", "ping", 5, &out); err != nil {
			t.Fatalf("RunCommand failed: %v", err)
		}
		if out.Value != "ok" {
			t.Fatalf("decoded value = %q, want %q", out.Value, "ok")
		}

		evt := lastStartedEvent(t, mt)
		if evt.DatabaseName != "custom_db" {
			t.Fatalf("database = %q, want %q", evt.DatabaseName, "custom_db")
		}
		if evt.CommandName != "ping" {
			t.Fatalf("command = %q, want %q", evt.CommandName, "ping")
		}
		if got, ok := evt.Command.Lookup("ping").AsInt32OK(); !ok || got != 1 {
			t.Fatalf("ping value = %d, ok = %t, want %d", got, ok, 1)
		}
	})
}

func TestGetVersion(t *testing.T) {
	runMockMongo(t, "success", func(mt *mtest.T) {
		mt.AddMockResponses(mtest.CreateSuccessResponse(
			bson.E{Key: "version", Value: "6.0.12"},
			bson.E{Key: "versionArray", Value: bson.A{6, 0, 12, 0}},
		))

		version, err := GetVersion(mt.Client, 5)
		if err != nil {
			t.Fatalf("GetVersion failed: %v", err)
		}
		if version != "6.0" {
			t.Fatalf("version = %q, want %q", version, "6.0")
		}

		evt := lastStartedEvent(t, mt)
		if evt.DatabaseName != AdminDB {
			t.Fatalf("database = %q, want %q", evt.DatabaseName, AdminDB)
		}
		if evt.CommandName != "buildinfo" {
			t.Fatalf("command = %q, want %q", evt.CommandName, "buildinfo")
		}
	})
}

func TestGetVersionBadVersionArray(t *testing.T) {
	runMockMongo(t, "bad version array", func(mt *mtest.T) {
		mt.AddMockResponses(mtest.CreateSuccessResponse(
			bson.E{Key: "version", Value: "6.0.12"},
			bson.E{Key: "versionArray", Value: bson.A{6, 0}},
		))

		if _, err := GetVersion(mt.Client, 5); err == nil {
			t.Fatal("expected bad version array error")
		}
	})
}
