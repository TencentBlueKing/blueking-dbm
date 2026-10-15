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

// Package testhelper builds disposable KMS envelopes for integration tests.
package testhelper

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"testing"
)

// Generate a real RSA-OAEP/AES-CTR envelope using disposable keys, independently
// of the SDK implementation. Nothing here is a production credential.
func Envelope(t *testing.T, plaintext string) (string, string) {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatal(err)
	}
	symmetricKey := []byte("0123456789abcdef")
	encryptedKey, err := rsa.EncryptOAEP(sha256.New(), rand.Reader, &key.PublicKey, symmetricKey, nil)
	if err != nil {
		t.Fatal(err)
	}
	block, err := aes.NewCipher(symmetricKey)
	if err != nil {
		t.Fatal(err)
	}
	iv := make([]byte, aes.BlockSize)
	if _, err := rand.Read(iv); err != nil {
		t.Fatal(err)
	}
	ciphertext := make([]byte, len(plaintext))
	cipher.NewCTR(block, iv).XORKeyStream(ciphertext, []byte(plaintext))
	raw, err := json.Marshal(map[string]string{
		"asymmetric_type": "RSA", "symmetric_type": "AES", "symmetric_mode": "CTR",
		"encrypted_key": base64.StdEncoding.EncodeToString(encryptedKey),
		"ciphertext":    base64.StdEncoding.EncodeToString(append(iv, ciphertext...)),
	})
	if err != nil {
		t.Fatal(err)
	}
	privateKey := pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: x509.MarshalPKCS1PrivateKey(key)})
	return base64.StdEncoding.EncodeToString(raw), base64.StdEncoding.EncodeToString(privateKey)
}
