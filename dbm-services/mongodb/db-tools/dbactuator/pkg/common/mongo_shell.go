package common

import (
	"fmt"
	"os"
	"path/filepath"
)

// ResolveMongoShellBin 选择客户端。
// 优先使用可执行的 mongosh；没有 mongosh 时回退到 mongo。
// 不要通过执行 mongod/mongos 探测版本，避免二进制损坏时连清理任务都无法初始化。
func ResolveMongoShellBin(binDir string) (string, error) {
	for _, name := range []string{"mongosh", "mongo"} {
		path := filepath.Join(binDir, "mongodb", "bin", name)
		info, err := os.Stat(path)
		if err == nil && !info.IsDir() && info.Mode()&0o111 != 0 {
			return path, nil
		}
	}
	return "", fmt.Errorf("mongo shell not found under %s", filepath.Join(binDir, "mongodb", "bin"))
}
