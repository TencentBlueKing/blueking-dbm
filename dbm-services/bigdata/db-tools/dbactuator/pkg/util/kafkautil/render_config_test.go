package kafkautil

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// TestCreateServerPropertiesFile_RendersUsernameIntoSuperUsers ensures {{.Username}} is
// substituted when rendering super.users, so ACL grants the actual per-cluster admin account
// rather than leaving the placeholder literal in server.properties.
func TestCreateServerPropertiesFile_RendersUsernameIntoSuperUsers(t *testing.T) {
	jsonData := []byte(`{
		"super.users": "User:{{.Username}};User:kafka",
		"authorizer.class.name": "kafka.security.authorizer.AclAuthorizer"
	}`)
	templateData := TemplateData{Username: "test_admin"}

	filePath := filepath.Join(t.TempDir(), "server.properties")
	if err := CreateServerPropertiesFile(jsonData, templateData, filePath); err != nil {
		t.Fatalf("CreateServerPropertiesFile failed: %v", err)
	}

	content, err := os.ReadFile(filePath)
	if err != nil {
		t.Fatalf("failed to read rendered file: %v", err)
	}

	lines := strings.Split(strings.TrimSpace(string(content)), "\n")
	found := false
	for _, line := range lines {
		if line == "super.users=User:test_admin;User:kafka" {
			found = true
		}
		if strings.Contains(line, "{{.Username}}") {
			t.Fatalf("super.users placeholder was not rendered: %q", line)
		}
	}
	if !found {
		t.Fatalf("expected rendered super.users line not found, got: %v", lines)
	}
}
