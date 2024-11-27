package mongologparser

import (
	"bytes"
	"fmt"
	"time"

	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/bson/primitive"
)

// ParseV1Log parses a log line and returns a MongoLogMsg for mongodb version 2.4
// example: Fri Apr 19 18:48:43.491 [initandlisten] ...
//
//	 layout := "Mon Jan 2 15:04:05.000"
//		str := "Fri Apr 19 18:48:43.491"
//		t, err := time.Parse(layout, str)
func ParseV1Log(line []byte) (*MongoLogMsg, error) {
	segs, pos, err := getWords(line, 5)
	var msg MongoLogMsg
	if err != nil {
		msg.Msg = fmt.Sprintf("parse error: %s", string(line))
		return &msg, errors.New("parse error")
	}
	msg.OriginLine = line
	dt, err := parseTimeV24(string(line[segs[0][0]:segs[3][1]]))
	if err != nil {
		return nil, errors.Wrap(err, "parse time error")
	}
	msg.T.DateTime = primitive.NewDateTimeFromTime(dt)
	msg.S = "I"
	msg.Id = 0
	msg.Ctx = getField(line, segs[4])
	msg.C = "NETWORK"
	if bytes.HasSuffix(line, []byte("ms")) {
		msg.Id = LogTypeSlowlog
		msg.C = "slowquery"
	}
	msg.Id = 0
	msg.Msg = string(line[pos:])
	msg.ParseMore()
	msg.OriginLine = nil
	return &msg, nil
}

// parseTimeV24  parse time string for mongodb 2.4
func parseTimeV24(str string) (t time.Time, err error) {
	var now = time.Now()
	t, err = time.Parse(timeStrV24, str)
	if err != nil {
		t = now
		return
	}
	if t.Year() == 0 {
		t = t.AddDate(now.Year(), 0, 0)
	}
	// 如果当前是1月份，且t是12月份 ，则t要修正上1年
	if now.Month() == 1 && t.Month() == 12 {
		t = t.AddDate(-1, 0, 0)
	} else if now.Month() == 12 && t.Month() == 1 {
		t = t.AddDate(1, 0, 0)
	}
	return
}
