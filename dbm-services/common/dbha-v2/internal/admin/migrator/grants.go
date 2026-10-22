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

import "strings"

const (
	grantGlobal   = "global"
	grantDatabase = "database"
	grantTable    = "table"
)

var writePrivileges = []string{"SELECT", "INSERT", "UPDATE", "CREATE", "ALTER", "INDEX"}

type grantSet struct {
	privs map[string]bool
	all   bool
}

func (g *grantSet) add(privs []string) {
	if g.privs == nil {
		g.privs = map[string]bool{}
	}
	for _, priv := range privs {
		priv = strings.ToUpper(strings.TrimSpace(priv))
		if priv == "ALL" || priv == "ALL PRIVILEGES" {
			g.all = true
			continue
		}
		g.privs[priv] = true
	}
}

func (g grantSet) canCreate() bool {
	return g.all || g.privs["CREATE"]
}

func (g grantSet) canWrite(other grantSet) bool {
	if g.all || other.all {
		return true
	}
	for _, priv := range writePrivileges {
		if !g.privs[priv] && !other.privs[priv] {
			return false
		}
	}
	return true
}

func parseGrant(line string) ([]string, string, string, bool) {
	upper := strings.ToUpper(line)
	if !strings.HasPrefix(upper, "GRANT ") {
		return nil, "", "", false
	}
	on := strings.Index(upper, " ON ")
	toRel := strings.Index(upper, " TO ")
	if on < len("GRANT ") || toRel < 0 || toRel < on+len(" ON ") {
		return nil, "", "", false
	}
	privPart := strings.TrimSpace(line[len("GRANT "):on])
	scopePart := strings.TrimSpace(line[on+len(" ON ") : toRel])
	if privPart == "" || strings.Contains(privPart, "(") {
		return nil, "", "", false
	}
	kind, name, ok := parseGrantScope(scopePart)
	if !ok {
		return nil, "", "", false
	}
	return strings.Split(privPart, ","), kind, name, true
}

func parseGrantScope(scope string) (string, string, bool) {
	scope = strings.ReplaceAll(scope, "`", "")
	parts := strings.Split(scope, ".")
	if len(parts) != 2 {
		return "", "", false
	}
	left := strings.TrimSpace(parts[0])
	right := strings.TrimSpace(parts[1])
	switch {
	case left == "*" && right == "*":
		return grantGlobal, "", true
	case right == "*" && left != "" && left != "*":
		return grantDatabase, left, true
	case left != "" && right != "" && left != "*" && right != "*":
		return grantTable, left, true
	default:
		return "", "", false
	}
}
