// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

// The replay no longer splits tredisbinlog output; this copy of redis-cli's sdssplitargs stays
// in tests as the reference the native decoder's commands are compared against.

// splitArgs splits a line the way redis-cli does (sdssplitargs), undoing tredisbinlog's
// sdscatrepr: double quotes with \xHH, \n, \r, \t, \b, \a and \<c> escapes, single quotes with
// \', and bare words, which only end at a space, \n, \r or \t. A quote may start mid-word; a
// closing quote must end the word. ok is false on unbalanced quotes, where redis-cli prints
// "Invalid argument(s)" and sends nothing.
func splitArgs(line string) (args []string, ok bool) {
	i, n := 0, len(line)
	isSpace := func(c byte) bool { return c == ' ' || c == '\n' || c == '\r' || c == '\t' || c == '\v' || c == '\f' }
	for {
		for i < n && isSpace(line[i]) {
			i++
		}
		if i >= n {
			return args, true
		}
		var cur []byte
		inq, insq := false, false
		for done := false; !done; {
			switch {
			case inq:
				switch {
				case i >= n:
					return nil, false
				case line[i] == '\\' && i+3 < n && line[i+1] == 'x' && isHex(line[i+2]) && isHex(line[i+3]):
					cur = append(cur, hexVal(line[i+2])<<4|hexVal(line[i+3]))
					i += 3
				case line[i] == '\\' && i+1 < n:
					i++
					switch c := line[i]; c {
					case 'n':
						cur = append(cur, '\n')
					case 'r':
						cur = append(cur, '\r')
					case 't':
						cur = append(cur, '\t')
					case 'b':
						cur = append(cur, '\b')
					case 'a':
						cur = append(cur, '\a')
					default:
						cur = append(cur, c)
					}
				case line[i] == '"':
					if i+1 < n && !isSpace(line[i+1]) {
						return nil, false
					}
					done = true
				default:
					cur = append(cur, line[i])
				}
			case insq:
				switch {
				case i >= n:
					return nil, false
				case line[i] == '\\' && i+1 < n && line[i+1] == '\'':
					i++
					cur = append(cur, '\'')
				case line[i] == '\'':
					if i+1 < n && !isSpace(line[i+1]) {
						return nil, false
					}
					done = true
				default:
					cur = append(cur, line[i])
				}
			default:
				switch {
				case i >= n || line[i] == ' ' || line[i] == '\n' || line[i] == '\r' || line[i] == '\t':
					done = true
				case line[i] == '"':
					inq = true
				case line[i] == '\'':
					insq = true
				default:
					cur = append(cur, line[i])
				}
			}
			if i < n {
				i++
			}
		}
		args = append(args, string(cur))
	}
}

func isHex(c byte) bool {
	return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')
}

func hexVal(c byte) byte {
	switch {
	case c >= '0' && c <= '9':
		return c - '0'
	case c >= 'a' && c <= 'f':
		return c - 'a' + 10
	default:
		return c - 'A' + 10
	}
}
