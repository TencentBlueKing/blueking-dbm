package atommongodb

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLocateDumpRoot(t *testing.T) {
	root := t.TempDir()

	nested := filepath.Join(root, "nested")
	if err := os.MkdirAll(filepath.Join(nested, "dump", "app"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(nested, "dump", "app", "orders.bson"), []byte("x"), 0644); err != nil {
		t.Fatal(err)
	}
	got, err := locateDumpRoot(nested)
	if err != nil {
		t.Fatal(err)
	}
	if got != filepath.Join(nested, "dump") {
		t.Fatalf("nested layout: got %s", got)
	}

	flat := filepath.Join(root, "flat")
	if err := os.MkdirAll(filepath.Join(flat, "pr21833migb359"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(flat, "dump.log"), []byte("ok"), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(flat, "pr21833migb359", "orders.bson"), []byte("x"), 0644); err != nil {
		t.Fatal(err)
	}
	got, err = locateDumpRoot(flat)
	if err != nil {
		t.Fatal(err)
	}
	if got != flat {
		t.Fatalf("flat layout: got %s", got)
	}
}
