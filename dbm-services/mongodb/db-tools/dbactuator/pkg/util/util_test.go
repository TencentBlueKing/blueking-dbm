package util

import (
	"fmt"
	"os"
	"path"
	"testing"
	"time"
)

func TestDeleteBadLink(t *testing.T) {
	// 创建一个临时目录
	dirName := fmt.Sprintf("%d", time.Now().UnixNano())
	dirPath := path.Join("/tmp", dirName)
	err := os.Mkdir(dirPath, 0755)
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}

	defer os.RemoveAll(dirPath) // 确保在测试结束时删除临时目录
	// 创建一个坏链接

	linkPath := fmt.Sprintf("%s-link", dirPath)
	t.Logf("dirPath: %s linkPath:%s", dirPath, linkPath)
	err = os.Symlink(dirPath, linkPath)
	if err != nil {
		t.Fatalf("Failed to create bad link: %v", err)
	}
	deleted, err := TryDeleteBadLink(linkPath)
	t.Logf("deleted: %v, err: %v", deleted, err)
	os.RemoveAll(dirPath)
	deleted, err = TryDeleteBadLink(linkPath)
	t.Logf("deleted: %v, err: %v", deleted, err)
}
