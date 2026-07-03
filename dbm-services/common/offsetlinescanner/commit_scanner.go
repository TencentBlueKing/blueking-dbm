package offsetlinescanner

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
	"syscall"
)

// OffsetCommitScanner 支持延迟提交 offset 的扫描器。
// 与 OffsetScanner 不同，它不会在每次 Scan() 时自动推进 offset reg 文件，
// 而是仅在显式调用 Commit() 时才将当前读取位置写入 reg 文件。
// 这样可以保证：只有完整处理成功的数据才推进 offset，避免半段数据丢失。
//
// reg 文件格式: "offset,inode"
// 通过 inode 对比可以精确检测文件轮转（logrotate），避免仅靠文件大小判断的漏洞。
type OffsetCommitScanner struct {
	filePath         string
	regPath          string
	f                *os.File
	rf               *os.File
	err              error
	inode            uint64 // 当前文件的 inode
	pendingOffset    int64  // 当前已读取到的位置（尚未提交）
	lastCommitted    int64  // 上次已提交的 offset
	lastScannedBytes int64  // 上一次 scan 读取的字节数，用于根据下一次 scan 分段
	*bufio.Scanner
}

// getInode 获取文件的 inode 号
func getInode(fi os.FileInfo) (uint64, bool) {
	stat, ok := fi.Sys().(*syscall.Stat_t)
	if !ok {
		return 0, false
	}
	return stat.Ino, true
}

// Scan 读取下一行，更新 pendingOffset 但不写入 reg 文件
func (c *OffsetCommitScanner) Scan() bool {
	rt := c.Scanner.Scan()
	if rt {
		offset, err := c.f.Seek(0, io.SeekCurrent)
		if err != nil {
			c.err = err
			return false
		}
		// 本次扫描在文件中实际消耗的字节数（含换行符）
		c.lastScannedBytes = offset - c.pendingOffset
		c.pendingOffset = offset
	}
	return rt
}

// Commit 将当前 pendingOffset 写入 reg 文件，推进 offset。
// 应在完整段处理成功后调用。
func (c *OffsetCommitScanner) Commit() error {
	lastSegEndOffset := c.pendingOffset - c.lastScannedBytes

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
	if c.Scanner.Err() != nil {
		return c.Scanner.Err()
	}
	return c.err
}

// Close 关闭底层文件句柄
func (c *OffsetCommitScanner) Close() error {
	var firstErr error
	if c.f != nil {
		if err := c.f.Close(); err != nil {
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

	// 决定起始读取位置
	var startOffset int64
	switch {
	case lastReg.offset < 0:
		// 冷启动：从文件末尾开始
		startOffset = fileSize
	case lastReg.inode != 0 && lastReg.inode != currentInode:
		// inode 不匹配，文件已被轮转替换，从头开始
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
	_, err = rf.WriteString(fmt.Sprintf("%d,%d", startOffset, currentInode))
	if err != nil {
		return nil, err
	}

	// 打开文件并 Seek 到指定位置
	f, err := os.OpenFile(filePath, os.O_RDONLY, 0)
	if err != nil {
		return nil, err
	}

	_, err = f.Seek(startOffset, 0)
	if err != nil {
		_ = f.Close()
		return nil, err
	}

	sc := bufio.NewScanner(f)
	sc.Split(bufio.ScanLines)
	return &OffsetCommitScanner{
		filePath:      filePath,
		regPath:       regPath,
		f:             f,
		rf:            rf,
		inode:         currentInode,
		pendingOffset: startOffset,
		lastCommitted: startOffset,
		Scanner:       sc,
	}, nil
}
