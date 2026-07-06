package offsetlinescanner

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
)

// 默认读缓冲区大小 64KB
const defaultBufSize = 64 * 1024

// OffsetCommitScanner 支持延迟提交 offset 的扫描器。
// 与 OffsetScanner 不同，它不会在每次 Scan() 时自动推进 offset reg 文件，
// 而是仅在显式调用 Commit() 时才将当前读取位置写入 reg 文件。
// 这样可以保证：只有完整处理成功的数据才推进 offset，避免半段数据丢失。
//
// reg 文件格式: "offset,inode"
// 通过 inode 对比可以精确检测文件轮转（logrotate），避免仅靠文件大小判断的漏洞。
//
// 链式读取（Rotate 场景）：
// 当检测到文件已被 rotate 时，Scanner 会先读完旧文件（rotated file）的剩余数据，
// 再无缝切换到新文件从头开始读取，对调用方完全透明。
type OffsetCommitScanner struct {
	filePath         string
	regPath          string
	f                *os.File
	rf               *os.File
	reader           *bufio.Reader
	err              error
	inode            uint64 // 当前文件的 inode
	pendingOffset    int64  // 当前已读取到的位置（尚未提交）
	lastCommitted    int64  // 上次已提交的 offset
	lastScannedBytes int64  // 上一次 scan 读取的字节数，用于根据下一次 scan 分段
	line             []byte // 当前行内容
	done             bool   // 是否已读取完毕

	// 链式读取相关字段（rotate 场景）
	rotatedFile    *os.File      // 旧文件（被 rotate 后的文件）句柄
	rotatedReader  *bufio.Reader // 旧文件的 reader
	readingRotated bool          // 当前是否正在读取旧文件
}

// getInode 获取文件的 inode 号
func getInode(fi os.FileInfo) (uint64, bool) {
	stat, ok := fi.Sys().(*syscall.Stat_t)
	if !ok {
		return 0, false
	}
	return stat.Ino, true
}

// Scan 读取下一行，更新 pendingOffset 但不写入 reg 文件。
// 如果处于链式读取模式（rotate 场景），会先读完旧文件剩余数据，
// 再自动切换到新文件继续读取，对调用方完全透明。
func (c *OffsetCommitScanner) Scan() bool {
	if c.done {
		return false
	}

	// 选择当前活跃的 reader
	activeReader := c.reader
	if c.readingRotated {
		activeReader = c.rotatedReader
	}

	line, isPrefix, err := activeReader.ReadLine()
	if err != nil {
		if err == io.EOF && c.readingRotated {
			// 旧文件读完，切换到新文件
			c.switchToNewFile()
			// 从新文件继续读取
			return c.Scan()
		}
		if err != io.EOF {
			c.err = err
		}
		c.done = true
		return false
	}

	if !isPrefix {
		// 快速路径：单行完整读取，复用 c.line 底层数组避免重复分配
		c.line = append(c.line[:0], line...)
	} else {
		// 慢路径：长行需要多次拼接
		fullLine := append([]byte(nil), line...)
		for isPrefix {
			line, isPrefix, err = activeReader.ReadLine()
			if err != nil {
				if err == io.EOF && c.readingRotated {
					// 旧文件在长行中间结束（异常情况），丢弃不完整行，切换到新文件
					c.switchToNewFile()
					return c.Scan()
				}
				if err != io.EOF {
					c.err = err
				}
				c.done = true
				return false
			}
			fullLine = append(fullLine, line...)
		}
		c.line = fullLine
	}

	// 精确计算本行占用的字节数：行内容 + 换行符(1字节)
	lineBytes := int64(len(c.line)) + 1
	c.lastScannedBytes = lineBytes
	c.pendingOffset += lineBytes
	return true
}

// switchToNewFile 从旧文件切换到新文件，关闭旧文件句柄，重置 offset 为新文件起始位置
func (c *OffsetCommitScanner) switchToNewFile() {
	if c.rotatedFile != nil {
		_ = c.rotatedFile.Close()
		c.rotatedFile = nil
		c.rotatedReader = nil
	}
	c.readingRotated = false
	// 切换到新文件后，pendingOffset 从 0 开始（新文件从头读）
	c.pendingOffset = 0
	c.lastCommitted = 0
}

// Bytes 返回当前行的字节内容（不含换行符）
func (c *OffsetCommitScanner) Bytes() []byte {
	return c.line
}

// Text 返回当前行的字符串内容（不含换行符）
func (c *OffsetCommitScanner) Text() string {
	return string(c.line)
}

