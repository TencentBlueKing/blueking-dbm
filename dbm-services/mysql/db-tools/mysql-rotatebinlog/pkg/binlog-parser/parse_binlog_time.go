package binlog_parser

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"

	"github.com/go-mysql-org/go-mysql/replication"
	"github.com/pkg/errors"
)

// BinlogTimeComp TODO
type BinlogTimeComp struct {
	Params BinlogTimeParam `json:"extend"`
}

// Example TODO
func (t *BinlogTimeComp) Example() interface{} {
	return &BinlogTimeComp{
		Params: BinlogTimeParam{
			BinlogDir:   "/data/dbbak",
			BinlogFiles: []string{"binlog20000.00001", "binlog20000.00002"},
			OutFormat:   "json",
			TimeLayout:  time.RFC3339,
		},
	}
}

// BinlogTimeParam TODO
type BinlogTimeParam struct {
	BinlogDir   string   `json:"binlog_dir" validate:"required"`
	BinlogFiles []string `json:"binlog_files" validate:"required"`
	OutFormat   string   `json:"format" enums:",json,dump"`
	TimeLayout  string   `json:"time_layout"`
	parser      *BinlogParse
}

// Init TODO
func (t *BinlogTimeComp) Init() error {
	bp, err := NewBinlogParse("mysql", 0, t.Params.TimeLayout)
	if err != nil {
		return err
	}
	t.Params.parser = bp
	return nil
}

// Start TODO
func (t *BinlogTimeComp) Start() error {
	for _, f := range t.Params.BinlogFiles {
		filename := filepath.Join(t.Params.BinlogDir, f)
		if err := cmutil.FileExistsErr(filename); err != nil {
			fmt.Printf("%s: %v\n", filename, err)
			continue
		}
		if events, err := t.Params.parser.GetTime(filename, true, true); err != nil {
			fmt.Printf("%s: %v\n", filename, err)
		} else {
			b, _ := json.Marshal(events)
			fmt.Printf("%s: %s\n", filename, b)
		}
	}
	return nil
}

const (
	// MaxFirstBufSize FormatDescriptionEvent 最大长度
	MaxFirstBufSize = 150
	// MaxLastBufSize 我们认为的 RotateEvent 最大长度
	MaxLastBufSize = 100
	// RotateEventPosLen 下一个 binlog 时间开始位置，8 bytes, 现在固定是 4
	RotateEventPosLen = 8
	// MaxTimestamp 我们认为的最大合法的 timestamp 值
	MaxTimestamp = 2177424000
)

// BinlogParse 解析选项
type BinlogParse struct {
	// binlog full filename with path
	FileName string `json:"file_name"`
	// 第一个 event FormatDescriptionEvent 的大小
	FirstBufSize int `json:"first_buf_size"`
	// 取最后的多少个字节来获取 RotateEvent，最大取 100
	LastBufSize int `json:"last_buf_size"`
	// 输出格式，json 或者 其它
	Output string `json:"output" enums:",json,dump"`
	// 输出的日期格式
	TimeLayout string `json:"time_layout"`
	// mysql or mariadb
	Flavor string `json:"flavor" enums:"mysql,mariadb"`

	parser *replication.BinlogParser
	// 第一个 event 开始位置，4。前 4 个字节是 [0xfe 0x62 0x69 0x6e]
	firstEventPos int64
	// event header 固定大小 19
	eventHeaderLen int
}

// NewBinlogParse godoc
// lastBufSize 默认会根据当前 binlog filename 来算，见 GetRotateEvent
func NewBinlogParse(flavor string, lastBufSize int, timeFormat string) (*BinlogParse, error) {
	bp := BinlogParse{
		Flavor:      flavor,
		LastBufSize: lastBufSize,
		TimeLayout:  timeFormat,
	}
	if err := bp.init(); err != nil {
		return nil, err
	}
	return &bp, nil
}

func (b *BinlogParse) init() error {
	b.eventHeaderLen = replication.EventHeaderSize
	b.firstEventPos = int64(len(replication.BinLogFileHeader)) // int64(4) // fe 62 69 6e
	b.FirstBufSize = MaxFirstBufSize
	/*
		if b.LastBufSize == 0 {
			b.LastBufSize = 49 // 这里默认第一次取 49
		}
	*/
	b.parser = replication.NewBinlogParser()
	if b.Flavor == "" {
		b.parser.SetFlavor("mysql")
	}
	if b.TimeLayout == "" {
		b.TimeLayout = "2006-01-02 15:04:05"
	}
	if b.Output == "" {
		b.Output = "json"
	}
	return nil
}

// GetTime 获取binlog 开始或结束时间
// 即使获取 rotate event 失败，也把已经成功的返回
func (b *BinlogParse) GetTime(fileName string, start, stop bool) ([]BinlogEventHeaderWrapper, error) {
	b.FileName = fileName
	if err := cmutil.FileExistsErr(b.FileName); err != nil {
		return nil, err
	}
	f, err := os.Open(b.FileName)
	if err != nil {
		return nil, errors.Wrap(err, "get time from binlog")
	}
	defer f.Close()

	var events []*replication.EventHeader
	var evhWrappers []BinlogEventHeaderWrapper
	if start {
		if evh, err := b.GetFormatDescriptionEvent(f); err != nil {
			return nil, err
		} else {
			events = append(events, evh)
			evhWrappers = append(evhWrappers, b.NewBinlogEventHeaderWrapper(evh))
		}
	}
	if stop {
		evh, err := b.GetRotateEvent(f)
		if err != nil {
			b.LastBufSize = MaxLastBufSize
			if evh, err = b.GetRotateEvent(f); err != nil {
				return evhWrappers, err
			}
		}
		events = append(events, evh)
		evhWrappers = append(evhWrappers, b.NewBinlogEventHeaderWrapper(evh))
	}
	return evhWrappers, nil
}

