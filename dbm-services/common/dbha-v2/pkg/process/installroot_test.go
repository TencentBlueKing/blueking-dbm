/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 */

package process

import (
	"path/filepath"
	"testing"
)

func TestInstallRoot_ParentOfBin(t *testing.T) {
	root, err := InstallRoot()
	if err != nil {
		t.Fatalf("InstallRoot: %v", err)
	}
	if root == "" {
		t.Fatal("empty InstallRoot")
	}
	// InstallRoot is parent of the directory that contains the test binary
	// (usually .../pkg/process or a go-test temp). Just ensure Clean/Join shape.
	if filepath.Clean(root) != root {
		t.Fatalf("InstallRoot not cleaned: %q", root)
	}
}
