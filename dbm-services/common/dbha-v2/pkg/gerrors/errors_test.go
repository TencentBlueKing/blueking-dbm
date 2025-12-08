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

package gerrors_test

import (
	"errors"
	"testing"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

func TestError(t *testing.T) {
	err1 := gerrors.New(gerrors.InvalidParameter, "invalid user id")
	err2 := gerrors.Newf(gerrors.InvalidParameter, "invalid user id: %d", 123)

	if !errors.Is(err1, err2) {
		t.Error("err1 is not err2")
	}

	if !err1.HasCode(gerrors.InvalidParameter) {
		t.Error("err1 does not have code InvalidParameter")
	}

	stdErr := errors.New("connection failed")
	wrappedErr := gerrors.NewE(gerrors.NetException, stdErr)
	if !errors.Is(wrappedErr, stdErr) {
		t.Error("wrappedErr is not stdErr")
	}

	root := wrappedErr.RootCause()
	if root != stdErr {
		t.Error("root is not stdErr")
	}

	if errors.Unwrap(wrappedErr) != stdErr {
		t.Error("unwrap wrappedErr is not stdErr")
	}

	t.Log("Success")

}
