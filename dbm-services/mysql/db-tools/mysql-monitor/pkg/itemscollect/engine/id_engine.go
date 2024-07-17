package engine

import (
	"fmt"
	"io/fs"
	"path/filepath"
	"slices"
	"strings"
)

type engineDetail struct {
	Engine EnumEngineType `json:"engine"`
	Tables []string       `json:"tables"`
}

type engineSummary struct {
	Engine EnumEngineType `json:"engine"`
	Count  int            `json:"count"`
}

type engineReport struct {
	Details   []*engineDetail  `json:"details"`
	Summaries []*engineSummary `json:"summaries"`
}

type EnumEngineType string

const (
	MyISAMEngine EnumEngineType = "myisam"
	InnoDBEngine EnumEngineType = "innodb"

	UnknownEngine EnumEngineType = "unknown"
)

type EnumEngineExtType string

const (
	MyISAMExt  EnumEngineExtType = ".myd"
	InnoDBExt  EnumEngineExtType = ".ibd"
	UnknownExt EnumEngineExtType = ".unknown"
)

var extEngineMap map[EnumEngineExtType]EnumEngineType

func init() {
	extEngineMap = map[EnumEngineExtType]EnumEngineType{
		MyISAMExt: MyISAMEngine,
		InnoDBExt: InnoDBEngine,
	}
}

func idEngine(filename string) (EnumEngineType, EnumEngineExtType) {
	ext := EnumEngineExtType(strings.ToLower(filepath.Ext(filename)))
	if _, ok := extEngineMap[ext]; ok {
		return extEngineMap[ext], ext
	}
	return UnknownEngine, UnknownExt
}

func (c *Checker) idEngine(dataDir string) (res *engineReport, err error) {
	res = &engineReport{}

	err = filepath.WalkDir(
		dataDir, func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				return fs.SkipDir
			}
			if d.IsDir() {
				return nil
			}

			dir := filepath.Dir(path)
			dbName := filepath.Base(dir)
			if slices.Index(systemDBs, dbName) >= 0 {
				return nil
			}

			engine, ext := idEngine(d.Name())
			if engine == UnknownEngine {
				return nil
			}

			var tableName string
			match := partitionPattern.FindStringSubmatch(d.Name())
			if match == nil {
				tableName = strings.TrimSuffix(d.Name(), string(ext))
			} else {
				tableName = match[1]
			}

			fullTableName := fmt.Sprintf("%s.%s", dbName, tableName)

			var detail *engineDetail
			dtid := slices.IndexFunc(res.Details, func(detail *engineDetail) bool {
				return detail.Engine == engine
			})

			if dtid < 0 {
				detail = &engineDetail{
					Engine: engine,
					Tables: []string{fullTableName},
				}
				res.Details = append(res.Details, detail)

				summary := &engineSummary{
					Engine: engine,
					Count:  1,
				}
				res.Summaries = append(res.Summaries, summary)
			} else {
				detail = res.Details[dtid]
				if slices.Index(detail.Tables, fullTableName) < 0 {
					detail.Tables = append(detail.Tables, fullTableName)

					var summary *engineSummary
					sid := slices.IndexFunc(res.Summaries, func(summary *engineSummary) bool {
						return summary.Engine == engine
					})

					summary = res.Summaries[sid]
					summary.Count++

				}
			}

			return nil
		})

	return res, err
}
