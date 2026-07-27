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

// Package provider holds the single DB-type provider manifest.
// Run `go generate ./internal/provider/...` after editing Entries.
package provider

//go:generate go run ./internal/gen

// Capability declares which sub-packages a provider contributes.
type Capability string

const (
	CapDesc    Capability = "desc"
	CapHarvest Capability = "harvest"
	CapSwitch  Capability = "switch"
	CapParse   Capability = "parse"
)

// Entry describes one DB provider and the capabilities it exposes.
type Entry struct {
	// Name is a short identifier used in comments (e.g. "redis", "mysql").
	Name string
	// BasePath is the full import path of the provider root
	// (e.g. "dbm-services/common/dbha-v2/internal/provider/redis").
	BasePath string
	// Caps lists which sub-packages should be blank-imported by binaries.
	// CapDesc maps to "<BasePath>/dbtypedesc".
	// CapHarvest maps to "<BasePath>/harvest".
	// CapSwitch maps to "<BasePath>/switch".
	// CapParse maps to "<BasePath>/parse".
	Caps []Capability
}

const providerRoot = "dbm-services/common/dbha-v2/internal/provider"

// Entries is the single source of truth for provider blank-imports.
// MySQL mapping is a builtin placeholder in pkg/dbtype (providers may take it over).
// Redis mapping lives in provider/redis/dbtypedesc (CapDesc) as a pure-provider example.
var Entries = []Entry{
	{
		Name:     "mysql",
		BasePath: providerRoot + "/mysql",
		Caps:     []Capability{CapHarvest, CapSwitch},
	},
	{
		Name:     "redis",
		BasePath: providerRoot + "/redis",
		Caps:     []Capability{CapDesc, CapHarvest},
	},
}
