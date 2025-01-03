// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlerrlog

import (
	"bufio"
	"log/slog"
	"os"
	"path/filepath"
	"strconv"

	"github.com/jmoiron/sqlx"
)

func snapShot(db *sqlx.DB) error {
	errLogPath, err := findErrLogFile(db)
	if err != nil {
		return err
	}
	slog.Info("snap shot err log", slog.String("path", errLogPath))

	scanner, offset, err := newScanner(errLogPath)
	if err != nil {
		return err
	}

	regFile, err := os.OpenFile(
		errLogRegFile,
		os.O_CREATE|os.O_TRUNC|os.O_RDWR,
		0755,
	)
	if err != nil {
		slog.Error("create reg file", slog.String("error", err.Error()))
		return err
	}

	for scanner.Scan() {
		content := scanner.Bytes()
		err := scanner.Err()
		if err != nil {
			slog.Error("scan err log", err)
			return err
		}
		offset += int64(len(content)) + 1

		startMatch, err := rowStartPattern.MatchString(string(content))
		if err != nil {
			slog.Error("apply row start pattern", slog.String("error", err.Error()))
			return err
		}

		baseErrTokenMatch, err := baseErrTokenPattern.MatchString(string(content))
		if err != nil {
			slog.Error("apply base error token pattern", slog.String("error", err.Error()))
			return err
		}

		if startMatch && baseErrTokenMatch {
			_, err = regFile.Write(append(content, []byte("\n")...))
			if err != nil {
				slog.Error("write errlog.reg", err)
				return err
			}
		}
	}

	f, err := os.OpenFile(offsetRegFile, os.O_CREATE|os.O_TRUNC|os.O_RDWR, 0755)
	if err != nil {
		slog.Error("open offset reg", slog.String("error", err.Error()))
		return err
	}
	_, err = f.WriteString(strconv.FormatInt(offset, 10))
	if err != nil {
		slog.Error("update offset reg", slog.String("error", err.Error()))
		return err
	}

	//scanned = true
	return nil
}

func loadSnapShot() (*bufio.Scanner, error) {
	f, err := os.Open(errLogRegFile)
	if err != nil {
		slog.Error("open err log reg", slog.String("error", err.Error()))
		return nil, err
	}

	return bufio.NewScanner(f), nil
}

func findErrLogFile(db *sqlx.DB) (string, error) {
	var errLogPath, dataDir string
	err := db.QueryRowx(`SELECT @@LOG_ERROR, @@DATADIR`).Scan(&errLogPath, &dataDir)
	if err != nil {
		slog.Error("query log_error, datadir", slog.String("error", err.Error()))
		return "", err
	}

	if !filepath.IsAbs(errLogPath) {
		errLogPath = filepath.Join(dataDir, errLogPath)
	}
	return errLogPath, nil
}

func newScanner(logPath string) (*bufio.Scanner, int64, error) {
	f, err := os.Open(logPath)
	if err != nil {
		slog.Error("open err log", slog.String("error", err.Error()))
		return nil, 0, err
	}

	st, err := f.Stat()
	if err != nil {
		slog.Error("stat of err log", slog.String("error", err.Error()))
		return nil, 0, err
	}
	errLogSize := st.Size()
	slog.Debug("snap shot err log", slog.Int64("err log size", errLogSize))

	lastOffset, err := lastRoundOffset()
	if err != nil {
		return nil, 0, err
	}

	slog.Debug("snap shot err log", slog.Int64("last offset", lastOffset))

	// errlog 应该是被 rotate 了
	if errLogSize < lastOffset {
		lastOffset = 0
	}

	if errLogSize-lastOffset > maxScanSize {
		lastOffset = errLogSize - maxScanSize - 1
	}

	offset, err := f.Seek(lastOffset, 0)
	if err != nil {
		slog.Error("seek err log", slog.String("error", err.Error()))
		return nil, 0, err
	}

	return bufio.NewScanner(f), offset, nil
}

func lastRoundOffset() (int64, error) {
	content, err := os.ReadFile(offsetRegFile)

	if err != nil {
		if os.IsNotExist(err) {
			return 0, nil
		}
		slog.Error("read offset reg", err, slog.String("file", offsetRegFile))
		return 0, err
	}

	slog.Info("read offset reg", slog.String("offset", string(content)))

	r, err := strconv.ParseInt(string(content), 10, 64)
	if err != nil {
		slog.Warn("parse last offset", slog.String("error", err.Error()))
		return 0, nil
	}

	return r, nil
}
