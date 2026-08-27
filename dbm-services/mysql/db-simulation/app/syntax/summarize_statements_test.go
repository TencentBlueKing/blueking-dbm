package syntax_test

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"dbm-services/mysql/db-simulation/app/syntax"
)

func TestSummarizeParsedStatements_CommandCountsAndAlterGrouping(t *testing.T) {
	byFile := map[string][]syntax.ParseIncludeTableBase{
		"change.sql": {
			{Command: syntax.SQLTypeUseDb, DbName: "db1"},
			{
				Command:     syntax.SQLTypeAlterTable,
				TableName:   "t1",
				QueryString: "ALTER TABLE `t1` ADD COLUMN `foo` INT",
			},
			{
				Command:     syntax.SQLTypeAlterTable,
				TableName:   "t1",
				QueryString: "ALTER TABLE `t1` DROP COLUMN `bar`",
			},
			{Command: syntax.SQLTypeInsert, DbName: "db1", TableName: "t1"},
			{Command: syntax.SQLTypeInsertSelect, DbName: "db1", TableName: "t1"},
			{Command: syntax.SQLTypeDelete, DbName: "db1", TableName: "t1"},
		},
		"alter_user.sql": {
			{
				Command:     syntax.SQLTypeAlterTable,
				DbName:      "db2",
				TableName:   "t2",
				QueryString: "ALTER TABLE `t2` ADD INDEX `idx_a` (`a`)",
			},
		},
		"dml_only.sql": {
			{Command: syntax.SQLTypeInsert, DbName: "db3", TableName: "t3"},
			{Command: syntax.SQLTypeDelete, DbName: "db3", TableName: "t3"},
		},
	}

	summary, err := syntax.SummarizeParsedStatements(byFile, []string{"change.sql", "alter_user.sql", "dml_only.sql"}, true)
	require.NoError(t, err)
	require.NotNil(t, summary)

	assert.Equal(t, 2, summary.CommandCounts[syntax.SQLTypeDelete])
	assert.Equal(t, 2, summary.CommandCounts[syntax.SQLTypeInsert])
	assert.Equal(t, 1, summary.CommandCounts[syntax.SQLTypeInsertSelect])
	assert.Equal(t, 3, summary.CommandCounts[syntax.SQLTypeAlterTable])
	assert.Equal(t, 1, summary.CommandCounts[syntax.SQLTypeUseDb])

	require.Len(t, summary.AlterTables, 2)
	assert.Equal(t, "change.sql", summary.AlterTables[0].FileName)
	require.Len(t, summary.AlterTables[0].Alters, 2)
	assert.Equal(t, "db1", summary.AlterTables[0].Alters[0].DbName)
	assert.Equal(t, "t1", summary.AlterTables[0].Alters[0].TableName)
	assert.Equal(t, "ALTER TABLE `t1` ADD COLUMN `foo` INT", summary.AlterTables[0].Alters[0].SqlText)
	assert.Equal(t, "db1", summary.AlterTables[0].Alters[1].DbName)
	assert.Equal(t, "t1", summary.AlterTables[0].Alters[1].TableName)
	assert.Equal(t, "ALTER TABLE `t1` DROP COLUMN `bar`", summary.AlterTables[0].Alters[1].SqlText)

	assert.Equal(t, "alter_user.sql", summary.AlterTables[1].FileName)
	require.Len(t, summary.AlterTables[1].Alters, 1)
	assert.Equal(t, "db2", summary.AlterTables[1].Alters[0].DbName)
	assert.Equal(t, "t2", summary.AlterTables[1].Alters[0].TableName)
	assert.Equal(t, "ALTER TABLE `t2` ADD INDEX `idx_a` (`a`)", summary.AlterTables[1].Alters[0].SqlText)
	assert.Empty(t, summary.DropTables)
	assert.Empty(t, summary.TruncateTables)
}

