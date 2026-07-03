package saveproxyconnlog

import (
	"bufio"
	"log/slog"
	"os"
	"syscall"
)

// scanConnLog 基于 offset 的一次性扫描 connlog 文件
// 参照 mysqlerrlog 的 offset + Seek 模式：
// 1. 加载上次保存的 offset 和 inode
// 2. 对比当前文件的 inode 和大小，决定从哪里开始读取
// 3. 逐行扫描并解析，始终读到文件末尾（推进 offset 到最新位置）
// 4. 当条目数超过 maxLines 时，只保留前 maxLines 条，多余的丢弃
// 5. maxLines=0 时不限制，全部保留
func scanConnLog(filePath string, maxLines int) (entries []*ConnLogEntry, newOffset offsetData, err error) {
	// 文件不存在时记录 Warning 并返回空
	fi, err := os.Stat(filePath)
	if err != nil {
		if os.IsNotExist(err) {
			slog.Warn("proxy connlog file not found, skip", slog.String("file", filePath))
			return nil, offsetData{}, nil
		}
		return nil, offsetData{}, err
	}

	// 获取当前文件的 inode
	stat, ok := fi.Sys().(*syscall.Stat_t)
	if !ok {
		slog.Warn("cannot get file inode, treat as new file")
		return nil, offsetData{}, nil
	}
	currentInode := stat.Ino
	currentSize := fi.Size()

	// 加载上次的 offset
	lastData := loadOffset()

	// 决定起始读取位置
	var seekOffset int64
	if lastData.Inode != uint64(currentInode) {
		// inode 不匹配，文件已被轮转替换，从头开始
		slog.Info("inode changed, file rotated, read from beginning",
			slog.Uint64("last_inode", lastData.Inode),
			slog.Uint64("current_inode", uint64(currentInode)),
		)
		seekOffset = 0
	} else if currentSize < lastData.Offset {
		// 文件被 truncate 过（大小变小），从头开始
		slog.Info("file truncated, read from beginning",
			slog.Int64("current_size", currentSize),
			slog.Int64("last_offset", lastData.Offset),
		)
		seekOffset = 0
	} else if lastData.Offset == 0 && lastData.Inode == 0 {
		// 首次运行，从文件末尾开始（避免首次导入大量历史数据）
		slog.Info("first run, start from end of file", slog.Int64("file_size", currentSize))
		seekOffset = currentSize
	} else {
		// 正常续接
		seekOffset = lastData.Offset
	}

	// 如果 seekOffset 等于当前文件大小，说明没有新数据
	if seekOffset >= currentSize {
		slog.Info("no new data in connlog", slog.Int64("offset", seekOffset), slog.Int64("size", currentSize))
		// 仍然保存 offset（更新 inode）
		newOffset = offsetData{Offset: seekOffset, Inode: uint64(currentInode)}
		return nil, newOffset, nil
	}

	// 打开文件并 Seek 到指定位置
	f, err := os.Open(filePath)
	if err != nil {
		slog.Error("open connlog file failed", slog.String("error", err.Error()))
		return nil, offsetData{}, err
	}
	defer func() {
		_ = f.Close()
	}()

	offset, err := f.Seek(seekOffset, 0)
	if err != nil {
		slog.Error("seek connlog file failed", slog.String("error", err.Error()))
		return nil, offsetData{}, err
	}

	// 逐行扫描
	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024) // 最大支持 1MB 单行

	lineCount := 0
	discarded := 0

	for scanner.Scan() {
		line := scanner.Text()
		offset += int64(len(scanner.Bytes())) + 1 // +1 for newline

		entry := parseConnLogLineV2(line)
		if entry == nil {
			continue
		}

		lineCount++
		// maxLines > 0 时只保留前 maxLines 条，多余的丢弃但继续读文件推进 offset
		if maxLines > 0 && lineCount > maxLines {
			discarded++
			continue
		}

		entries = append(entries, entry)
	}

	if err := scanner.Err(); err != nil {
		slog.Error("scan connlog file error", slog.String("error", err.Error()))
		return entries, offsetData{Offset: offset, Inode: uint64(currentInode)}, err
	}

	if discarded > 0 {
		slog.Warn("proxy connlog overload, entries discarded",
			slog.Int("max_lines", maxLines),
			slog.Int("collected", len(entries)),
			slog.Int("discarded", discarded),
			slog.Int("total_matched", lineCount),
		)
	}

	newOffset = offsetData{Offset: offset, Inode: uint64(currentInode)}
	slog.Info("scan connlog done",
		slog.Int("entries", len(entries)),
		slog.Int64("new_offset", offset),
		slog.Int("discarded", discarded),
	)

	return entries, newOffset, nil
}
