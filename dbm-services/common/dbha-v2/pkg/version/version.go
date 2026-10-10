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

package version

import "fmt"

var (
	buildTime = ""
	gitTag    = ""
	gitHash   = ""
	version   = ""
)

// Info describes the build information injected via -ldflags at link time.
// All fields are empty strings when the binary is built without those ldflags.
type Info struct {
	BuildTime string
	GitTag    string
	GitHash   string
	Version   string
}

// Get returns the build information injected at link time.
func Get() Info {
	return Info{
		BuildTime: buildTime,
		GitTag:    gitTag,
		GitHash:   gitHash,
		Version:   version,
	}
}

// Print writes the service name and build information to stdout.
func Print(service string) {
	info := Get()
	fmt.Printf("%s\n", service)
	fmt.Printf("\tBuildTime:\t%s\n", info.BuildTime)
	fmt.Printf("\tGitTag:\t\t%s\n", info.GitTag)
	fmt.Printf("\tGitHash:\t%s\n", info.GitHash)
	fmt.Printf("\tVersion:\t%s\n", info.Version)
}
