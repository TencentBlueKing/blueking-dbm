package ibd_statistic

import (
	"io/fs"
	"os"
	"path/filepath"
	"strings"

	"golang.org/x/exp/slog"
)

func collectResult(dataDir string) (map[string]map[string]int64, error) {
	result := make(map[string]map[string]int64)

	err := filepath.WalkDir(
		dataDir, func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				return fs.SkipDir
			}

			if !d.IsDir() && strings.ToLower(filepath.Ext(d.Name())) == ibdExt {
				dir := filepath.Dir(path)
				dbName := filepath.Base(dir)

				var tableName string

				match := partitionPattern.FindStringSubmatch(d.Name())

				if match == nil {
					tableName = strings.TrimSuffix(d.Name(), ibdExt)
				} else {
					tableName = match[1]
				}

				st, err := os.Stat(path)
				if err != nil {
					slog.Error("ibd-statistic collect result", err)
					return err
				}

				if _, ok := result[dbName]; !ok {
					result[dbName] = make(map[string]int64)
				}
				if _, ok := result[dbName][tableName]; !ok {
					result[dbName][tableName] = 0
				}

				result[dbName][tableName] += st.Size()
			}
			return nil
		},
	)

	if err != nil {
		slog.Error("ibd-statistic collect result", err)
		return nil, err
	}

	return result, nil
}
