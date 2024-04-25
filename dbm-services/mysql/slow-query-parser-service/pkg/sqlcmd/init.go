package sqlcmd

const (
	CmdDmlSelect  = "select"
	CmdDmlInsert  = "insert"
	CmdDmlUpdate  = "update"
	CmdDmlDelete  = "delete"
	CmdDmlReplace = "replace"
	CmdDmlCall    = "call"
	CmdDmlLoad    = "load"
	CmdDmlDo      = "do"
	CmdDmlHandler = "handler"
)

const (
	CmdDdlCreate        = "create"
	CmdDdlAlter         = "alter"
	CmdDdlDrop          = "drop"
	CmdDdlRenameTable   = "rename table"
	CmdDdlTruncateTable = "truncate table"
	CmdDdlSetRole       = "set role"
)

const (
	CmdAdminAlterUser     = "alter user"
	CmdAdminCreateUser    = "create user"
	CmdAdminDropUser      = "drop user"
	CmdAdminRenameUser    = "rename user"
	CmdAdminGrant         = "grant"
	CmdAdminRevoke        = "revoke"
	CmdAdminAnalyze       = "analyze"
	CmdAdminCheckTable    = "check table"
	CmdAdminChecksumTable = "checksum table"
	CmdAdminOptimizeTable = "optimize"
	CmdAdminRepair        = "repair"
	CmdAdminFlush         = "flush"
)