// BinlogEventHeaderWrapper 输出结果的格式
type BinlogEventHeaderWrapper struct {
	// replication.BinlogEvent
	evHeader  replication.EventHeader
	EventType string `json:"event_type"`
	// EventTime 已经转换成指定 time_layout 格式
	EventTime string `json:"event_time"`
	Timestamp uint32 `json:"timestamp"`
	ServerID  uint32 `json:"server_id"`
	EventSize uint32 `json:"event_size"`
}

// NewBinlogEventHeaderWrapper 封装EventHeader用于输出
func (b *BinlogParse) NewBinlogEventHeaderWrapper(evh *replication.EventHeader) BinlogEventHeaderWrapper {
	w := BinlogEventHeaderWrapper{
		evHeader:  *evh,
		EventType: replication.EventType(evh.EventType).String(),
		EventTime: time.Unix(int64(evh.Timestamp), 0).Format(b.TimeLayout),
		Timestamp: evh.Timestamp,
		ServerID:  evh.ServerID,
		EventSize: evh.EventSize,
	}
	// evh.Dump(os.Stdout)
	return w
}

// GetFormatDescriptionEvent 获取 header
func (b *BinlogParse) GetFormatDescriptionEvent(f *os.File) (*replication.EventHeader, error) {
	_, err := f.Seek(b.firstEventPos, io.SeekStart)
	desc := make([]byte, b.FirstBufSize)
	if _, err = f.ReadAt(desc, b.firstEventPos); err != nil {
		return nil, errors.Wrap(err, b.FileName)
	}
	r := bytes.NewReader(desc)
	evHeader := &replication.EventHeader{}
	if err := evHeader.Decode(desc); err != nil {
		return nil, errors.Wrap(err, b.FileName)
	}

	_, err = b.parser.ParseSingleEvent(
		r, func(e *replication.BinlogEvent) error {
			if e.Header.EventType == replication.FORMAT_DESCRIPTION_EVENT {
				// evHeader = e.Header
				return nil
			} else {
				return errors.Errorf("%s: failed to find FormatDescriptionEvent at pos 4", b.FileName)
			}
		},
	)
	if err != nil {
		return nil, errors.Wrap(err, b.FileName)
	}
	return evHeader, nil
}

// GetRotateEvent 获取 rotate event header
func (b *BinlogParse) GetRotateEvent(f *os.File) (*replication.EventHeader, error) {
	// RotateEvent event size: 19(header size) + 8(pos length) + name_len + 4
	// 暂且估计下一个 binlog filename 长度与当前分析的相同(且是ascii字符，即一个字符占一个字节)，所以避免手动 rename 文件名
	filename := path.Base(b.FileName)
	rotateEventSize := b.eventHeaderLen + RotateEventPosLen + len(filename) + len(replication.BinLogFileHeader)
	if b.LastBufSize < rotateEventSize && rotateEventSize <= MaxLastBufSize {
		b.LastBufSize = rotateEventSize
	}
	// https://dev.mysql.com/doc/dev/mysql-server/latest/page_protocol_replication_binlog_event.html#sect_protocol_replication_event_rotate
	bufSize := b.LastBufSize // 取最后的多少个字节
	buf := make([]byte, bufSize)
	_, err := f.Seek(-int64(bufSize), io.SeekEnd)
	if _, err = f.Read(buf); err != nil {
		return nil, errors.Wrap(err, b.FileName)
	}
	minBegin := b.eventHeaderLen // StopEvent 最小长度
	stopWhere := bufSize - minBegin

	evHeader := &replication.EventHeader{}
	for i := 0; i <= stopWhere; i++ { // i is startPos
		endPos := i + b.eventHeaderLen
		if err := evHeader.Decode(buf[i:endPos]); err != nil {
			if evHeader.EventSize < uint32(b.eventHeaderLen) || strings.Contains(err.Error(), "invalid event size") {
				// 解析到非法的 event，移动到下一个字节开始
				continue
			} else {
				return nil, errors.Wrap(err, b.FileName)
			}
		}
		if evHeader.EventType == replication.UNKNOWN_EVENT { // 非法 event
			continue
		} else if evHeader.EventType == replication.ROTATE_EVENT {
			if evHeader.EventSize > MaxLastBufSize { // not RotateEvent
				continue
			} else if evHeader.Timestamp > MaxTimestamp { // invalid timestamp
				continue
			}
			r := bytes.NewReader(buf[i:])
			_, err = b.parser.ParseSingleEvent(
				r, func(e *replication.BinlogEvent) error {
					// valid event
					return nil
				},
			)
			if err != nil {
				return nil, errors.Wrap(err, b.FileName)
			}
			return evHeader, nil
		} else if evHeader.EventType == replication.STOP_EVENT {
			// stopEventLen := []int{19, 23}  // StopEvent 有 19,23 两种长度，见 replication.parser_test.go
			if evHeader.EventSize <= 23 && evHeader.Timestamp < MaxTimestamp {
				// 认为是合法的 StopEvent
				return evHeader, nil
			}
		}
	}
	// if mysqld is shutdown with kill -9, binlog maynot contains rotate/stop event
	return nil, errors.Errorf("%s: get RotateEvent or StopEvent failed", b.FileName)
}
