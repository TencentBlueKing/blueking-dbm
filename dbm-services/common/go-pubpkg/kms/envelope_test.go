/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package kms

import (
	"dbm-services/common/go-pubpkg/kms/testhelper"
	"encoding/base64"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

var testOptions = LoadOptions{CredentialDirEnv: "PUBPKG_KMS_TEST_DIR"}

func TestLoadEnvelope(t *testing.T) {
	for _, projected := range []bool{false, true} {
		t.Run(map[bool]string{false: "directory", true: "projected-secret"}[projected], func(t *testing.T) {
			plaintext := `{"mysql":{"service":{"password":" keep spaces!@#:%/ "}}}`
			envelope, key := testhelper.Envelope(t, plaintext)
			dir := t.TempDir()
			dataDir := dir
			if projected {
				dataDir = filepath.Join(dir, "generation")
				if err := os.Mkdir(dataDir, 0700); err != nil {
					t.Fatal(err)
				}
				if err := os.Symlink("generation", filepath.Join(dir, "..data")); err != nil {
					t.Fatal(err)
				}
			}
			opts := testOptions
			opts.EnvelopeFile = "custom-envelope"
			path := filepath.Join(dataDir, opts.EnvelopeFile)
			if err := os.WriteFile(path, []byte(envelope+"\n"), 0600); err != nil {
				t.Fatal(err)
			}
			t.Setenv(EnabledEnv, "true")
			t.Setenv(PrivateKeyEnv, key)
			t.Setenv(opts.CredentialDirEnv, dir)
			got, enabled, err := LoadEnvelope(opts)
			if err != nil {
				t.Fatal(err)
			}
			if !enabled || got != plaintext {
				t.Fatal("decrypted contents changed")
			}
			// The shared loader is deliberately uncached: service startup owns caching.
			if err := os.WriteFile(path, []byte("invalid replacement"), 0600); err != nil {
				t.Fatal(err)
			}
			got, enabled, err = LoadEnvelope(opts)
			if !enabled || got != "" || err == nil {
				t.Fatal("loader unexpectedly reused cached plaintext")
			}
		})
	}
}

func TestGating(t *testing.T) {
	for _, flag := range []string{"", "false", "true", "TRUE", "1", " false "} {
		t.Run("enabled="+flag, func(t *testing.T) {
			t.Setenv(EnabledEnv, flag)
			t.Setenv(PrivateKeyEnv, "")
			t.Setenv(testOptions.CredentialDirEnv, "")
			plaintext, enabled, err := LoadEnvelope(testOptions)
			if plaintext != "" {
				t.Fatal("unexpected plaintext")
			}
			if flag == "" || flag == "false" {
				if enabled || err != nil {
					t.Fatal("disabled loader accessed credentials")
				}
			} else if err == nil {
				t.Fatal("invalid or incomplete configuration accepted")
			}
		})
	}
}

func TestInvalidInputsAreRedacted(t *testing.T) {
	for _, input := range []string{"", "private-input-marker", base64.StdEncoding.EncodeToString([]byte(`{"asymmetric_type":"private-input-marker"}`))} {
		t.Run("invalid-envelope", func(t *testing.T) {
			dir := t.TempDir()
			if err := os.WriteFile(filepath.Join(dir, "envelope"), []byte(input), 0600); err != nil {
				t.Fatal(err)
			}
			t.Setenv(EnabledEnv, "true")
			t.Setenv(PrivateKeyEnv, "private-key-marker")
			t.Setenv(testOptions.CredentialDirEnv, dir)
			plaintext, enabled, err := LoadEnvelope(testOptions)
			if plaintext != "" || !enabled || err == nil {
				t.Fatal("invalid envelope accepted")
			}
			if strings.Contains(err.Error(), "marker") || strings.Contains(err.Error(), dir) {
				t.Fatal("error leaked credential input")
			}
		})
	}
}

func TestInvalidOptionsAndMissingInputs(t *testing.T) {
	t.Setenv(EnabledEnv, "true")
	t.Setenv(PrivateKeyEnv, "key")
	t.Setenv(testOptions.CredentialDirEnv, t.TempDir())
	for _, file := range []string{".", "..", "../envelope", "/envelope", `dir\envelope`} {
		opts := testOptions
		opts.EnvelopeFile = file
		if _, _, err := LoadEnvelope(opts); err == nil {
			t.Fatal("unsafe envelope filename accepted")
		}
	}
	for _, opts := range []LoadOptions{{}} {
		if _, _, err := LoadEnvelope(opts); err == nil {
			t.Fatal("incomplete options accepted")
		}
	}
	for _, missing := range []string{"key", "directory", "file"} {
		t.Run(missing, func(t *testing.T) {
			t.Setenv(PrivateKeyEnv, "key")
			t.Setenv(testOptions.CredentialDirEnv, t.TempDir())
			if missing == "key" {
				t.Setenv(PrivateKeyEnv, "")
			}
			if missing == "directory" {
				t.Setenv(testOptions.CredentialDirEnv, "")
			}
			if plaintext, enabled, err := LoadEnvelope(testOptions); plaintext != "" || !enabled || err == nil {
				t.Fatal("missing credential input accepted")
			}
		})
	}
}

func TestJSONAndRequiredFields(t *testing.T) {
	var doc struct {
		Password string `json:"password"`
	}
	if err := DecodeJSON(`{"password":" keep spaces ","unknown":true}`, &doc); err != nil {
		t.Fatal(err)
	}
	if doc.Password != " keep spaces " {
		t.Fatal("password changed")
	}
	if err := RequireNonEmpty(doc.Password, "mysql.service.password"); err != nil {
		t.Fatal(err)
	}
	if err := RequireNonEmpty(" \n", "mysql.service.password"); err == nil || !strings.Contains(err.Error(), "mysql.service.password") {
		t.Fatal("required field not validated")
	}
	if err := DecodeJSON(`{"password":"private-marker`, &doc); err == nil || strings.Contains(err.Error(), "marker") {
		t.Fatal("JSON error accepted or leaked input")
	}
}
