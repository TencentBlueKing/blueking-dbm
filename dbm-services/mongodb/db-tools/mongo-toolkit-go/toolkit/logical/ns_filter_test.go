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

func TestNewNsFilterForBackup(t *testing.T) {

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
					Db:  "testdb1",
					Col: []string{"col1", "col2"},
				},
				{
					Db:  "testdb2",
					Col: []string{"col1", "col2"},
				},
				{
					Db:  "notestdb",
					Col: []string{"col1", "col2"},
				},
			},
			WhiteDbList: []string{"test*"},
			BlackDbList: []string{""},
			WhiteTbList: []string{"col1"},
			BlackTbList: []string{""},
			retColList: []DbCollection{
				{
					Db:  "testdb1",
					Col: []string{"col1"},
				},
				{
					Db:  "testdb2",
					Col: []string{"col1"},
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

	for i, item := range input {
		filter := NewNsFilter(item.WhiteDbList, item.BlackDbList, item.WhiteTbList, item.BlackTbList)
		var retRows []DbCollection
		for _, dbCol := range item.dbColList {
			var retRow DbCollection
			retRow.Db = dbCol.Db
			retRow.Col, _ = filter.FilterTbV2(dbCol.Db, dbCol.Col)
			if len(retRow.Col) == 0 {
				continue
			}
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

func TestNewNsFilterForCleanDB(t *testing.T) {

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
					Db:  "testdb1",
					Col: []string{"col1", "col2"},
				},
				{
					Db:  "testdb2",
					Col: []string{"col1", "col2"},
				},
				{
					Db:  "notestdb",
					Col: []string{"col1", "col2"},
				},
			},
			WhiteDbList: []string{"*"},
			BlackDbList: []string{"notestdb"},
			WhiteTbList: []string{"*"},
			BlackTbList: []string{"*"},
			retColList: []DbCollection{
				{
					Db:  "testdb1",
					Col: []string{"col1", "col2"},
				},
				{
					Db:  "testdb2",
					Col: []string{"col1", "col2"},
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

			retRow.Col, _ = filter.FilterTbV2(dbCol.Db, dbCol.Col)
			if len(retRow.Col) == 0 {
				continue
			}
			retRows = append(retRows, retRow)
		}
		isEq := reflect.DeepEqual(retRows, item.retColList)
		if !isEq {
			t.Errorf("error case %d, want:%v, got:%v", i, item.retColList, retRows)
		} else {
			t.Logf("ok case %d, want:%v, got:%v", i, item.retColList, retRows)
		}
	}

}

func TestIsMatch(t *testing.T) {
	t.Logf("test isMatch")
	type inputRow struct {
		name string
		list []string
		want bool
	}
	newInputRow := func(name string, list []string, want bool) inputRow {
		return inputRow{
			name: name,
			list: list,
			want: want,
		}
	}

	input := []inputRow{
		newInputRow("abc", []string{"*"}, true),
		newInputRow("abc", []string{"abc"}, true),
		newInputRow("abc", []string{"abc*"}, true),
		newInputRow("abc", []string{"*abc"}, true),
		newInputRow("abc", []string{"*abc*"}, true),
		newInputRow("abc", []string{""}, false),
		newInputRow("abc", []string{"abc", "def"}, true),
		newInputRow("db2", []string{"db2*"}, true),
		newInputRow("db22", []string{"db2*"}, true),
	}
	for _, item := range input {
		got := isMatch(item.list, item.name, false)
		if got != item.want {
			t.Errorf("error case %s, want:%v, got:%v", item.name, item.want, got)
		} else {
			t.Logf("ok case %s, want:%v, got:%v", item.name, item.want, got)
		}
	}
}

func TestNewNsFilterInV2(t *testing.T) {

	type tmpConf struct {
		WhiteDbList []string
		WhiteTbList []string
		BlackDbList []string
		BlackTbList []string
	}

	newCollection := func(db string, cols []string) DbCollection {
		return DbCollection{
			Db:  db,
			Col: cols,
		}
	}

	input := []struct {
		name       string
		dbColList  []DbCollection
		conf       tmpConf
		retColList []DbCollection
	}{
		{
			name: "case1: match all",
			dbColList: []DbCollection{
				newCollection("db1", []string{"col1", "col2"}),
				newCollection("db2", []string{"col1", "col2"}),
				newCollection("xdb1", []string{"col1", "col2"}),
			},
			conf: tmpConf{
				WhiteDbList: []string{"*"},
				BlackDbList: []string{""},
				WhiteTbList: []string{"*"},
				BlackTbList: []string{""},
			},
			// match db1.col1 and not match db2.col2 => db1.col1
			retColList: []DbCollection{
				newCollection("db1", []string{"col1", "col2"}),
				newCollection("db2", []string{"col1", "col2"}),
				newCollection("xdb1", []string{"col1", "col2"}),
			},
		},
		{
			name: "case2: match all. 不要库名为db2.* 也不要表名为*.col2",
			dbColList: []DbCollection{
				newCollection("db1", []string{"col1", "col2"}),
				newCollection("db2", []string{"col1", "col2"}),
				newCollection("xdb1", []string{"col1", "col2"}),
			},
			conf: tmpConf{
				WhiteDbList: []string{"*"},
				BlackDbList: []string{"db2"},
				WhiteTbList: []string{"*"},
				BlackTbList: []string{"col2"},
			},
			// match all db and not match any tb => all db and all tb
			retColList: []DbCollection{
				newCollection("db1", []string{"col1"}),
				newCollection("xdb1", []string{"col1"}),
			},
		},
		{
			name: "case3: 所有库表。但不包括db2库里的所有表",
			dbColList: []DbCollection{
				newCollection("db1", []string{"col1", "col2"}),
				newCollection("db2", []string{"col1", "col2"}),
				newCollection("xdb1", []string{"col1", "col2"}),
			},
			conf: tmpConf{
				WhiteDbList: []string{"*"},
				BlackDbList: []string{"db2"},
				WhiteTbList: []string{"*"},
				BlackTbList: []string{""},
			},
			// match db1.*  => db1 and all tb
			retColList: []DbCollection{
				newCollection("db1", []string{"col1", "col2"}),
				newCollection("xdb1", []string{"col1", "col2"}),
			},
		},
		{
			name: "case4: 所有库表。但不包括所有库下的col2表",
			dbColList: []DbCollection{
				newCollection("db1", []string{"col1", "col2"}),
				newCollection("db2", []string{"col1", "col2"}),
				newCollection("xdb1", []string{"col1", "col2"}),
			},
			conf: tmpConf{
				WhiteDbList: []string{"*"},
				BlackDbList: []string{""},
				WhiteTbList: []string{"*"},
				BlackTbList: []string{"col2"},
			},
			// match db1.*  => db1 and all tb
			retColList: []DbCollection{
				newCollection("db1", []string{"col1"}),
				newCollection("db2", []string{"col1"}),
				newCollection("xdb1", []string{"col1"}),
			},
		},
		{
			name: "case5: db1下的所有表",
			dbColList: []DbCollection{
				newCollection("db1", []string{"tb_aa1", "tb_aa2", "xxxx"}),
				newCollection("db2", []string{"tb_aa1", "tb_aa2"}),
				newCollection("db22", []string{"tb_aa1", "tb_aa2"}),
			},
			conf: tmpConf{
				WhiteDbList: []string{"db1"},
				WhiteTbList: []string{"*"},
				BlackDbList: []string{""},
				BlackTbList: []string{""},
			},
			// match *.tb_aa* and not match db2*.tb_aa_1 => db1.tb_aa1, db1.tb_aa2
			retColList: []DbCollection{
				newCollection("db1", []string{"tb_aa1", "tb_aa2", "xxxx"}),
			},
		},
		{
			name: "case6: db1.tb_aa1",
			dbColList: []DbCollection{
				newCollection("db1", []string{"tb_aa1", "abc"}),
				newCollection("db2", []string{"tb_aa1", "tb_aa2"}),
				newCollection("db22", []string{"tb_aa1", "tb_aa2"}),
			},
			conf: tmpConf{
				WhiteDbList: []string{"db1"},
				WhiteTbList: []string{"tb_aa1"},
				BlackDbList: []string{""},
				BlackTbList: []string{""},
			},
			// match db1.* and not match db1.abc => db1.tb_aa1
			retColList: []DbCollection{
				newCollection("db1", []string{"tb_aa1"}),
			},
		},
		{
			name: "case7: 所有库中的tb_aa1表,但不包括db1中的tb_aa1表", // 无法实现
			dbColList: []DbCollection{
				newCollection("db1", []string{"tb_aa1", "abc"}),
				newCollection("db2", []string{"tb_aa1", "tb_aa2"}),
				newCollection("db22", []string{"tb_aa1", "tb_aa2"}),
			},
			conf: tmpConf{
				WhiteDbList: []string{"*"},
				WhiteTbList: []string{"tb_aa1"},
				BlackDbList: []string{"db1"},
				BlackTbList: []string{"tb_aa1"},
			},
			// match db1.* and not match db1.abc => db1.tb_aa1
			retColList: []DbCollection{},
		},
		{
			name: "case8: 指定库名 db1 db2 下的所有表",
			dbColList: []DbCollection{
				newCollection("db1", []string{"tb_aa1", "abc"}),
				newCollection("db2", []string{"tb_aa1", "tb_aa2"}),
				newCollection("db22", []string{"tb_aa1", "tb_aa2"}),
			},
			conf: tmpConf{
				WhiteDbList: []string{"db1", "db2"},
				WhiteTbList: []string{"*"},
				BlackDbList: []string{""},
				BlackTbList: []string{""},
			},
			// match db1.* and not match db1.abc => db1.tb_aa1
			retColList: []DbCollection{
				newCollection("db1", []string{"tb_aa1", "abc"}),
				newCollection("db2", []string{"tb_aa1", "tb_aa2"}),
			},
		},
	}

	for i, item := range input {
		filter := NewNsFilter(item.conf.WhiteDbList, item.conf.BlackDbList, item.conf.WhiteTbList, item.conf.BlackTbList)
		var retRows []DbCollection
		for _, dbCol := range item.dbColList {
			var retRow DbCollection
			retRow.Db = dbCol.Db
			retRow.Col, _ = filter.FilterTbV2(dbCol.Db, dbCol.Col)
			if len(retRow.Col) == 0 {
				continue
			}
			retRows = append(retRows, retRow)
		}

		v := reflect.DeepEqual(retRows, item.retColList)
		emptyList := len(retRows) == 0 && len(item.retColList) == 0
		if !v && !emptyList {
			t.Errorf("error case %d, want:%v, got:%v", i+1, item.retColList, retRows)
		} else {
			t.Logf("ok case %d, want:%v, got:%v", i+1, item.retColList, retRows)
		}
	}
}

func TestNewNsFilterInV2_Cartesian(t *testing.T) {

	type tmpConf struct {
		WhiteDbList []string
		WhiteTbList []string
		BlackDbList []string
		BlackTbList []string
	}

	newCollection := func(db string, cols []string) DbCollection {
		return DbCollection{
			Db:  db,
			Col: cols,
		}
	}

	input := []struct {
		name       string
		dbColList  []DbCollection
		conf       tmpConf
		retColList []DbCollection
	}{
		{
			name: "case1: match all",
			dbColList: []DbCollection{
				newCollection("db1", []string{"col1", "col2"}),
				newCollection("db2", []string{"col1", "col2"}),
				newCollection("xdb1", []string{"col1", "col2"}),
			},
			conf: tmpConf{
				WhiteDbList: []string{"*"},
				WhiteTbList: []string{"*"},
				BlackDbList: []string{""},
				BlackTbList: []string{""},
			},
			// match db1.col1 and not match db2.col2 => db1.col1
			retColList: []DbCollection{
				newCollection("db1", []string{"col1", "col2"}),
				newCollection("db2", []string{"col1", "col2"}),
				newCollection("xdb1", []string{"col1", "col2"}),
			},
		},
		{
			name: "case2: match all and not match db2.tb2",
			dbColList: []DbCollection{
				newCollection("db1", []string{"col1", "col2"}),
				newCollection("db2", []string{"col1", "col2"}),
				newCollection("xdb1", []string{"col1", "col2"}),
			},
			conf: tmpConf{
				WhiteDbList: []string{"*"},
				BlackDbList: []string{"db2"},
				WhiteTbList: []string{"*"},
				BlackTbList: []string{"col2"},
			},
			// match all db and not match any tb => all db and all tb
			retColList: []DbCollection{
				newCollection("db1", []string{"col1", "col2"}),
				newCollection("db2", []string{"col1"}),
				newCollection("xdb1", []string{"col1", "col2"}),
			},
		},
		{
			name: "case3: 所有库表。但不包括db2库里的所有表",
			dbColList: []DbCollection{
				newCollection("db1", []string{"col1", "col2"}),
				newCollection("db2", []string{"col1", "col2"}),
				newCollection("xdb1", []string{"col1", "col2"}),
			},
			conf: tmpConf{
				WhiteDbList: []string{"*"},
				WhiteTbList: []string{"*"},
				BlackDbList: []string{"db2"},
				BlackTbList: []string{"*"},
			},
			// match db1.*  => db1 and all tb
			retColList: []DbCollection{
				newCollection("db1", []string{"col1", "col2"}),
				newCollection("xdb1", []string{"col1", "col2"}),
			},
		},
		{
			name: "case4: 所有库表。但不包括所有库下的col2表",
			dbColList: []DbCollection{
				newCollection("db1", []string{"col1", "col2"}),
				newCollection("db2", []string{"col1", "col2"}),
				newCollection("xdb1", []string{"col1", "col2"}),
			},
			conf: tmpConf{
				WhiteDbList: []string{"*"},
				WhiteTbList: []string{"*"},
				BlackDbList: []string{"*"},
				BlackTbList: []string{"col2"},
			},
			// match db1.*  => db1 and all tb
			retColList: []DbCollection{
				newCollection("db1", []string{"col1"}),
				newCollection("db2", []string{"col1"}),
				newCollection("xdb1", []string{"col1"}),
			},
		},
		{
			name: "case5: db1下的所有表",
			dbColList: []DbCollection{
				newCollection("db1", []string{"tb_aa1", "tb_aa2", "xxxx"}),
				newCollection("db2", []string{"tb_aa1", "tb_aa2"}),
				newCollection("db22", []string{"tb_aa1", "tb_aa2"}),
			},
			conf: tmpConf{
				WhiteDbList: []string{"db1"},
				WhiteTbList: []string{"*"},
				BlackDbList: []string{""},
				BlackTbList: []string{""},
			},
			// match *.tb_aa* and not match db2*.tb_aa_1 => db1.tb_aa1, db1.tb_aa2
			retColList: []DbCollection{
				newCollection("db1", []string{"tb_aa1", "tb_aa2", "xxxx"}),
			},
		},
		{
			name: "case6: db1.tb_aa1",
			dbColList: []DbCollection{
				newCollection("db1", []string{"tb_aa1", "abc"}),
				newCollection("db2", []string{"tb_aa1", "tb_aa2"}),
				newCollection("db22", []string{"tb_aa1", "tb_aa2"}),
			},
			conf: tmpConf{
				WhiteDbList: []string{"db1"},
				WhiteTbList: []string{"tb_aa1"},
				BlackDbList: []string{""},
				BlackTbList: []string{""},
			},
			// match db1.* and not match db1.abc => db1.tb_aa1
			retColList: []DbCollection{
				newCollection("db1", []string{"tb_aa1"}),
			},
		},
		{
			name: "case7: 所有库中的tb_aa1表，但不包括db1中的tb_aa1表",
			dbColList: []DbCollection{
				newCollection("db1", []string{"tb_aa1", "abc"}),
				newCollection("db2", []string{"tb_aa1", "tb_aa2"}),
				newCollection("db22", []string{"tb_aa1", "tb_aa2"}),
			},
			conf: tmpConf{
				WhiteDbList: []string{"*"},
				WhiteTbList: []string{"tb_aa1"},
				BlackDbList: []string{"db1"},
				BlackTbList: []string{"tb_aa1"},
			},
			// match db1.* and not match db1.abc => db1.tb_aa1
			retColList: []DbCollection{
				newCollection("db2", []string{"tb_aa1"}),
				newCollection("db22", []string{"tb_aa1"}),
			},
		},
		{
			name: "case8: 指定库名 db1 db2 下的所有表",
			dbColList: []DbCollection{
				newCollection("db1", []string{"tb_aa1", "abc"}),
				newCollection("db2", []string{"tb_aa1", "tb_aa2"}),
				newCollection("db22", []string{"tb_aa1", "tb_aa2"}),
			},
			conf: tmpConf{
				WhiteDbList: []string{"db1", "db2"},
				WhiteTbList: []string{"*"},
				BlackDbList: []string{""},
				BlackTbList: []string{""},
			},
			// match db1.* and not match db1.abc => db1.tb_aa1
			retColList: []DbCollection{
				newCollection("db1", []string{"tb_aa1", "abc"}),
				newCollection("db2", []string{"tb_aa1", "tb_aa2"}),
			},
		},
	}

	for i, item := range input {
		filter := NewNsFilter(item.conf.WhiteDbList, item.conf.BlackDbList, item.conf.WhiteTbList, item.conf.BlackTbList)
		var retRows []DbCollection
		for _, dbCol := range item.dbColList {
			var retRow DbCollection
			retRow.Db = dbCol.Db
			retRow.Col, _ = filter.FilterTbV2_Cartesian(dbCol.Db, dbCol.Col)
			if len(retRow.Col) == 0 {
				continue
			}
			retRows = append(retRows, retRow)
		}
		v := reflect.DeepEqual(retRows, item.retColList)
		if !v {
			t.Errorf("error case %d, want:%v, got:%v", i, item.retColList, retRows)
		} else {
			t.Logf("ok case %d, want:%v, got:%v", i, item.retColList, retRows)
		}
	}
}
