// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"bufio"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

// passwordDir is where a port's config files are, replaced in tests.
var passwordDir = func(port int) string {
	return filepath.Join(consts.GetRedisDataDir(), "redis", strconv.Itoa(port))
}

// cachedPassword is a port dir's requirepass together with the conf files it was read from.
// A later Prepare or CONFIG REWRITE changes the stamp, and the next connection reads again.
type cachedPassword struct {
	password string
	stamp    string
}

var passwords = struct {
	mu sync.Mutex
	m  map[string]cachedPassword
}{m: map[string]cachedPassword{}}

// portPassword is the instance's requirepass. Like myredis.GetRedisPasswdFromConfFile, redis.conf
// is preferred over instance.conf and an instance without requirepass has an empty password;
// unlike it, nothing is spawned or logged. A dir is reused only while its conf files are unchanged,
// so a rewrite in this process is picked up on the next connection.
func portPassword(port int) (string, error) {
	dir := passwordDir(port)
	stamp, err := confStamp(dir)
	if err != nil {
		return "", err
	}
	passwords.mu.Lock()
	if cached, ok := passwords.m[dir]; ok && cached.stamp == stamp {
		passwords.mu.Unlock()
		return cached.password, nil
	}
	passwords.mu.Unlock()

	password, err := readPortPassword(dir)
	if err != nil {
		return "", err
	}
	// Skip the cache when the files moved during the read; the next call stamps them again.
	if after, err := confStamp(dir); err == nil && after == stamp {
		passwords.mu.Lock()
		passwords.m[dir] = cachedPassword{password: password, stamp: stamp}
		passwords.mu.Unlock()
	}
	return password, nil
}

// readPortPassword is the requirepass of dir. redis.conf wins when it has one; an empty
// requirepass is a real password and does not fall through to the other file.
func readPortPassword(dir string) (string, error) {
	found := false
	var password string
	for _, name := range []string{"redis.conf", "instance.conf"} {
		pass, err := confPassword(filepath.Join(dir, name))
		if errors.Is(err, fs.ErrNotExist) {
			continue
		}
		if err != nil {
			return "", err
		}
		found = true
		if pass != "" {
			password = pass
			break
		}
	}
	if !found {
		return "", fmt.Errorf("neither redis.conf nor instance.conf exists in %s", dir)
	}
	return password, nil
}

// confStamp identifies the two conf files a password was read from. A missing file is part of
// the stamp, so creating it later is a change.
func confStamp(dir string) (string, error) {
	var b strings.Builder
	for _, name := range []string{"redis.conf", "instance.conf"} {
		info, err := os.Stat(filepath.Join(dir, name))
		if errors.Is(err, fs.ErrNotExist) {
			b.WriteString("-\n")
			continue
		}
		if err != nil {
			return "", err
		}
		fmt.Fprintf(&b, "%d %d\n", info.ModTime().UnixNano(), info.Size())
	}
	return b.String(), nil
}

// confPassword is the first requirepass in conf, unquoted; empty when there is none.
func confPassword(conf string) (string, error) {
	f, err := os.Open(conf)
	if err != nil {
		return "", err
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 64*1024), 1024*1024)
	for sc.Scan() {
		fields := strings.Fields(sc.Text())
		if len(fields) == 0 || fields[0] != "requirepass" {
			continue
		}
		if len(fields) < 2 {
			return "", nil
		}
		return strings.TrimSuffix(strings.TrimPrefix(fields[1], `"`), `"`), nil
	}
	return "", sc.Err()
}
