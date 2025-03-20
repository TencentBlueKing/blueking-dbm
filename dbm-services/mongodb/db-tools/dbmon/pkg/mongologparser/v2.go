package mongologparser

import (
	"bytes"
	"fmt"
	"strings"
	"time"

	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/bson/primitive"
)

// ParseV2Log parses a log line and returns a MongoLogMsg for mongodb version 3.0 - 4.2
func ParseV2Log(line []byte) (*MongoLogMsg, error) {
	// 读前面4个word.
	segs, pos, err := getWords(line, 4)
	var msg MongoLogMsg
	for i := 0; i < 4; i++ {
		if segs[i][0] == 0 && segs[i][1] == 0 {
			msg.Msg = fmt.Sprintf("parse error: %s", string(line))
			return &msg, errors.New("parse error")
		}
	}
	msg.OriginLine = line
	var dt time.Time
	dt, err = time.Parse(timeStr, string(line[segs[0][0]:segs[0][1]]))
	if err != nil {
		return &msg, errors.New("parse time error")
	}
	msg.DateTime = primitive.NewDateTimeFromTime(dt)
	msg.S = string(line[segs[1][0]:segs[1][1]])
	msg.C = string(line[segs[2][0]:segs[2][1]])
	msg.Id = 0

	//  remove [ and ]
	if segs[3][1]-segs[3][0] > 2 && line[segs[3][0]] == '[' && line[segs[3][1]-1] == ']' {
		msg.Ctx = string(line[segs[3][0]+1 : segs[3][1]-1])
	} else {
		msg.Ctx = string(line[segs[3][0]:segs[3][1]])
	}

	msg.Msg = string(line[pos:])
	msg.ParseOk = 0
	msg.ParseMore()
	return &msg, nil
}

// ParseMore 进一步解析消息内容
// 1. slowlog ms
func (m *MongoLogMsg) ParseMore() (err error) {
	// {"t":{"$date":"2024-03-26T15:42:28.802+08:00"},"s":"I", "c":"NETWORK", "id":22943,
	//"ctx":"listener","msg":"Connection accepted",
	switch m.C {
	case "NETWORK":
		if len(m.Ctx) > 0 && m.Ctx != "conn" {
			// connection accepted from 1.1.1.1:50908 #5343139 (5 connections now open)
			// 不转换.
		}
		m.ParseOk = 1
	case "COMMAND", "QUERY", "WRITE", "TXN", "slowquery":
		var attr *SlowlogAttr
		if !bytes.HasSuffix(m.OriginLine, []byte("ms")) {
			attr, err = m.ParseDropCmd()
		} else {
			attr, err = m.ParseSlowlog()
		}

		if attr != nil {
			m.ParseOk = 1
			m.Attr = attr
			m.Id = LogTypeSlowlog
		} else {
			m.ParseOk = 0
			m.Attr = &SlowlogAttr{
				Type: m.C,
			}
			err = errors.New("parse error")
			// log.Warnf("parse error: %v", err)
		}
	case "CONTROL", "ACCESS":
		m.ParseOk = 1
	default:

	}
	return
}

// ParseDropCmd parse drop cmd
func (m *MongoLogMsg) ParseDropCmd() (*SlowlogAttr, error) {
	wordPos := decodeSlowLogLine(m.OriginLine)
	if len(wordPos) < 2 {
		return nil, errors.New("decodeSlowLogLine failed")
	}
	cmd := getField(m.OriginLine, wordPos[1])
	if cmd == "CMD: drop" {
		var attr SlowlogAttr
		attr.SetProp("type", "drop")
		attr.SetProp("ns", getField(m.OriginLine, wordPos[0]))
		return &attr, nil
	} else if cmd == "CMD: dropIndexes" {
		var attr SlowlogAttr
		attr.SetProp("type", "dropIndexes")
		return &attr, nil
	} else if strings.HasPrefix(cmd, "CMD:") {
		cmdName := strings.TrimPrefix(cmd, "CMD:")
		var attr SlowlogAttr
		attr.SetProp("type", strings.TrimSpace(cmdName))
		return &attr, nil
	} else {
		var attr SlowlogAttr
		attr.SetProp("type", "COMMAND")
		return &attr, nil
	}

	return nil, errors.New("unknown format ")
}

// ParseSlowlog parse slowlog
func (m *MongoLogMsg) ParseSlowlog() (*SlowlogAttr, error) {
	// wordPos 是倒序的单词pos列表
	wordPos := decodeSlowLogLine(m.OriginLine)
	if len(wordPos) < 2 {
		return nil, errors.New("decodeSlowLogLine failed")
	}
	var attr SlowlogAttr
	attr.SetProp("durationMillis", getField(m.OriginLine, wordPos[0]))
	for i := 1; i < len(wordPos); i++ {
		word := m.OriginLine[wordPos[i][0]:wordPos[i][1]]
		if keyEnd := bytes.IndexByte(word, ':'); keyEnd > 0 {
			key := string(word[:keyEnd])
			attr.SetProp(key, string(word[keyEnd+1:]))
		} else {
			// 不是 kk:vv ，跳过
		}
	}

	size := len(wordPos)
	idx := 5
	command := getField(m.OriginLine, wordPos[size-idx])
	// v24日志，从第6个字段开始
	if strings.HasPrefix(command, "[") {
		idx = 6
		command = getField(m.OriginLine, wordPos[size-idx])
	}
	//  "warning: log line attempted (133k) over max size (10k), printing beginning and end ... command 跳过...前的内容
	if strings.HasPrefix(command, "warning:") {
		for i := idx; i < len(wordPos); i++ {
			v := getField(m.OriginLine, wordPos[size-i])
			if v == "..." {
				idx = i + 1
				break
			}
		}
	}

	// 没有找到command的位置
	if idx > size-5 {
		return &attr, nil
	}

	command = getField(m.OriginLine, wordPos[size-idx])
	attr.SetProp("type", command)
	idx++
	attr.SetProp("ns", getField(m.OriginLine, wordPos[size-idx]))
	return &attr, nil
}

// decodeSlowLogLine 将日志分散成单词
func decodeSlowLogLine(line []byte) [][2]int {
	pos := len(line) - 1
	last := pos + 1
	wordPos := make([][2]int, 0)
	depth := 0
	for ; pos >= 0; pos-- {
		switch line[pos] {
		case ' ':
			if depth == 0 {
				if pos > 0 && line[pos-1] == ':' {
					continue
				}
				// 跳过空格
				size := last - pos
				if size > 1 || line[pos+1] != ' ' {
					wordPos = append(wordPos, [2]int{pos + 1, last})
				}
				last = pos
			}
		case '}':
			depth++
		case '{':
			depth--
		}
	}
	wordPos = append(wordPos, [2]int{pos + 1, last})
	return wordPos
}
func getWords(line []byte, n int) (segs [][2]int, pos int, err error) {
	segs = make([][2]int, n)
	var segi = 0
	var prevSpace = false
	var startIndex = 0
	for pos = 0; pos < len(line); {
		isSpace := line[pos] == ' ' || line[pos] == '\t'
		if isSpace {
			if !prevSpace {
				segs[segi][0], segs[segi][1] = startIndex, pos
				segi++
			}
		} else {
			if prevSpace {
				startIndex = pos
			}
		}
		pos++
		prevSpace = isSpace
		if segi == n {
			break
		}
	}

	for i := 0; i < n; i++ {
		if segs[i][0] == 0 && segs[i][1] == 0 {
			err = errors.New("parse error")
			break
		}
	}
	return
}
