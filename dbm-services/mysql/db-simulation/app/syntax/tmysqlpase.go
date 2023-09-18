package syntax

import util "dbm-services/common/go-pubpkg/cmutil"

// ColDef TODO
type ColDef struct {
	Type        string `json:"type"`
	ColName     string `json:"col_name"`
	DataType    string `json:"data_type"`
	FieldLength int    `json:"field_length"`
	Nullable    bool   `json:"nullable"`
	DefaultVal  struct {
		Type  string `json:"type"`
		Value string `json:"value"`
	} `json:"default_val"`
	AutoIncrement       bool        `json:"auto_increment"`
	UniqueKey           bool        `json:"unique_key"`
	PrimaryKey          bool        `json:"primary_key"`
	Comment             string      `json:"comment"`
	CharacterSet        string      `json:"character_set"`
	Collate             string      `json:"collate"`
	ReferenceDefinition interface{} `json:"reference_definition"`
}

// KeyDef TODO
type KeyDef struct {
	Type     string `json:"type"`
	KeyName  string `json:"key_name"`
	KeyParts []struct {
		ColName string `json:"col_name"`
		KeyLen  int    `json:"key_len"`
	} `json:"key_parts"`
	KeyAlg              string      `json:"key_alg"`
	UniqueKey           bool        `json:"unique_key"`
	PrimaryKey          bool        `json:"primary_key"`
	Comment             string      `json:"comment"`
	ForeignKey          bool        `json:"foreign_key"`
	ReferenceDefinition interface{} `json:"reference_definition"`
}

// TableOption TODO
type TableOption struct {
	Key   string      `json:"key"`
	Value interface{} `json:"value"`
}

// ConverTableOptionToMap TODO
func ConverTableOptionToMap(options []TableOption) map[string]interface{} {
	r := make(map[string]interface{})
	for _, v := range options {
		if !util.IsEmpty(v.Key) {
			r[v.Key] = v.Value
		}
	}
	return r
}

// CreateTableResult TODO
type CreateTableResult struct {
	QueryID             int    `json:"query_id"`
	Command             string `json:"command"`
	DbName              string `json:"db_name"`
	TableName           string `json:"table_name"`
	IsTemporary         bool   `json:"is_temporary"`
	IfNotExists         bool   `json:"if_not_exists"`
	IsCreateTableLike   bool   `json:"is_create_table_like"`
	IsCreateTableSelect bool   `json:"is_create_table_select"`
	CreateDefinitions   struct {
		ColDefs []ColDef `json:"col_defs"`
		KeyDefs []KeyDef `json:"key_defs"`
	} `json:"create_definitions"`
	TableOptions     []TableOption          `json:"table_options,omitempty"`
	TableOptionMap   map[string]interface{} `json:"-"`
	PartitionOptions interface{}            `json:"partition_options"`
}

// CreateDBResult TODO
type CreateDBResult struct {
	QueryID      int    `json:"query_id"`
	Command      string `json:"command"`
	DbName       string `json:"db_name"`
	CharacterSet string `json:"character_set"`
	Collate      string `json:"collate"`
}

// AlterTableResult TODO
type AlterTableResult struct {
	QueryID          int            `json:"query_id"`
	Command          string         `json:"command"`
	DbName           string         `json:"db_name"`
	TableName        string         `json:"table_name"`
	AlterCommands    []AlterCommand `json:"alter_commands"`
	PartitionOptions interface{}    `json:"partition_options"`
}

// AlterCommand TODO
type AlterCommand struct {
	Type         string        `json:"type"`
	ColDef       ColDef        `json:"col_def,omitempty"`
	After        string        `json:"after,omitempty"`
	KeyDef       KeyDef        `json:"key_def,omitempty"`
	ColName      string        `json:"col_name,omitempty"`
	KeyName      string        `json:"key_name,omitempty"`
	DropPrimary  bool          `json:"drop_primary,omitempty"`
	DropForeign  bool          `json:"drop_foreign,omitempty"`
	DbName       string        `json:"db_name,omitempty"`
	TableName    string        `json:"table_name,omitempty"`
	OldKeyName   string        `json:"old_key_name,omitempty"`
	NewKeyName   string        `json:"new_key_name,omitempty"`
	TableOptions []TableOption `json:"table_options,omitempty"`
	Algorithm    string        `json:"algorithm,omitempty"`
	Lock         string        `json:"lock,omitempty"`
}

