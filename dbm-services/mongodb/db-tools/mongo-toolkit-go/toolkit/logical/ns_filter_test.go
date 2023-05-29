package logical

import (
	"reflect"
	"testing"
)

func TestNewNsFilter(t *testing.T) {

	input := []struct {
		dbColList   []DbCollection
		WhiteDbList []string
		BlackDbList []string
		WhiteTbList []string
		BlackTbList []string
		retColList  []DbCollection
	}{
		{
			dbColList: []DbCollection{
				{
					Db:  "db1",
					Col: []string{"col1", "col2"},
				},
				{
					Db:  "db2",
					Col: []string{"col1", "col2"},
				},
				{
					Db:  "xdb1",
					Col: []string{"col1", "col2"},
				},
			},
			WhiteDbList: []string{"db1"},
			BlackDbList: []string{"db2"},
			WhiteTbList: []string{"col1"},
			BlackTbList: []string{"col2"},
			retColList: []DbCollection{
				{
					Db:  "db1",
					Col: []string{"col1"},
				},
			},
		},
		{
			dbColList: []DbCollection{
				{
					Db:  "db1",
					Col: []string{"col1", "col2"},
				},
				{
					Db:  "db2",
					Col: []string{"col1", "col2"},
				},
			},
			WhiteDbList: []string{"*"},
			BlackDbList: []string{},
			WhiteTbList: []string{},
			BlackTbList: []string{},
			retColList: []DbCollection{
				{
					Db:  "db1",
					Col: []string{"col1", "col2"},
				},
				{
					Db:  "db2",
					Col: []string{"col1", "col2"},
				},
			},
		},
		{
			dbColList: []DbCollection{
				{
					Db:  "db1",
					Col: []string{"col1", "col2"},
				},
				{
					Db:  "db2",
					Col: []string{"col1", "col2"},
				},
			},
			WhiteDbList: []string{"db1"},
			BlackDbList: nil,
			WhiteTbList: nil,
			BlackTbList: nil,
			retColList: []DbCollection{
				{
					Db:  "db1",
					Col: []string{"col1", "col2"},
				},
			},
		},
		{
			dbColList: []DbCollection{
				{
					Db:  "db1",
					Col: []string{"tb_aa1", "tb_aa2"},
				},
				{
					Db:  "db2",
					Col: []string{"tb_aa1", "tb_aa2"},
				},
				{
					Db:  "db22",
					Col: []string{"tb_aa1", "tb_aa2"},
				},
			},
			WhiteDbList: []string{"db1", "db2"},
			BlackDbList: []string{"db2*"},
			WhiteTbList: []string{"tb_aa*"},
			BlackTbList: []string{"tb_aa_1"},
			retColList: []DbCollection{
				{
					Db:  "db1",
					Col: []string{"tb_aa1", "tb_aa2"},
				},
			},
		},
	}

	for i, item := range input {
		filter := NewNsFilter(item.WhiteDbList, item.BlackDbList, item.WhiteTbList, item.BlackTbList)
		var retRows []DbCollection
		for _, dbCol := range item.dbColList {
			var retRow DbCollection
			retRow.Db = dbCol.Db

			if !filter.IsDbMatched(dbCol.Db) {
				continue
			}
			retRow.Col, _ = filter.FilterTb(dbCol.Col)
			retRows = append(retRows, retRow)
		}
		v := reflect.DeepEqual(retRows, item.retColList)
		if !v {
			t.Errorf("error case %d, want:%v, got:%v", i, item.retColList, retRows)
		} else {
			t.Logf("case %d, want:%v, got:%v", i, item.retColList, retRows)
		}
	}

}
