package ext3_check

import (
	"io/fs"
	"os"
	"path/filepath"
)

func findHugeFile(dirs []string, threshold int64) (files []string, err error) {
	for _, dir := range dirs {
		err = filepath.WalkDir(
			dir, func(path string, d fs.DirEntry, err error) error {
				if err != nil {
					return filepath.SkipDir
				}

				st, sterr := os.Stat(path)
				if sterr != nil {
					return filepath.SkipDir
				}
				if !d.IsDir() && st.Size() >= threshold {
					files = append(files, path)
				}
				return nil
			},
		)
		if err != nil {
			return nil, err
		}
	}
	return files, nil
}
