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

// Package kms loads and decrypts BlueKing KMS envelopes for DBM services.
package kms

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/TencentBlueKing/bk-kms-sdk/go/decrypt"
)

// Shared environment names match the parent Chart's KMS injection.
const (
	EnabledEnv    = "ENABLE_KMS"
	PrivateKeyEnv = "BK_DBM_KMS_PRIVATE_KEY"
)

// LoadOptions configures the mounted envelope location used by a service.
type LoadOptions struct {
	CredentialDirEnv string
	// EnvelopeFile defaults to "envelope" and must be a single file name.
	EnvelopeFile string
}

// Enabled accepts only true/false. An unset variable disables KMS.
func Enabled() (bool, error) {
	switch os.Getenv(EnabledEnv) {
	case "", "false":
		return false, nil
	case "true":
		return true, nil
	default:
		return false, fmt.Errorf("%s must be true or false", EnabledEnv)
	}
}

// LoadEnvelope returns plaintext only after successful decryption. enabled
// reports the switch state even on a load error. Disabled KMS returns
// ("", false, nil) without reading secrets.
// Each call reads a fresh envelope; callers own startup caching and validation.
// Errors expose only stages or configuration names, never SDK errors or input.
func LoadEnvelope(opts LoadOptions) (plaintext string, enabled bool, err error) {
	enabled, err = Enabled()
	if err != nil || !enabled {
		return "", enabled, err
	}
	if opts.CredentialDirEnv == "" {
		return "", true, errors.New("KMS credential directory environment name must not be empty")
	}
	file := opts.EnvelopeFile
	if file == "" {
		file = "envelope"
	}
	if file == "." || file == ".." || strings.ContainsAny(file, "/\\") {
		return "", true, errors.New("KMS envelope file must be a single file name")
	}
	privateKey := strings.TrimSpace(os.Getenv(PrivateKeyEnv))
	if err := RequireNonEmpty(privateKey, PrivateKeyEnv); err != nil {
		return "", true, err
	}
	dir := strings.TrimSpace(os.Getenv(opts.CredentialDirEnv))
	if err := RequireNonEmpty(dir, opts.CredentialDirEnv); err != nil {
		return "", true, err
	}
	// Resolve Kubernetes' projected Secret generation once before reading it.
	dataDir, err := filepath.EvalSymlinks(filepath.Join(dir, "..data"))
	if errors.Is(err, os.ErrNotExist) {
		dataDir = dir
	} else if err != nil {
		return "", true, errors.New("failed to resolve KMS credential directory")
	}
	envelope, err := os.ReadFile(filepath.Join(dataDir, file))
	if err != nil || len(strings.TrimSpace(string(envelope))) == 0 {
		return "", true, fmt.Errorf("failed to read KMS credential file %s", file)
	}
	plaintext, err = decrypt.Decrypt(strings.TrimSpace(string(envelope)), privateKey)
	if err != nil {
		return "", true, errors.New("failed to decrypt KMS runtime credentials")
	}
	return plaintext, true, nil
}

// DecodeJSON decodes a credential document without exposing JSON error details.
// Services supply their own structure and validate the fields they consume.
func DecodeJSON(plaintext string, target any) error {
	if err := json.Unmarshal([]byte(plaintext), target); err != nil {
		return errors.New("invalid KMS runtime credential document")
	}
	return nil
}

// RequireNonEmpty checks for blank values while preserving credential contents.
// field must be a static field or configuration name, never sensitive input.
func RequireNonEmpty(value, field string) error {
	if strings.TrimSpace(value) == "" {
		return fmt.Errorf("KMS credential field %s must not be empty", field)
	}
	return nil
}