func TestSummarizeParsedStatements_UseDbDoesNotCrossFiles(t *testing.T) {
	byFile := map[string][]syntax.ParseIncludeTableBase{
		"a.sql": {
			{Command: syntax.SQLTypeUseDb, DbName: "db_a"},
			{Command: syntax.SQLTypeAlterTable, TableName: "t_a", QueryString: "ALTER TABLE t_a ADD COLUMN x INT"},
		},
		"b.sql": {
			{Command: syntax.SQLTypeAlterTable, TableName: "t_b", QueryString: "ALTER TABLE t_b ADD COLUMN y INT"},
		},
	}

	summary, err := syntax.SummarizeParsedStatements(byFile, []string{"a.sql", "b.sql"}, true)
	require.NoError(t, err)
	require.Len(t, summary.AlterTables, 2)
	assert.Equal(t, "db_a", summary.AlterTables[0].Alters[0].DbName)
	assert.Equal(t, "", summary.AlterTables[1].Alters[0].DbName)
}

func TestSummarizeParsedStatements_SyntaxError(t *testing.T) {
	byFile := map[string][]syntax.ParseIncludeTableBase{
		"bad.sql": {
			{Command: syntax.SQLTypeInsert, TableName: "t1"},
			{ErrorCode: 1064, ErrorMsg: "You have an error in your SQL syntax"},
		},
	}

	summary, err := syntax.SummarizeParsedStatements(byFile, []string{"bad.sql"}, true)
	require.Error(t, err)
	assert.Nil(t, summary)
	assert.Contains(t, err.Error(), "You have an error in your SQL syntax")
}

func TestSummarizeParsedStatements_SkipEmptyCommand(t *testing.T) {
	byFile := map[string][]syntax.ParseIncludeTableBase{
		"a.sql": {
			{Command: ""},
			{Command: syntax.SQLTypeDelete, TableName: "t1"},
		},
	}

	summary, err := syntax.SummarizeParsedStatements(byFile, []string{"a.sql"}, true)
	require.NoError(t, err)
	assert.Equal(t, 1, summary.CommandCounts[syntax.SQLTypeDelete])
	assert.Empty(t, summary.AlterTables)
	assert.Empty(t, summary.DropTables)
	assert.Empty(t, summary.TruncateTables)
}

func TestSummarizeParsedStatements_DropAndTruncateTables(t *testing.T) {
	byFile := map[string][]syntax.ParseIncludeTableBase{
		"ddl.sql": {
			{Command: syntax.SQLTypeUseDb, DbName: "db1"},
			{
				Command:         syntax.SQLTypeDropTable,
				DbName:          "db1",
				TableName:       "t1",
				QueryDigestText: "DROP TABLE `t1` ",
			},
			{
				Command:         syntax.SQLTypeDropTable,
				DbName:          "db2",
				TableName:       "t2",
				QueryDigestText: "DROP TABLE `db2` . `t2` , `t3` ",
			},
			{
				Command:         syntax.SQLTypeTruncate,
				QueryDigestText: "TRUNCATE TABLE `t4` ",
			},
			{
				Command:         syntax.SQLTypeTruncate,
				QueryDigestText: "TRUNCATE TABLE `db3` . `t5` ",
			},
		},
		"dml.sql": {
			{Command: syntax.SQLTypeDelete, TableName: "t9"},
		},
	}

	summary, err := syntax.SummarizeParsedStatements(byFile, []string{"ddl.sql", "dml.sql"}, true)
	require.NoError(t, err)

	assert.Equal(t, 2, summary.CommandCounts[syntax.SQLTypeDropTable])
	assert.Equal(t, 2, summary.CommandCounts[syntax.SQLTypeTruncate])

	require.Len(t, summary.DropTables, 1)
	assert.Equal(t, "ddl.sql", summary.DropTables[0].FileName)
	require.Len(t, summary.DropTables[0].Tables, 3)
	assert.Equal(t, syntax.TableRef{DbName: "db1", TableName: "t1"}, summary.DropTables[0].Tables[0])
	assert.Equal(t, syntax.TableRef{DbName: "db2", TableName: "t2"}, summary.DropTables[0].Tables[1])
	assert.Equal(t, syntax.TableRef{DbName: "db1", TableName: "t3"}, summary.DropTables[0].Tables[2])

	require.Len(t, summary.TruncateTables, 1)
	assert.Equal(t, "ddl.sql", summary.TruncateTables[0].FileName)
	require.Len(t, summary.TruncateTables[0].Tables, 2)
	assert.Equal(t, syntax.TableRef{DbName: "db1", TableName: "t4"}, summary.TruncateTables[0].Tables[0])
	assert.Equal(t, syntax.TableRef{DbName: "db3", TableName: "t5"}, summary.TruncateTables[0].Tables[1])
}

