package mysql

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	binlogParser "dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/binlog-parser"
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
	parser      *binlogParser.BinlogParse
}

// Init TODO
func (t *BinlogTimeComp) Init() error {
	bp, err := binlogParser.NewBinlogParse("mysql", 0, t.Params.TimeLayout)
	if err != nil {
		return err
	}
	t.Params.parser = bp
	return nil
}

// Start TODO
func (t *BinlogTimeComp) Start() error {
	var errs []error
	for _, f := range t.Params.BinlogFiles {
		filename := filepath.Join(t.Params.BinlogDir, f)
		if err := cmutil.FileExistsErr(filename); err != nil {
			fmt.Printf("%s: %v\n", filename, err)
			continue
		}
		if events, err := t.Params.parser.GetTime(filename, true, true); err != nil {
			fmt.Fprintf(os.Stderr, "%s: %v\n", filename, err)
			errs = append(errs, err)
		} else {
			b, _ := json.Marshal(events)
			fmt.Printf("%s: %s\n", filename, b)
		}
	}
	if len(errs) > 0 {
		return errors.New("parse error")
	}
	return nil
}

func (t *BinlogTimeComp) ExampleOutput() interface{} {
	return []binlogParser.BinlogEventHeaderWrapper{
		{EventType: "FormatDescriptionEvent", EventSize: 137, EventTime: "2022-06-20 15:17:47",
			Timestamp: 1655709467, ServerID: 111},
		{EventType: "RotateEvent", EventSize: 49, EventTime: "2022-07-07 23:38:36",
			Timestamp: 1657208316, ServerID: 111},
	}
}
