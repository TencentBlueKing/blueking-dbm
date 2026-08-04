/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package crypto provides symmetric decryption helpers used by dbactuator
// to consume sensitive secrets passed in via parameters (e.g. remote login
// passwords for linked-server cloning).
//
// Contract with the caller (DBM ticket layer):
//
//	key       = SHA-256( host + "|" + salt )
//	nonce     = 12 random bytes
//	cipher    = AES-256-GCM( key, nonce, plaintext )
//	transport = base64_std( nonce || cipher )   // nonce prepended
//
// The `host` is the target-instance host (the same value passed in as
// CloneLinkserversParam.Host), so different targets naturally derive
// different keys — leaking a ciphertext for host A cannot be replayed
// on host B.
package crypto

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"fmt"
)

// linkserverSecretSalt is the hardcoded salt shared between DBM (Python)
// and dbactuator (Go). Rotating it requires a coordinated release on both sides.
const linkserverSecretSalt = "dbm-sqlserver-login-secret-v1"

// DeriveKey derives a 32-byte AES-256 key from the target host and the
// hardcoded salt: key = SHA-256(host + "|" + salt).
func DeriveKey(host string) []byte {
	sum := sha256.Sum256([]byte(host + "|" + linkserverSecretSalt))
	return sum[:]
}

// DecryptLinkserverSecret decrypts a base64(nonce||ciphertext) blob using
// AES-256-GCM with a key derived from the given host.
//
// Returns the plaintext password, or an error if the blob is malformed or
// authentication fails (which typically means the host / salt / ciphertext
// were tampered with, or the encrypting side used a wrong host).
func DecryptLinkserverSecret(host, b64Payload string) (string, error) {
	if b64Payload == "" {
		return "", errors.New("empty ciphertext payload")
	}
	raw, err := base64.StdEncoding.DecodeString(b64Payload)
	if err != nil {
		return "", fmt.Errorf("base64 decode failed: %w", err)
	}

	block, err := aes.NewCipher(DeriveKey(host))
	if err != nil {
		return "", fmt.Errorf("aes new cipher failed: %w", err)
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", fmt.Errorf("gcm init failed: %w", err)
	}
	ns := gcm.NonceSize()
	if len(raw) < ns+gcm.Overhead() {
		return "", errors.New("ciphertext too short")
	}
	nonce, ct := raw[:ns], raw[ns:]
	pt, err := gcm.Open(nil, nonce, ct, nil)
	if err != nil {
		return "", fmt.Errorf("gcm open failed (bad host/salt/ciphertext): %w", err)
	}
	return string(pt), nil
}
