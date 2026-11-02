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

package migrator

import (
	"errors"
	"fmt"
	"testing"

	"github.com/go-sql-driver/mysql"
)

func TestUnknownVariable(t *testing.T) {
	unknown := &mysql.MySQLError{Number: unknownSystemVariableCode}
	cases := []struct {
		name string
		err  error
		want bool
	}{
		{name: "mysql unknown variable", err: unknown, want: true},
		{name: "wrapped mysql unknown variable", err: fmt.Errorf("load server, errmsg: %w", unknown), want: true},
		{name: "other mysql error", err: &mysql.MySQLError{Number: 1045}, want: false},
		{name: "plain error", err: errors.New("unknown system variable"), want: false},
	}
	for _, item := range cases {
		t.Run(item.name, func(t *testing.T) {
			if got := unknownVariable(item.err); got != item.want {
				t.Fatalf("unknown variable, got: %t, want: %t", got, item.want)
			}
		})
	}
}
