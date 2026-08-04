/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package sink

import (
	"testing"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// TestMySQLSaveUnknownClusterTypeOK asserts Save does not reject probe payloads whose
// cluster_type is unregistered; receiver storage is db-type agnostic and only needs
// valid HarvestData JSON (dbs may be nil — no DB write is required for this check).
func TestMySQLSaveUnknownClusterTypeOK(t *testing.T) {
	payload := []byte(`{
		"cluster_type":"someFutureDb",
		"db_type_name":"future",
		"machine_type":"future_machine",
		"db_ip":"127.0.0.1",
		"db_port":6379,
		"data":{"x":1}
	}`)

	s := &mysql{}
	err := s.Save(&Message{Topic: "probe", Data: payload})
	if err != nil {
		t.Fatalf("Save returned error for unknown cluster_type, errmsg: %s", err)
	}
}

// TestMySQLSaveInvalidJSON asserts Save rejects non-JSON payloads with InvalidJson.
func TestMySQLSaveInvalidJSON(t *testing.T) {
	s := &mysql{}
	err := s.Save(&Message{Topic: "probe", Data: []byte("not-json")})
	if err == nil {
		t.Fatal("Save returned nil error for invalid JSON, want InvalidJson")
	}
	ge, ok := err.(*gerrors.Error)
	if !ok {
		t.Fatalf("error type = %T, want *gerrors.Error", err)
	}
	if !ge.HasCode(gerrors.InvalidJson) {
		t.Fatalf("error code = %d, want InvalidJson", ge.Code())
	}
}