// Commit 将当前 pendingOffset 写入 reg 文件，推进 offset。
// 应在完整段处理成功后调用。
func (c *OffsetCommitScanner) Commit() error {
	lastSegEndOffset := c.pendingOffset - c.lastScannedBytes
	fmt.Println("xxxx", c.pendingOffset, c.lastScannedBytes, lastSegEndOffset, c.lastCommitted)

	if lastSegEndOffset == c.lastCommitted {
		return nil // 无需重复写入
	}

	if err := c.writeReg(lastSegEndOffset); err != nil {
		return err
	}

	c.lastCommitted = lastSegEndOffset
	return nil
}

// CommitOffset 将指定的 offset 写入 reg 文件
func (c *OffsetCommitScanner) CommitOffset(offset int64) error {
	if offset == c.lastCommitted {
		return nil // 无需重复写入
	}

	if err := c.writeReg(offset); err != nil {
		return err
	}

	c.lastCommitted = offset
	return nil
}

// writeReg 将 offset 和 inode 写入 reg 文件
// 格式: "offset,inode"
func (c *OffsetCommitScanner) writeReg(offset int64) error {
	_, err := c.rf.Seek(0, 0)
	if err != nil {
		return err
	}

	err = c.rf.Truncate(0)
	if err != nil {
		return err
	}

	_, err = c.rf.WriteString(fmt.Sprintf("%d,%d", offset, c.inode))
	return err
}

// Err 返回扫描过程中遇到的第一个非 EOF 错误
func (c *OffsetCommitScanner) Err() error {
	return c.err
}

// Close 关闭底层文件句柄
func (c *OffsetCommitScanner) Close() error {
	var firstErr error
	if c.rotatedFile != nil {
		if err := c.rotatedFile.Close(); err != nil {
			firstErr = err
		}
	}
	if c.f != nil {
		if err := c.f.Close(); err != nil && firstErr == nil {
			firstErr = err
		}
	}
	if c.rf != nil {
		if err := c.rf.Close(); err != nil && firstErr == nil {
			firstErr = err
		}
	}
	return firstErr
}

// PendingOffset 返回当前已读取但尚未提交的 offset（供调试/测试使用）
func (c *OffsetCommitScanner) PendingOffset() int64 {
	return c.pendingOffset
}

// LastCommitted 返回上次已提交的 offset（供调试/测试使用）
func (c *OffsetCommitScanner) LastCommitted() int64 {
	return c.lastCommitted
}

// Inode 返回当前文件的 inode（供调试/测试使用）
func (c *OffsetCommitScanner) Inode() uint64 {
	return c.inode
}

// regData reg 文件中保存的数据
type regData struct {
	offset int64
	inode  uint64
}

// parseRegContent 解析 reg 文件内容
// 兼容旧格式（纯 offset）和新格式（offset,inode）
func parseRegContent(content string) (regData, error) {
	content = strings.TrimSpace(content)
	if content == "" {
		return regData{offset: -1}, nil
	}

	parts := strings.SplitN(content, ",", 2)

	offset, err := strconv.ParseInt(parts[0], 10, 64)
	if err != nil {
		return regData{}, fmt.Errorf("parse offset: %w", err)
	}

	var inode uint64
	if len(parts) == 2 {
		inode, err = strconv.ParseUint(parts[1], 10, 64)
		if err != nil {
			return regData{}, fmt.Errorf("parse inode: %w", err)
		}
	}

	return regData{offset: offset, inode: inode}, nil
}