// ChangeDbResult TODO
type ChangeDbResult struct {
	QueryID int    `json:"query_id"`
	Command string `json:"command"`
	DbName  string `json:"db_name"`
}

// ErrorResult TODO
type ErrorResult struct {
	QueryID   int    `json:"query_id"`
	Command   string `json:"command"`
	ErrorCode int    `json:"error_code,omitempty"`
	ErrorMsg  string `json:"error_msg,omitempty"`
}

// ParseBase TODO
type ParseBase struct {
	QueryId     int    `json:"query_id"`
	Command     string `json:"command"`
	QueryString string `json:"query_string,omitempty"`
}

// ParseLineQueryBase TODO
type ParseLineQueryBase struct {
	QueryId         int    `json:"query_id"`
	Command         string `json:"command"`
	QueryString     string `json:"query_string,omitempty"`
	ErrorCode       int    `json:"error_code,omitempty"`
	ErrorMsg        string `json:"error_msg,omitempty"`
	MinMySQLVersion int    `json:"min_mysql_version"`
	MaxMySQLVersion int    `json:"max_my_sql_version"`
}

// UserHost TODO
type UserHost struct {
	User string `json:"user"`
	Host string `json:"host"`
}

// CreateView TODO
type CreateView struct {
	ParseBase
	DbName      string   `json:"db_name,omitempty"`
	ViewName    string   `json:"view_name,omitempty"`
	FieldNames  []string `json:"field_names,omitempty"`
	Definer     UserHost `json:"definer,omitempty"`
	Algorithm   string   `json:"algorithm,omitempty"`
	SqlSecurity string   `json:"sql_security,omitempty"`
	AsSelect    string   `json:"as_select,omitempty"`
	CheckOption string   `json:"check_option,omitempty"`
}

// CreateProcedure TODO
type CreateProcedure struct {
	ParseBase
	Definer     UserHost `json:"definer,omitempty"`
	SpName      string   `json:"sp_name,omitempty"`
	SqlSecurity string   `json:"sql_security,omitempty"`
	DataAccess  string   `json:"data_access,omitempty"`
}

// CreateTrigger TODO
type CreateTrigger struct {
	ParseBase
	Definer      UserHost `json:"definer,omitempty"`
	TriggerName  string   `json:"trigger_name,omitempty"`
	TableName    string   `json:"table_name"`
	TriggerEvent string   `json:"trigger_event"`
}

// CreateFunction TODO
type CreateFunction struct {
	ParseBase
	Definer UserHost `json:"definer,omitempty"`
	// TODO
}

// CreateEvent TODO
type CreateEvent struct {
	ParseBase
	Definer UserHost `json:"definer,omitempty"`
	// TODO
}

// CreateIndex TODO
type CreateIndex struct {
	ParseBase
	DbName    string   `json:"db_name,omitempty"`
	TableName string   `json:"table_name"`
	KeyDefs   []KeyDef `json:"key_defs"`
	Algorithm string   `json:"algorithm,omitempty"`
	Lock      string   `json:"lock,omitempty"`
}

// DeleteResult TODO
type DeleteResult struct {
	ParseBase
	DbName    string `json:"db_name,omitempty"`
	TableName string `json:"table_name"`
	HasWhere  bool   `json:"has_where"`
	Limit     int    `json:"limit"`
}

// UpdateResult TODO
type UpdateResult struct {
	ParseBase
	DbName           string `json:"db_name,omitempty"`
	TableName        string `json:"table_name"`
	UpdateLockOption string `json:"update_lock_option"`
	HasIgnore        bool   `json:"has_ignore"`
	HasWhere         bool   `json:"has_where"`
	Limit            int    `json:"limit"`
}