func TestSummarizeParsedStatements_UseDbThenQualifiedOverride(t *testing.T) {
	byFile := map[string][]syntax.ParseIncludeTableBase{
		"a.sql": {
			{Command: syntax.SQLTypeUseDb, DbName: "db1"},
			{Command: syntax.SQLTypeAlterTable, TableName: "t1", QueryString: "ALTER TABLE t1 ADD COLUMN x INT"},
			{Command: syntax.SQLTypeDropTable, TableName: "t2", QueryDigestText: "DROP TABLE `t2` "},
			{Command: syntax.SQLTypeUseDb, DbName: "db2"},
			{Command: syntax.SQLTypeTruncate, QueryDigestText: "TRUNCATE TABLE `t3` "},
			{
				Command:     syntax.SQLTypeAlterTable,
				DbName:      "dbx",
				TableName:   "t",
				QueryString: "ALTER TABLE `dbx`.`t` ADD COLUMN y INT",
			},
		},
	}

	summary, err := syntax.SummarizeParsedStatements(byFile, []string{"a.sql"}, false)
	require.NoError(t, err)

	require.Len(t, summary.AlterTables[0].Alters, 2)
	assert.Equal(t, syntax.AlterTableRef{DbName: "db1", TableName: "t1"}, summary.AlterTables[0].Alters[0])
	assert.Equal(t, syntax.AlterTableRef{DbName: "dbx", TableName: "t"}, summary.AlterTables[0].Alters[1])
	require.Len(t, summary.DropTables[0].Tables, 1)
	assert.Equal(t, syntax.TableRef{DbName: "db1", TableName: "t2"}, summary.DropTables[0].Tables[0])
	require.Len(t, summary.TruncateTables[0].Tables, 1)
	assert.Equal(t, syntax.TableRef{DbName: "db2", TableName: "t3"}, summary.TruncateTables[0].Tables[0])
}

func TestSummarizeParsedStatements_FileCommandCounts(t *testing.T) {
	byFile := map[string][]syntax.ParseIncludeTableBase{
		"change.sql": {
			{Command: syntax.SQLTypeUseDb, DbName: "db1"},
			{Command: syntax.SQLTypeAlterTable, TableName: "t1"},
			{Command: syntax.SQLTypeDelete, TableName: "t1"},
		},
		"dml.sql": {
			{Command: syntax.SQLTypeInsert, TableName: "t2"},
		},
	}

	summary, err := syntax.SummarizeParsedStatements(byFile, []string{"change.sql", "dml.sql"}, false)
	require.NoError(t, err)
	assert.Equal(t, map[string]int{
		syntax.SQLTypeUseDb:      1,
		syntax.SQLTypeAlterTable: 1,
		syntax.SQLTypeDelete:     1,
	}, summary.FileCommandCounts["change.sql"])
	assert.Equal(t, map[string]int{syntax.SQLTypeInsert: 1}, summary.FileCommandCounts["dml.sql"])
	assert.Equal(t, 1, summary.CommandCounts[syntax.SQLTypeInsert])
	assert.Equal(t, 1, summary.CommandCounts[syntax.SQLTypeDelete])
}

func TestSummarizeParsedStatements_OmitSQLText(t *testing.T) {
	byFile := map[string][]syntax.ParseIncludeTableBase{
		"change.sql": {
			{
				Command:     syntax.SQLTypeAlterTable,
				DbName:      "db1",
				TableName:   "t1",
				QueryString: "ALTER TABLE `t1` ADD COLUMN `foo` INT",
			},
		},
	}

	summary, err := syntax.SummarizeParsedStatements(byFile, []string{"change.sql"}, false)
	require.NoError(t, err)
	require.Len(t, summary.AlterTables, 1)
	require.Len(t, summary.AlterTables[0].Alters, 1)
	assert.Equal(t, "t1", summary.AlterTables[0].Alters[0].TableName)
	assert.Empty(t, summary.AlterTables[0].Alters[0].SqlText)
}