// NewOffsetCommitScanner 创建一个支持延迟提交 offset 的扫描器。
// 参数与 NewOffsetScanner 相同：filePath 是要读取的文件，regPath 是 offset 注册文件。
// 行为差异：Scan() 不会自动推进 reg 文件，需要显式调用 Commit() 来推进。
//
// 轮转检测逻辑：
//   - inode 变化 → 文件被 rotate，从头开始读
//   - inode 相同但文件大小 < offset → 文件被 truncate，从头开始读
//   - reg 文件不存在（冷启动）→ 从文件末尾开始（避免首次导入大量历史数据）
func NewOffsetCommitScanner(filePath string, regPath string) (scanner *OffsetCommitScanner, err error) {
	var rf *os.File
	defer func() {
		if err != nil {
			if rf != nil {
				_ = rf.Close()
			}
		}
	}()

	// 获取源文件信息
	fst, err := os.Stat(filePath)
	if err != nil {
		return nil, err
	}
	fileSize := fst.Size()

	// 获取当前文件的 inode
	currentInode, ok := getInode(fst)
	if !ok {
		return nil, fmt.Errorf("cannot get inode for file: %s", filePath)
	}

	// 读取 reg 文件
	var lastReg regData

	_, err = os.Stat(regPath)
	if err == nil {
		rf, err = os.OpenFile(regPath, os.O_RDWR, 0755)
		if err != nil {
			return nil, err
		}
		content, err := io.ReadAll(rf)
		if err != nil {
			return nil, err
		}
		lastReg, err = parseRegContent(string(content))
		if err != nil {
			return nil, err
		}
	} else if os.IsNotExist(err) {
		rf, err = os.OpenFile(regPath, os.O_RDWR|os.O_CREATE, 0755)
		if err != nil {
			return nil, err
		}
		lastReg = regData{offset: -1}
	} else {
		return nil, err
	}

	// 决定起始读取位置，以及是否需要链式读取旧文件
	var startOffset int64
	var rotatedFile *os.File
	var rotatedReader *bufio.Reader
	var readingRotated bool

	switch {
	case lastReg.offset < 0:
		// 冷启动：从文件末尾开始
		startOffset = fileSize
	case lastReg.inode != 0 && lastReg.inode != currentInode:
		// inode 不匹配，文件已被轮转替换
		// 尝试找到旧文件，先读完旧文件剩余数据
		rotatedPath := findRotatedFile(filePath, lastReg.inode)
		if rotatedPath != "" {
			rotatedFile, err = os.OpenFile(rotatedPath, os.O_RDONLY, 0)
			if err == nil {
				_, err = rotatedFile.Seek(lastReg.offset, 0)
				if err != nil {
					_ = rotatedFile.Close()
					rotatedFile = nil
				} else {
					rotatedReader = bufio.NewReaderSize(rotatedFile, defaultBufSize)
					readingRotated = true
				}
			} else {
				rotatedFile = nil
				err = nil // 找不到旧文件不算致命错误，继续从新文件头开始
			}
		}
		startOffset = 0
	case fileSize < lastReg.offset:
		// 文件被 truncate 过（大小变小），从头开始
		startOffset = 0
	default:
		// 正常续接
		startOffset = lastReg.offset
	}

	// 写入初始 reg 状态
	_, err = rf.Seek(0, 0)
	if err != nil {
		return nil, err
	}
	err = rf.Truncate(0)
	if err != nil {
		return nil, err
	}
	// 如果正在读旧文件，reg 先记录旧文件的 offset 和旧 inode
	if readingRotated {
		_, err = rf.WriteString(fmt.Sprintf("%d,%d", lastReg.offset, lastReg.inode))
	} else {
		_, err = rf.WriteString(fmt.Sprintf("%d,%d", startOffset, currentInode))
	}
	if err != nil {
		return nil, err
	}

	// 打开新文件并 Seek 到指定位置
	f, err := os.OpenFile(filePath, os.O_RDONLY, 0)
	if err != nil {
		return nil, err
	}

	_, err = f.Seek(startOffset, 0)
	if err != nil {
		_ = f.Close()
		return nil, err
	}

	reader := bufio.NewReaderSize(f, defaultBufSize)

	// 确定初始 pendingOffset 和 lastCommitted
	initialOffset := startOffset
	if readingRotated {
		// 链式读取模式：pendingOffset 从旧文件的 offset 开始
		initialOffset = lastReg.offset
	}

	return &OffsetCommitScanner{
		filePath:       filePath,
		regPath:        regPath,
		f:              f,
		rf:             rf,
		reader:         reader,
		inode:          currentInode,
		pendingOffset:  initialOffset,
		lastCommitted:  initialOffset,
		rotatedFile:    rotatedFile,
		rotatedReader:  rotatedReader,
		readingRotated: readingRotated,
	}, nil
}

// findRotatedFile 在常见的 rotate 路径中查找匹配指定 inode 的文件。
// 搜索策略：
//  1. 检查 filePath.1, filePath.0 等常见 logrotate 命名
//  2. 遍历同目录下的文件，匹配 inode
func findRotatedFile(filePath string, targetInode uint64) string {
	// 常见的 rotate 文件名后缀
	candidates := []string{
		filePath + ".1",
		filePath + ".0",
		filePath + "-old",
	}

	for _, p := range candidates {
		fi, err := os.Stat(p)
		if err != nil {
			continue
		}
		if ino, ok := getInode(fi); ok && ino == targetInode {
			return p
		}
	}

	// 遍历同目录下的文件，查找匹配 inode 的文件
	dir := filepath.Dir(filePath)
	baseName := filepath.Base(filePath)
	entries, err := os.ReadDir(dir)
	if err != nil {
		return ""
	}

	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		name := entry.Name()
		// 跳过当前文件本身
		if name == baseName {
			continue
		}
		// 只检查以 baseName 为前缀的文件（如 slow.log.1, slow.log.2 等）
		if !strings.HasPrefix(name, baseName) {
			continue
		}
		fullPath := filepath.Join(dir, name)
		fi, err := os.Stat(fullPath)
		if err != nil {
			continue
		}
		if ino, ok := getInode(fi); ok && ino == targetInode {
			return fullPath
		}
	}

	return ""
}
