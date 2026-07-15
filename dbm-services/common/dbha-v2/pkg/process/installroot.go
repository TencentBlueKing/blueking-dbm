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

package process

import (
	"os"
	"path/filepath"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// InstallRoot returns the installation root directory for a packaged layout
// where the binary lives in <root>/bin/<name>. Relative pid/log/runtime paths
// and ensure(chdir) use this as the working directory anchor.
func InstallRoot() (string, error) {
	exe, err := os.Executable()
	if err != nil {
		return "", gerrors.NewE(gerrors.Failure, err)
	}
	if resolved, err := filepath.EvalSymlinks(exe); err == nil {
		exe = resolved
	}
	root := filepath.Clean(filepath.Join(filepath.Dir(exe), ".."))
	return root, nil
}

// ChdirInstallRoot changes the process working directory to InstallRoot()
// and verifies a packaged layout (<root>/bin exists).
func ChdirInstallRoot() (string, error) {
	root, err := InstallRoot()
	if err != nil {
		return "", err
	}
	binDir := filepath.Join(root, "bin")
	if st, err := os.Stat(binDir); err != nil || !st.IsDir() {
		return "", gerrors.Newf(gerrors.Failure, "install root missing bin/, path: %s", root)
	}
	if err := os.Chdir(root); err != nil {
		return "", gerrors.NewE(gerrors.Failure, err)
	}
	return root, nil
}
