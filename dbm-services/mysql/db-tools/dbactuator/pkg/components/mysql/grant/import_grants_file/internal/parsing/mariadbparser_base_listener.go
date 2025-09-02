// Code generated from MariaDBParser.g4 by ANTLR 4.13.2. DO NOT EDIT.

package parsing // MariaDBParser
import "github.com/antlr4-go/antlr/v4"

// BaseMariaDBParserListener is a complete listener for a parse tree produced by MariaDBParser.
type BaseMariaDBParserListener struct{}

var _ MariaDBParserListener = &BaseMariaDBParserListener{}

// VisitTerminal is called when a terminal node is visited.
func (s *BaseMariaDBParserListener) VisitTerminal(node antlr.TerminalNode) {}

// VisitErrorNode is called when an error node is visited.
func (s *BaseMariaDBParserListener) VisitErrorNode(node antlr.ErrorNode) {}

// EnterEveryRule is called when any rule is entered.
func (s *BaseMariaDBParserListener) EnterEveryRule(ctx antlr.ParserRuleContext) {}

// ExitEveryRule is called when any rule is exited.
func (s *BaseMariaDBParserListener) ExitEveryRule(ctx antlr.ParserRuleContext) {}

// EnterRoot is called when production root is entered.
func (s *BaseMariaDBParserListener) EnterRoot(ctx *RootContext) {}

// ExitRoot is called when production root is exited.
func (s *BaseMariaDBParserListener) ExitRoot(ctx *RootContext) {}

// EnterSqlStatements is called when production sqlStatements is entered.
func (s *BaseMariaDBParserListener) EnterSqlStatements(ctx *SqlStatementsContext) {}

// ExitSqlStatements is called when production sqlStatements is exited.
func (s *BaseMariaDBParserListener) ExitSqlStatements(ctx *SqlStatementsContext) {}

// EnterSqlStatement is called when production sqlStatement is entered.
func (s *BaseMariaDBParserListener) EnterSqlStatement(ctx *SqlStatementContext) {}

// ExitSqlStatement is called when production sqlStatement is exited.
func (s *BaseMariaDBParserListener) ExitSqlStatement(ctx *SqlStatementContext) {}

// EnterSetStatementFor is called when production setStatementFor is entered.
func (s *BaseMariaDBParserListener) EnterSetStatementFor(ctx *SetStatementForContext) {}

// ExitSetStatementFor is called when production setStatementFor is exited.
func (s *BaseMariaDBParserListener) ExitSetStatementFor(ctx *SetStatementForContext) {}

// EnterEmptyStatement_ is called when production emptyStatement_ is entered.
func (s *BaseMariaDBParserListener) EnterEmptyStatement_(ctx *EmptyStatement_Context) {}

// ExitEmptyStatement_ is called when production emptyStatement_ is exited.
func (s *BaseMariaDBParserListener) ExitEmptyStatement_(ctx *EmptyStatement_Context) {}

// EnterDdlStatement is called when production ddlStatement is entered.
func (s *BaseMariaDBParserListener) EnterDdlStatement(ctx *DdlStatementContext) {}

// ExitDdlStatement is called when production ddlStatement is exited.
func (s *BaseMariaDBParserListener) ExitDdlStatement(ctx *DdlStatementContext) {}

// EnterDmlStatement is called when production dmlStatement is entered.
func (s *BaseMariaDBParserListener) EnterDmlStatement(ctx *DmlStatementContext) {}

// ExitDmlStatement is called when production dmlStatement is exited.
func (s *BaseMariaDBParserListener) ExitDmlStatement(ctx *DmlStatementContext) {}

// EnterTransactionStatement is called when production transactionStatement is entered.
func (s *BaseMariaDBParserListener) EnterTransactionStatement(ctx *TransactionStatementContext) {}

// ExitTransactionStatement is called when production transactionStatement is exited.
func (s *BaseMariaDBParserListener) ExitTransactionStatement(ctx *TransactionStatementContext) {}

// EnterReplicationStatement is called when production replicationStatement is entered.
func (s *BaseMariaDBParserListener) EnterReplicationStatement(ctx *ReplicationStatementContext) {}

// ExitReplicationStatement is called when production replicationStatement is exited.
func (s *BaseMariaDBParserListener) ExitReplicationStatement(ctx *ReplicationStatementContext) {}

// EnterPreparedStatement is called when production preparedStatement is entered.
func (s *BaseMariaDBParserListener) EnterPreparedStatement(ctx *PreparedStatementContext) {}

// ExitPreparedStatement is called when production preparedStatement is exited.
func (s *BaseMariaDBParserListener) ExitPreparedStatement(ctx *PreparedStatementContext) {}

// EnterCompoundStatement is called when production compoundStatement is entered.
func (s *BaseMariaDBParserListener) EnterCompoundStatement(ctx *CompoundStatementContext) {}

// ExitCompoundStatement is called when production compoundStatement is exited.
func (s *BaseMariaDBParserListener) ExitCompoundStatement(ctx *CompoundStatementContext) {}

// EnterAdministrationStatement is called when production administrationStatement is entered.
func (s *BaseMariaDBParserListener) EnterAdministrationStatement(ctx *AdministrationStatementContext) {
}

// ExitAdministrationStatement is called when production administrationStatement is exited.
func (s *BaseMariaDBParserListener) ExitAdministrationStatement(ctx *AdministrationStatementContext) {
}

// EnterUtilityStatement is called when production utilityStatement is entered.
func (s *BaseMariaDBParserListener) EnterUtilityStatement(ctx *UtilityStatementContext) {}

// ExitUtilityStatement is called when production utilityStatement is exited.
func (s *BaseMariaDBParserListener) ExitUtilityStatement(ctx *UtilityStatementContext) {}

// EnterCreateDatabase is called when production createDatabase is entered.
func (s *BaseMariaDBParserListener) EnterCreateDatabase(ctx *CreateDatabaseContext) {}

// ExitCreateDatabase is called when production createDatabase is exited.
func (s *BaseMariaDBParserListener) ExitCreateDatabase(ctx *CreateDatabaseContext) {}

// EnterCreateEvent is called when production createEvent is entered.
func (s *BaseMariaDBParserListener) EnterCreateEvent(ctx *CreateEventContext) {}

// ExitCreateEvent is called when production createEvent is exited.
func (s *BaseMariaDBParserListener) ExitCreateEvent(ctx *CreateEventContext) {}

// EnterCreateIndex is called when production createIndex is entered.
func (s *BaseMariaDBParserListener) EnterCreateIndex(ctx *CreateIndexContext) {}

// ExitCreateIndex is called when production createIndex is exited.
func (s *BaseMariaDBParserListener) ExitCreateIndex(ctx *CreateIndexContext) {}

// EnterCreateLogfileGroup is called when production createLogfileGroup is entered.
func (s *BaseMariaDBParserListener) EnterCreateLogfileGroup(ctx *CreateLogfileGroupContext) {}

// ExitCreateLogfileGroup is called when production createLogfileGroup is exited.
func (s *BaseMariaDBParserListener) ExitCreateLogfileGroup(ctx *CreateLogfileGroupContext) {}

// EnterCreateProcedure is called when production createProcedure is entered.
func (s *BaseMariaDBParserListener) EnterCreateProcedure(ctx *CreateProcedureContext) {}

// ExitCreateProcedure is called when production createProcedure is exited.
func (s *BaseMariaDBParserListener) ExitCreateProcedure(ctx *CreateProcedureContext) {}

// EnterCreateFunction is called when production createFunction is entered.
func (s *BaseMariaDBParserListener) EnterCreateFunction(ctx *CreateFunctionContext) {}

// ExitCreateFunction is called when production createFunction is exited.
func (s *BaseMariaDBParserListener) ExitCreateFunction(ctx *CreateFunctionContext) {}

// EnterCreateRole is called when production createRole is entered.
func (s *BaseMariaDBParserListener) EnterCreateRole(ctx *CreateRoleContext) {}

// ExitCreateRole is called when production createRole is exited.
func (s *BaseMariaDBParserListener) ExitCreateRole(ctx *CreateRoleContext) {}

// EnterCreateServer is called when production createServer is entered.
func (s *BaseMariaDBParserListener) EnterCreateServer(ctx *CreateServerContext) {}

// ExitCreateServer is called when production createServer is exited.
func (s *BaseMariaDBParserListener) ExitCreateServer(ctx *CreateServerContext) {}

// EnterCopyCreateTable is called when production copyCreateTable is entered.
func (s *BaseMariaDBParserListener) EnterCopyCreateTable(ctx *CopyCreateTableContext) {}

// ExitCopyCreateTable is called when production copyCreateTable is exited.
func (s *BaseMariaDBParserListener) ExitCopyCreateTable(ctx *CopyCreateTableContext) {}

// EnterQueryCreateTable is called when production queryCreateTable is entered.
func (s *BaseMariaDBParserListener) EnterQueryCreateTable(ctx *QueryCreateTableContext) {}

// ExitQueryCreateTable is called when production queryCreateTable is exited.
func (s *BaseMariaDBParserListener) ExitQueryCreateTable(ctx *QueryCreateTableContext) {}

// EnterColumnCreateTable is called when production columnCreateTable is entered.
func (s *BaseMariaDBParserListener) EnterColumnCreateTable(ctx *ColumnCreateTableContext) {}

// ExitColumnCreateTable is called when production columnCreateTable is exited.
func (s *BaseMariaDBParserListener) ExitColumnCreateTable(ctx *ColumnCreateTableContext) {}

// EnterCreateTablespaceInnodb is called when production createTablespaceInnodb is entered.
func (s *BaseMariaDBParserListener) EnterCreateTablespaceInnodb(ctx *CreateTablespaceInnodbContext) {}

// ExitCreateTablespaceInnodb is called when production createTablespaceInnodb is exited.
func (s *BaseMariaDBParserListener) ExitCreateTablespaceInnodb(ctx *CreateTablespaceInnodbContext) {}

// EnterCreateTablespaceNdb is called when production createTablespaceNdb is entered.
func (s *BaseMariaDBParserListener) EnterCreateTablespaceNdb(ctx *CreateTablespaceNdbContext) {}

// ExitCreateTablespaceNdb is called when production createTablespaceNdb is exited.
func (s *BaseMariaDBParserListener) ExitCreateTablespaceNdb(ctx *CreateTablespaceNdbContext) {}

// EnterCreateTrigger is called when production createTrigger is entered.
func (s *BaseMariaDBParserListener) EnterCreateTrigger(ctx *CreateTriggerContext) {}

// ExitCreateTrigger is called when production createTrigger is exited.
func (s *BaseMariaDBParserListener) ExitCreateTrigger(ctx *CreateTriggerContext) {}

// EnterWithClause is called when production withClause is entered.
func (s *BaseMariaDBParserListener) EnterWithClause(ctx *WithClauseContext) {}

// ExitWithClause is called when production withClause is exited.
func (s *BaseMariaDBParserListener) ExitWithClause(ctx *WithClauseContext) {}

// EnterCommonTableExpressions is called when production commonTableExpressions is entered.
func (s *BaseMariaDBParserListener) EnterCommonTableExpressions(ctx *CommonTableExpressionsContext) {}

// ExitCommonTableExpressions is called when production commonTableExpressions is exited.
func (s *BaseMariaDBParserListener) ExitCommonTableExpressions(ctx *CommonTableExpressionsContext) {}

// EnterCteName is called when production cteName is entered.
func (s *BaseMariaDBParserListener) EnterCteName(ctx *CteNameContext) {}

// ExitCteName is called when production cteName is exited.
func (s *BaseMariaDBParserListener) ExitCteName(ctx *CteNameContext) {}

// EnterCteColumnName is called when production cteColumnName is entered.
func (s *BaseMariaDBParserListener) EnterCteColumnName(ctx *CteColumnNameContext) {}

// ExitCteColumnName is called when production cteColumnName is exited.
func (s *BaseMariaDBParserListener) ExitCteColumnName(ctx *CteColumnNameContext) {}

// EnterCreateView is called when production createView is entered.
func (s *BaseMariaDBParserListener) EnterCreateView(ctx *CreateViewContext) {}

// ExitCreateView is called when production createView is exited.
func (s *BaseMariaDBParserListener) ExitCreateView(ctx *CreateViewContext) {}

// EnterCreateSequence is called when production createSequence is entered.
func (s *BaseMariaDBParserListener) EnterCreateSequence(ctx *CreateSequenceContext) {}

// ExitCreateSequence is called when production createSequence is exited.
func (s *BaseMariaDBParserListener) ExitCreateSequence(ctx *CreateSequenceContext) {}

// EnterSequenceSpec is called when production sequenceSpec is entered.
func (s *BaseMariaDBParserListener) EnterSequenceSpec(ctx *SequenceSpecContext) {}

// ExitSequenceSpec is called when production sequenceSpec is exited.
func (s *BaseMariaDBParserListener) ExitSequenceSpec(ctx *SequenceSpecContext) {}

// EnterCreateDatabaseOption is called when production createDatabaseOption is entered.
func (s *BaseMariaDBParserListener) EnterCreateDatabaseOption(ctx *CreateDatabaseOptionContext) {}

// ExitCreateDatabaseOption is called when production createDatabaseOption is exited.
func (s *BaseMariaDBParserListener) ExitCreateDatabaseOption(ctx *CreateDatabaseOptionContext) {}

// EnterCharSet is called when production charSet is entered.
func (s *BaseMariaDBParserListener) EnterCharSet(ctx *CharSetContext) {}

// ExitCharSet is called when production charSet is exited.
func (s *BaseMariaDBParserListener) ExitCharSet(ctx *CharSetContext) {}

// EnterCurrentUserExpression is called when production currentUserExpression is entered.
func (s *BaseMariaDBParserListener) EnterCurrentUserExpression(ctx *CurrentUserExpressionContext) {}

// ExitCurrentUserExpression is called when production currentUserExpression is exited.
func (s *BaseMariaDBParserListener) ExitCurrentUserExpression(ctx *CurrentUserExpressionContext) {}

// EnterOwnerStatement is called when production ownerStatement is entered.
func (s *BaseMariaDBParserListener) EnterOwnerStatement(ctx *OwnerStatementContext) {}

// ExitOwnerStatement is called when production ownerStatement is exited.
func (s *BaseMariaDBParserListener) ExitOwnerStatement(ctx *OwnerStatementContext) {}

// EnterPreciseSchedule is called when production preciseSchedule is entered.
func (s *BaseMariaDBParserListener) EnterPreciseSchedule(ctx *PreciseScheduleContext) {}

// ExitPreciseSchedule is called when production preciseSchedule is exited.
func (s *BaseMariaDBParserListener) ExitPreciseSchedule(ctx *PreciseScheduleContext) {}

// EnterIntervalSchedule is called when production intervalSchedule is entered.
func (s *BaseMariaDBParserListener) EnterIntervalSchedule(ctx *IntervalScheduleContext) {}

// ExitIntervalSchedule is called when production intervalSchedule is exited.
func (s *BaseMariaDBParserListener) ExitIntervalSchedule(ctx *IntervalScheduleContext) {}

// EnterTimestampValue is called when production timestampValue is entered.
func (s *BaseMariaDBParserListener) EnterTimestampValue(ctx *TimestampValueContext) {}

// ExitTimestampValue is called when production timestampValue is exited.
func (s *BaseMariaDBParserListener) ExitTimestampValue(ctx *TimestampValueContext) {}

// EnterIntervalExpr is called when production intervalExpr is entered.
func (s *BaseMariaDBParserListener) EnterIntervalExpr(ctx *IntervalExprContext) {}

// ExitIntervalExpr is called when production intervalExpr is exited.
func (s *BaseMariaDBParserListener) ExitIntervalExpr(ctx *IntervalExprContext) {}

// EnterIntervalType is called when production intervalType is entered.
func (s *BaseMariaDBParserListener) EnterIntervalType(ctx *IntervalTypeContext) {}

// ExitIntervalType is called when production intervalType is exited.
func (s *BaseMariaDBParserListener) ExitIntervalType(ctx *IntervalTypeContext) {}

// EnterEnableType is called when production enableType is entered.
func (s *BaseMariaDBParserListener) EnterEnableType(ctx *EnableTypeContext) {}

// ExitEnableType is called when production enableType is exited.
func (s *BaseMariaDBParserListener) ExitEnableType(ctx *EnableTypeContext) {}

// EnterIndexType is called when production indexType is entered.
func (s *BaseMariaDBParserListener) EnterIndexType(ctx *IndexTypeContext) {}

// ExitIndexType is called when production indexType is exited.
func (s *BaseMariaDBParserListener) ExitIndexType(ctx *IndexTypeContext) {}

// EnterIndexOption is called when production indexOption is entered.
func (s *BaseMariaDBParserListener) EnterIndexOption(ctx *IndexOptionContext) {}

// ExitIndexOption is called when production indexOption is exited.
func (s *BaseMariaDBParserListener) ExitIndexOption(ctx *IndexOptionContext) {}

// EnterProcedureParameter is called when production procedureParameter is entered.
func (s *BaseMariaDBParserListener) EnterProcedureParameter(ctx *ProcedureParameterContext) {}

// ExitProcedureParameter is called when production procedureParameter is exited.
func (s *BaseMariaDBParserListener) ExitProcedureParameter(ctx *ProcedureParameterContext) {}

// EnterFunctionParameter is called when production functionParameter is entered.
func (s *BaseMariaDBParserListener) EnterFunctionParameter(ctx *FunctionParameterContext) {}

// ExitFunctionParameter is called when production functionParameter is exited.
func (s *BaseMariaDBParserListener) ExitFunctionParameter(ctx *FunctionParameterContext) {}

// EnterRoutineComment is called when production routineComment is entered.
func (s *BaseMariaDBParserListener) EnterRoutineComment(ctx *RoutineCommentContext) {}

// ExitRoutineComment is called when production routineComment is exited.
func (s *BaseMariaDBParserListener) ExitRoutineComment(ctx *RoutineCommentContext) {}

// EnterRoutineLanguage is called when production routineLanguage is entered.
func (s *BaseMariaDBParserListener) EnterRoutineLanguage(ctx *RoutineLanguageContext) {}

// ExitRoutineLanguage is called when production routineLanguage is exited.
func (s *BaseMariaDBParserListener) ExitRoutineLanguage(ctx *RoutineLanguageContext) {}

// EnterRoutineBehavior is called when production routineBehavior is entered.
func (s *BaseMariaDBParserListener) EnterRoutineBehavior(ctx *RoutineBehaviorContext) {}

// ExitRoutineBehavior is called when production routineBehavior is exited.
func (s *BaseMariaDBParserListener) ExitRoutineBehavior(ctx *RoutineBehaviorContext) {}

// EnterRoutineData is called when production routineData is entered.
func (s *BaseMariaDBParserListener) EnterRoutineData(ctx *RoutineDataContext) {}

// ExitRoutineData is called when production routineData is exited.
func (s *BaseMariaDBParserListener) ExitRoutineData(ctx *RoutineDataContext) {}

// EnterRoutineSecurity is called when production routineSecurity is entered.
func (s *BaseMariaDBParserListener) EnterRoutineSecurity(ctx *RoutineSecurityContext) {}

// ExitRoutineSecurity is called when production routineSecurity is exited.
func (s *BaseMariaDBParserListener) ExitRoutineSecurity(ctx *RoutineSecurityContext) {}

// EnterServerOption is called when production serverOption is entered.
func (s *BaseMariaDBParserListener) EnterServerOption(ctx *ServerOptionContext) {}

// ExitServerOption is called when production serverOption is exited.
func (s *BaseMariaDBParserListener) ExitServerOption(ctx *ServerOptionContext) {}

// EnterCreateDefinitions is called when production createDefinitions is entered.
func (s *BaseMariaDBParserListener) EnterCreateDefinitions(ctx *CreateDefinitionsContext) {}

// ExitCreateDefinitions is called when production createDefinitions is exited.
func (s *BaseMariaDBParserListener) ExitCreateDefinitions(ctx *CreateDefinitionsContext) {}

// EnterColumnDeclaration is called when production columnDeclaration is entered.
func (s *BaseMariaDBParserListener) EnterColumnDeclaration(ctx *ColumnDeclarationContext) {}

// ExitColumnDeclaration is called when production columnDeclaration is exited.
func (s *BaseMariaDBParserListener) ExitColumnDeclaration(ctx *ColumnDeclarationContext) {}

// EnterConstraintDeclaration is called when production constraintDeclaration is entered.
func (s *BaseMariaDBParserListener) EnterConstraintDeclaration(ctx *ConstraintDeclarationContext) {}

// ExitConstraintDeclaration is called when production constraintDeclaration is exited.
func (s *BaseMariaDBParserListener) ExitConstraintDeclaration(ctx *ConstraintDeclarationContext) {}

// EnterIndexDeclaration is called when production indexDeclaration is entered.
func (s *BaseMariaDBParserListener) EnterIndexDeclaration(ctx *IndexDeclarationContext) {}

// ExitIndexDeclaration is called when production indexDeclaration is exited.
func (s *BaseMariaDBParserListener) ExitIndexDeclaration(ctx *IndexDeclarationContext) {}

// EnterColumnDefinition is called when production columnDefinition is entered.
func (s *BaseMariaDBParserListener) EnterColumnDefinition(ctx *ColumnDefinitionContext) {}

// ExitColumnDefinition is called when production columnDefinition is exited.
func (s *BaseMariaDBParserListener) ExitColumnDefinition(ctx *ColumnDefinitionContext) {}

// EnterNullColumnConstraint is called when production nullColumnConstraint is entered.
func (s *BaseMariaDBParserListener) EnterNullColumnConstraint(ctx *NullColumnConstraintContext) {}

// ExitNullColumnConstraint is called when production nullColumnConstraint is exited.
func (s *BaseMariaDBParserListener) ExitNullColumnConstraint(ctx *NullColumnConstraintContext) {}

// EnterDefaultColumnConstraint is called when production defaultColumnConstraint is entered.
func (s *BaseMariaDBParserListener) EnterDefaultColumnConstraint(ctx *DefaultColumnConstraintContext) {
}

// ExitDefaultColumnConstraint is called when production defaultColumnConstraint is exited.
func (s *BaseMariaDBParserListener) ExitDefaultColumnConstraint(ctx *DefaultColumnConstraintContext) {
}

// EnterVisibilityColumnConstraint is called when production visibilityColumnConstraint is entered.
func (s *BaseMariaDBParserListener) EnterVisibilityColumnConstraint(ctx *VisibilityColumnConstraintContext) {
}

// ExitVisibilityColumnConstraint is called when production visibilityColumnConstraint is exited.
func (s *BaseMariaDBParserListener) ExitVisibilityColumnConstraint(ctx *VisibilityColumnConstraintContext) {
}

// EnterInvisibilityColumnConstraint is called when production invisibilityColumnConstraint is entered.
func (s *BaseMariaDBParserListener) EnterInvisibilityColumnConstraint(ctx *InvisibilityColumnConstraintContext) {
}

// ExitInvisibilityColumnConstraint is called when production invisibilityColumnConstraint is exited.
func (s *BaseMariaDBParserListener) ExitInvisibilityColumnConstraint(ctx *InvisibilityColumnConstraintContext) {
}

// EnterAutoIncrementColumnConstraint is called when production autoIncrementColumnConstraint is entered.
func (s *BaseMariaDBParserListener) EnterAutoIncrementColumnConstraint(ctx *AutoIncrementColumnConstraintContext) {
}

// ExitAutoIncrementColumnConstraint is called when production autoIncrementColumnConstraint is exited.
func (s *BaseMariaDBParserListener) ExitAutoIncrementColumnConstraint(ctx *AutoIncrementColumnConstraintContext) {
}

// EnterPrimaryKeyColumnConstraint is called when production primaryKeyColumnConstraint is entered.
func (s *BaseMariaDBParserListener) EnterPrimaryKeyColumnConstraint(ctx *PrimaryKeyColumnConstraintContext) {
}

// ExitPrimaryKeyColumnConstraint is called when production primaryKeyColumnConstraint is exited.
func (s *BaseMariaDBParserListener) ExitPrimaryKeyColumnConstraint(ctx *PrimaryKeyColumnConstraintContext) {
}

// EnterUniqueKeyColumnConstraint is called when production uniqueKeyColumnConstraint is entered.
func (s *BaseMariaDBParserListener) EnterUniqueKeyColumnConstraint(ctx *UniqueKeyColumnConstraintContext) {
}

// ExitUniqueKeyColumnConstraint is called when production uniqueKeyColumnConstraint is exited.
func (s *BaseMariaDBParserListener) ExitUniqueKeyColumnConstraint(ctx *UniqueKeyColumnConstraintContext) {
}

// EnterCommentColumnConstraint is called when production commentColumnConstraint is entered.
func (s *BaseMariaDBParserListener) EnterCommentColumnConstraint(ctx *CommentColumnConstraintContext) {
}

// ExitCommentColumnConstraint is called when production commentColumnConstraint is exited.
func (s *BaseMariaDBParserListener) ExitCommentColumnConstraint(ctx *CommentColumnConstraintContext) {
}

// EnterFormatColumnConstraint is called when production formatColumnConstraint is entered.
func (s *BaseMariaDBParserListener) EnterFormatColumnConstraint(ctx *FormatColumnConstraintContext) {}

// ExitFormatColumnConstraint is called when production formatColumnConstraint is exited.
func (s *BaseMariaDBParserListener) ExitFormatColumnConstraint(ctx *FormatColumnConstraintContext) {}

// EnterStorageColumnConstraint is called when production storageColumnConstraint is entered.
func (s *BaseMariaDBParserListener) EnterStorageColumnConstraint(ctx *StorageColumnConstraintContext) {
}

// ExitStorageColumnConstraint is called when production storageColumnConstraint is exited.
func (s *BaseMariaDBParserListener) ExitStorageColumnConstraint(ctx *StorageColumnConstraintContext) {
}

// EnterReferenceColumnConstraint is called when production referenceColumnConstraint is entered.
func (s *BaseMariaDBParserListener) EnterReferenceColumnConstraint(ctx *ReferenceColumnConstraintContext) {
}

// ExitReferenceColumnConstraint is called when production referenceColumnConstraint is exited.
func (s *BaseMariaDBParserListener) ExitReferenceColumnConstraint(ctx *ReferenceColumnConstraintContext) {
}

// EnterCollateColumnConstraint is called when production collateColumnConstraint is entered.
func (s *BaseMariaDBParserListener) EnterCollateColumnConstraint(ctx *CollateColumnConstraintContext) {
}

// ExitCollateColumnConstraint is called when production collateColumnConstraint is exited.
func (s *BaseMariaDBParserListener) ExitCollateColumnConstraint(ctx *CollateColumnConstraintContext) {
}

// EnterGeneratedColumnConstraint is called when production generatedColumnConstraint is entered.
func (s *BaseMariaDBParserListener) EnterGeneratedColumnConstraint(ctx *GeneratedColumnConstraintContext) {
}

// ExitGeneratedColumnConstraint is called when production generatedColumnConstraint is exited.
func (s *BaseMariaDBParserListener) ExitGeneratedColumnConstraint(ctx *GeneratedColumnConstraintContext) {
}

// EnterSerialDefaultColumnConstraint is called when production serialDefaultColumnConstraint is entered.
func (s *BaseMariaDBParserListener) EnterSerialDefaultColumnConstraint(ctx *SerialDefaultColumnConstraintContext) {
}

// ExitSerialDefaultColumnConstraint is called when production serialDefaultColumnConstraint is exited.
func (s *BaseMariaDBParserListener) ExitSerialDefaultColumnConstraint(ctx *SerialDefaultColumnConstraintContext) {
}

// EnterCheckColumnConstraint is called when production checkColumnConstraint is entered.
func (s *BaseMariaDBParserListener) EnterCheckColumnConstraint(ctx *CheckColumnConstraintContext) {}

// ExitCheckColumnConstraint is called when production checkColumnConstraint is exited.
func (s *BaseMariaDBParserListener) ExitCheckColumnConstraint(ctx *CheckColumnConstraintContext) {}

// EnterPrimaryKeyTableConstraint is called when production primaryKeyTableConstraint is entered.
func (s *BaseMariaDBParserListener) EnterPrimaryKeyTableConstraint(ctx *PrimaryKeyTableConstraintContext) {
}

// ExitPrimaryKeyTableConstraint is called when production primaryKeyTableConstraint is exited.
func (s *BaseMariaDBParserListener) ExitPrimaryKeyTableConstraint(ctx *PrimaryKeyTableConstraintContext) {
}

// EnterUniqueKeyTableConstraint is called when production uniqueKeyTableConstraint is entered.
func (s *BaseMariaDBParserListener) EnterUniqueKeyTableConstraint(ctx *UniqueKeyTableConstraintContext) {
}

// ExitUniqueKeyTableConstraint is called when production uniqueKeyTableConstraint is exited.
func (s *BaseMariaDBParserListener) ExitUniqueKeyTableConstraint(ctx *UniqueKeyTableConstraintContext) {
}

// EnterForeignKeyTableConstraint is called when production foreignKeyTableConstraint is entered.
func (s *BaseMariaDBParserListener) EnterForeignKeyTableConstraint(ctx *ForeignKeyTableConstraintContext) {
}

// ExitForeignKeyTableConstraint is called when production foreignKeyTableConstraint is exited.
func (s *BaseMariaDBParserListener) ExitForeignKeyTableConstraint(ctx *ForeignKeyTableConstraintContext) {
}

// EnterCheckTableConstraint is called when production checkTableConstraint is entered.
func (s *BaseMariaDBParserListener) EnterCheckTableConstraint(ctx *CheckTableConstraintContext) {}

// ExitCheckTableConstraint is called when production checkTableConstraint is exited.
func (s *BaseMariaDBParserListener) ExitCheckTableConstraint(ctx *CheckTableConstraintContext) {}

// EnterReferenceDefinition is called when production referenceDefinition is entered.
func (s *BaseMariaDBParserListener) EnterReferenceDefinition(ctx *ReferenceDefinitionContext) {}

// ExitReferenceDefinition is called when production referenceDefinition is exited.
func (s *BaseMariaDBParserListener) ExitReferenceDefinition(ctx *ReferenceDefinitionContext) {}

// EnterReferenceAction is called when production referenceAction is entered.
func (s *BaseMariaDBParserListener) EnterReferenceAction(ctx *ReferenceActionContext) {}

// ExitReferenceAction is called when production referenceAction is exited.
func (s *BaseMariaDBParserListener) ExitReferenceAction(ctx *ReferenceActionContext) {}

// EnterReferenceControlType is called when production referenceControlType is entered.
func (s *BaseMariaDBParserListener) EnterReferenceControlType(ctx *ReferenceControlTypeContext) {}

// ExitReferenceControlType is called when production referenceControlType is exited.
func (s *BaseMariaDBParserListener) ExitReferenceControlType(ctx *ReferenceControlTypeContext) {}

// EnterSimpleIndexDeclaration is called when production simpleIndexDeclaration is entered.
func (s *BaseMariaDBParserListener) EnterSimpleIndexDeclaration(ctx *SimpleIndexDeclarationContext) {}

// ExitSimpleIndexDeclaration is called when production simpleIndexDeclaration is exited.
func (s *BaseMariaDBParserListener) ExitSimpleIndexDeclaration(ctx *SimpleIndexDeclarationContext) {}

// EnterSpecialIndexDeclaration is called when production specialIndexDeclaration is entered.
func (s *BaseMariaDBParserListener) EnterSpecialIndexDeclaration(ctx *SpecialIndexDeclarationContext) {
}

// ExitSpecialIndexDeclaration is called when production specialIndexDeclaration is exited.
func (s *BaseMariaDBParserListener) ExitSpecialIndexDeclaration(ctx *SpecialIndexDeclarationContext) {
}

// EnterTableOptionEngine is called when production tableOptionEngine is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionEngine(ctx *TableOptionEngineContext) {}

// ExitTableOptionEngine is called when production tableOptionEngine is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionEngine(ctx *TableOptionEngineContext) {}

// EnterTableOptionEngineAttribute is called when production tableOptionEngineAttribute is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionEngineAttribute(ctx *TableOptionEngineAttributeContext) {
}

// ExitTableOptionEngineAttribute is called when production tableOptionEngineAttribute is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionEngineAttribute(ctx *TableOptionEngineAttributeContext) {
}

// EnterTableOptionAutoextendSize is called when production tableOptionAutoextendSize is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionAutoextendSize(ctx *TableOptionAutoextendSizeContext) {
}

// ExitTableOptionAutoextendSize is called when production tableOptionAutoextendSize is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionAutoextendSize(ctx *TableOptionAutoextendSizeContext) {
}

// EnterTableOptionAutoIncrement is called when production tableOptionAutoIncrement is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionAutoIncrement(ctx *TableOptionAutoIncrementContext) {
}

// ExitTableOptionAutoIncrement is called when production tableOptionAutoIncrement is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionAutoIncrement(ctx *TableOptionAutoIncrementContext) {
}

// EnterTableOptionAverage is called when production tableOptionAverage is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionAverage(ctx *TableOptionAverageContext) {}

// ExitTableOptionAverage is called when production tableOptionAverage is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionAverage(ctx *TableOptionAverageContext) {}

// EnterTableOptionCharset is called when production tableOptionCharset is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionCharset(ctx *TableOptionCharsetContext) {}

// ExitTableOptionCharset is called when production tableOptionCharset is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionCharset(ctx *TableOptionCharsetContext) {}

// EnterTableOptionChecksum is called when production tableOptionChecksum is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionChecksum(ctx *TableOptionChecksumContext) {}

// ExitTableOptionChecksum is called when production tableOptionChecksum is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionChecksum(ctx *TableOptionChecksumContext) {}

// EnterTableOptionCollate is called when production tableOptionCollate is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionCollate(ctx *TableOptionCollateContext) {}

// ExitTableOptionCollate is called when production tableOptionCollate is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionCollate(ctx *TableOptionCollateContext) {}

// EnterTableOptionComment is called when production tableOptionComment is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionComment(ctx *TableOptionCommentContext) {}

// ExitTableOptionComment is called when production tableOptionComment is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionComment(ctx *TableOptionCommentContext) {}

// EnterTableOptionCompression is called when production tableOptionCompression is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionCompression(ctx *TableOptionCompressionContext) {}

// ExitTableOptionCompression is called when production tableOptionCompression is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionCompression(ctx *TableOptionCompressionContext) {}

// EnterTableOptionConnection is called when production tableOptionConnection is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionConnection(ctx *TableOptionConnectionContext) {}

// ExitTableOptionConnection is called when production tableOptionConnection is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionConnection(ctx *TableOptionConnectionContext) {}

// EnterTableOptionDataDirectory is called when production tableOptionDataDirectory is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionDataDirectory(ctx *TableOptionDataDirectoryContext) {
}

// ExitTableOptionDataDirectory is called when production tableOptionDataDirectory is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionDataDirectory(ctx *TableOptionDataDirectoryContext) {
}

// EnterTableOptionDelay is called when production tableOptionDelay is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionDelay(ctx *TableOptionDelayContext) {}

// ExitTableOptionDelay is called when production tableOptionDelay is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionDelay(ctx *TableOptionDelayContext) {}

// EnterTableOptionEncryption is called when production tableOptionEncryption is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionEncryption(ctx *TableOptionEncryptionContext) {}

// ExitTableOptionEncryption is called when production tableOptionEncryption is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionEncryption(ctx *TableOptionEncryptionContext) {}

// EnterTableOptionEncrypted is called when production tableOptionEncrypted is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionEncrypted(ctx *TableOptionEncryptedContext) {}

// ExitTableOptionEncrypted is called when production tableOptionEncrypted is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionEncrypted(ctx *TableOptionEncryptedContext) {}

// EnterTableOptionPageCompressed is called when production tableOptionPageCompressed is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionPageCompressed(ctx *TableOptionPageCompressedContext) {
}

// ExitTableOptionPageCompressed is called when production tableOptionPageCompressed is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionPageCompressed(ctx *TableOptionPageCompressedContext) {
}

// EnterTableOptionPageCompressionLevel is called when production tableOptionPageCompressionLevel is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionPageCompressionLevel(ctx *TableOptionPageCompressionLevelContext) {
}

// ExitTableOptionPageCompressionLevel is called when production tableOptionPageCompressionLevel is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionPageCompressionLevel(ctx *TableOptionPageCompressionLevelContext) {
}

// EnterTableOptionEncryptionKeyId is called when production tableOptionEncryptionKeyId is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionEncryptionKeyId(ctx *TableOptionEncryptionKeyIdContext) {
}

// ExitTableOptionEncryptionKeyId is called when production tableOptionEncryptionKeyId is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionEncryptionKeyId(ctx *TableOptionEncryptionKeyIdContext) {
}

// EnterTableOptionIndexDirectory is called when production tableOptionIndexDirectory is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionIndexDirectory(ctx *TableOptionIndexDirectoryContext) {
}

// ExitTableOptionIndexDirectory is called when production tableOptionIndexDirectory is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionIndexDirectory(ctx *TableOptionIndexDirectoryContext) {
}

// EnterTableOptionInsertMethod is called when production tableOptionInsertMethod is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionInsertMethod(ctx *TableOptionInsertMethodContext) {
}

// ExitTableOptionInsertMethod is called when production tableOptionInsertMethod is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionInsertMethod(ctx *TableOptionInsertMethodContext) {
}

// EnterTableOptionKeyBlockSize is called when production tableOptionKeyBlockSize is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionKeyBlockSize(ctx *TableOptionKeyBlockSizeContext) {
}

// ExitTableOptionKeyBlockSize is called when production tableOptionKeyBlockSize is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionKeyBlockSize(ctx *TableOptionKeyBlockSizeContext) {
}

// EnterTableOptionMaxRows is called when production tableOptionMaxRows is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionMaxRows(ctx *TableOptionMaxRowsContext) {}

// ExitTableOptionMaxRows is called when production tableOptionMaxRows is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionMaxRows(ctx *TableOptionMaxRowsContext) {}

// EnterTableOptionMinRows is called when production tableOptionMinRows is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionMinRows(ctx *TableOptionMinRowsContext) {}

// ExitTableOptionMinRows is called when production tableOptionMinRows is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionMinRows(ctx *TableOptionMinRowsContext) {}

// EnterTableOptionPackKeys is called when production tableOptionPackKeys is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionPackKeys(ctx *TableOptionPackKeysContext) {}

// ExitTableOptionPackKeys is called when production tableOptionPackKeys is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionPackKeys(ctx *TableOptionPackKeysContext) {}

// EnterTableOptionPassword is called when production tableOptionPassword is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionPassword(ctx *TableOptionPasswordContext) {}

// ExitTableOptionPassword is called when production tableOptionPassword is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionPassword(ctx *TableOptionPasswordContext) {}

// EnterTableOptionRowFormat is called when production tableOptionRowFormat is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionRowFormat(ctx *TableOptionRowFormatContext) {}

// ExitTableOptionRowFormat is called when production tableOptionRowFormat is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionRowFormat(ctx *TableOptionRowFormatContext) {}

// EnterTableOptionStartTransaction is called when production tableOptionStartTransaction is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionStartTransaction(ctx *TableOptionStartTransactionContext) {
}

// ExitTableOptionStartTransaction is called when production tableOptionStartTransaction is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionStartTransaction(ctx *TableOptionStartTransactionContext) {
}

// EnterTableOptionSecondaryEngineAttribute is called when production tableOptionSecondaryEngineAttribute is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionSecondaryEngineAttribute(ctx *TableOptionSecondaryEngineAttributeContext) {
}

// ExitTableOptionSecondaryEngineAttribute is called when production tableOptionSecondaryEngineAttribute is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionSecondaryEngineAttribute(ctx *TableOptionSecondaryEngineAttributeContext) {
}

// EnterTableOptionRecalculation is called when production tableOptionRecalculation is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionRecalculation(ctx *TableOptionRecalculationContext) {
}

// ExitTableOptionRecalculation is called when production tableOptionRecalculation is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionRecalculation(ctx *TableOptionRecalculationContext) {
}

// EnterTableOptionPersistent is called when production tableOptionPersistent is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionPersistent(ctx *TableOptionPersistentContext) {}

// ExitTableOptionPersistent is called when production tableOptionPersistent is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionPersistent(ctx *TableOptionPersistentContext) {}

// EnterTableOptionSamplePage is called when production tableOptionSamplePage is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionSamplePage(ctx *TableOptionSamplePageContext) {}

// ExitTableOptionSamplePage is called when production tableOptionSamplePage is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionSamplePage(ctx *TableOptionSamplePageContext) {}

// EnterTableOptionTablespace is called when production tableOptionTablespace is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionTablespace(ctx *TableOptionTablespaceContext) {}

// ExitTableOptionTablespace is called when production tableOptionTablespace is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionTablespace(ctx *TableOptionTablespaceContext) {}

// EnterTableOptionTableType is called when production tableOptionTableType is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionTableType(ctx *TableOptionTableTypeContext) {}

// ExitTableOptionTableType is called when production tableOptionTableType is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionTableType(ctx *TableOptionTableTypeContext) {}

// EnterTableOptionTransactional is called when production tableOptionTransactional is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionTransactional(ctx *TableOptionTransactionalContext) {
}

// ExitTableOptionTransactional is called when production tableOptionTransactional is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionTransactional(ctx *TableOptionTransactionalContext) {
}

// EnterTableOptionUnion is called when production tableOptionUnion is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionUnion(ctx *TableOptionUnionContext) {}

// ExitTableOptionUnion is called when production tableOptionUnion is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionUnion(ctx *TableOptionUnionContext) {}

// EnterTableOptionWithSystemVersioning is called when production tableOptionWithSystemVersioning is entered.
func (s *BaseMariaDBParserListener) EnterTableOptionWithSystemVersioning(ctx *TableOptionWithSystemVersioningContext) {
}

// ExitTableOptionWithSystemVersioning is called when production tableOptionWithSystemVersioning is exited.
func (s *BaseMariaDBParserListener) ExitTableOptionWithSystemVersioning(ctx *TableOptionWithSystemVersioningContext) {
}

// EnterTableType is called when production tableType is entered.
func (s *BaseMariaDBParserListener) EnterTableType(ctx *TableTypeContext) {}

// ExitTableType is called when production tableType is exited.
func (s *BaseMariaDBParserListener) ExitTableType(ctx *TableTypeContext) {}

// EnterTablespaceStorage is called when production tablespaceStorage is entered.
func (s *BaseMariaDBParserListener) EnterTablespaceStorage(ctx *TablespaceStorageContext) {}

// ExitTablespaceStorage is called when production tablespaceStorage is exited.
func (s *BaseMariaDBParserListener) ExitTablespaceStorage(ctx *TablespaceStorageContext) {}

// EnterPartitionDefinitions is called when production partitionDefinitions is entered.
func (s *BaseMariaDBParserListener) EnterPartitionDefinitions(ctx *PartitionDefinitionsContext) {}

// ExitPartitionDefinitions is called when production partitionDefinitions is exited.
func (s *BaseMariaDBParserListener) ExitPartitionDefinitions(ctx *PartitionDefinitionsContext) {}

// EnterPartitionFunctionHash is called when production partitionFunctionHash is entered.
func (s *BaseMariaDBParserListener) EnterPartitionFunctionHash(ctx *PartitionFunctionHashContext) {}

// ExitPartitionFunctionHash is called when production partitionFunctionHash is exited.
func (s *BaseMariaDBParserListener) ExitPartitionFunctionHash(ctx *PartitionFunctionHashContext) {}

// EnterPartitionFunctionKey is called when production partitionFunctionKey is entered.
func (s *BaseMariaDBParserListener) EnterPartitionFunctionKey(ctx *PartitionFunctionKeyContext) {}

// ExitPartitionFunctionKey is called when production partitionFunctionKey is exited.
func (s *BaseMariaDBParserListener) ExitPartitionFunctionKey(ctx *PartitionFunctionKeyContext) {}

// EnterPartitionFunctionRange is called when production partitionFunctionRange is entered.
func (s *BaseMariaDBParserListener) EnterPartitionFunctionRange(ctx *PartitionFunctionRangeContext) {}

// ExitPartitionFunctionRange is called when production partitionFunctionRange is exited.
func (s *BaseMariaDBParserListener) ExitPartitionFunctionRange(ctx *PartitionFunctionRangeContext) {}

// EnterPartitionFunctionList is called when production partitionFunctionList is entered.
func (s *BaseMariaDBParserListener) EnterPartitionFunctionList(ctx *PartitionFunctionListContext) {}

// ExitPartitionFunctionList is called when production partitionFunctionList is exited.
func (s *BaseMariaDBParserListener) ExitPartitionFunctionList(ctx *PartitionFunctionListContext) {}

// EnterPartitionSystemVersion is called when production partitionSystemVersion is entered.
func (s *BaseMariaDBParserListener) EnterPartitionSystemVersion(ctx *PartitionSystemVersionContext) {}

// ExitPartitionSystemVersion is called when production partitionSystemVersion is exited.
func (s *BaseMariaDBParserListener) ExitPartitionSystemVersion(ctx *PartitionSystemVersionContext) {}

// EnterPartitionSystemVersionDefinitions is called when production partitionSystemVersionDefinitions is entered.
func (s *BaseMariaDBParserListener) EnterPartitionSystemVersionDefinitions(ctx *PartitionSystemVersionDefinitionsContext) {
}

// ExitPartitionSystemVersionDefinitions is called when production partitionSystemVersionDefinitions is exited.
func (s *BaseMariaDBParserListener) ExitPartitionSystemVersionDefinitions(ctx *PartitionSystemVersionDefinitionsContext) {
}

// EnterPartitionSystemVersionDefinition is called when production partitionSystemVersionDefinition is entered.
func (s *BaseMariaDBParserListener) EnterPartitionSystemVersionDefinition(ctx *PartitionSystemVersionDefinitionContext) {
}

// ExitPartitionSystemVersionDefinition is called when production partitionSystemVersionDefinition is exited.
func (s *BaseMariaDBParserListener) ExitPartitionSystemVersionDefinition(ctx *PartitionSystemVersionDefinitionContext) {
}

// EnterSubPartitionFunctionHash is called when production subPartitionFunctionHash is entered.
func (s *BaseMariaDBParserListener) EnterSubPartitionFunctionHash(ctx *SubPartitionFunctionHashContext) {
}

// ExitSubPartitionFunctionHash is called when production subPartitionFunctionHash is exited.
func (s *BaseMariaDBParserListener) ExitSubPartitionFunctionHash(ctx *SubPartitionFunctionHashContext) {
}

// EnterSubPartitionFunctionKey is called when production subPartitionFunctionKey is entered.
func (s *BaseMariaDBParserListener) EnterSubPartitionFunctionKey(ctx *SubPartitionFunctionKeyContext) {
}

// ExitSubPartitionFunctionKey is called when production subPartitionFunctionKey is exited.
func (s *BaseMariaDBParserListener) ExitSubPartitionFunctionKey(ctx *SubPartitionFunctionKeyContext) {
}

// EnterPartitionComparison is called when production partitionComparison is entered.
func (s *BaseMariaDBParserListener) EnterPartitionComparison(ctx *PartitionComparisonContext) {}

// ExitPartitionComparison is called when production partitionComparison is exited.
func (s *BaseMariaDBParserListener) ExitPartitionComparison(ctx *PartitionComparisonContext) {}

// EnterPartitionListAtom is called when production partitionListAtom is entered.
func (s *BaseMariaDBParserListener) EnterPartitionListAtom(ctx *PartitionListAtomContext) {}

// ExitPartitionListAtom is called when production partitionListAtom is exited.
func (s *BaseMariaDBParserListener) ExitPartitionListAtom(ctx *PartitionListAtomContext) {}

// EnterPartitionListVector is called when production partitionListVector is entered.
func (s *BaseMariaDBParserListener) EnterPartitionListVector(ctx *PartitionListVectorContext) {}

// ExitPartitionListVector is called when production partitionListVector is exited.
func (s *BaseMariaDBParserListener) ExitPartitionListVector(ctx *PartitionListVectorContext) {}

// EnterPartitionSimple is called when production partitionSimple is entered.
func (s *BaseMariaDBParserListener) EnterPartitionSimple(ctx *PartitionSimpleContext) {}

// ExitPartitionSimple is called when production partitionSimple is exited.
func (s *BaseMariaDBParserListener) ExitPartitionSimple(ctx *PartitionSimpleContext) {}

// EnterPartitionDefinerAtom is called when production partitionDefinerAtom is entered.
func (s *BaseMariaDBParserListener) EnterPartitionDefinerAtom(ctx *PartitionDefinerAtomContext) {}

// ExitPartitionDefinerAtom is called when production partitionDefinerAtom is exited.
func (s *BaseMariaDBParserListener) ExitPartitionDefinerAtom(ctx *PartitionDefinerAtomContext) {}

// EnterPartitionDefinerVector is called when production partitionDefinerVector is entered.
func (s *BaseMariaDBParserListener) EnterPartitionDefinerVector(ctx *PartitionDefinerVectorContext) {}

// ExitPartitionDefinerVector is called when production partitionDefinerVector is exited.
func (s *BaseMariaDBParserListener) ExitPartitionDefinerVector(ctx *PartitionDefinerVectorContext) {}

// EnterSubpartitionDefinition is called when production subpartitionDefinition is entered.
func (s *BaseMariaDBParserListener) EnterSubpartitionDefinition(ctx *SubpartitionDefinitionContext) {}

// ExitSubpartitionDefinition is called when production subpartitionDefinition is exited.
func (s *BaseMariaDBParserListener) ExitSubpartitionDefinition(ctx *SubpartitionDefinitionContext) {}

// EnterPartitionOptionEngine is called when production partitionOptionEngine is entered.
func (s *BaseMariaDBParserListener) EnterPartitionOptionEngine(ctx *PartitionOptionEngineContext) {}

// ExitPartitionOptionEngine is called when production partitionOptionEngine is exited.
func (s *BaseMariaDBParserListener) ExitPartitionOptionEngine(ctx *PartitionOptionEngineContext) {}

// EnterPartitionOptionComment is called when production partitionOptionComment is entered.
func (s *BaseMariaDBParserListener) EnterPartitionOptionComment(ctx *PartitionOptionCommentContext) {}

// ExitPartitionOptionComment is called when production partitionOptionComment is exited.
func (s *BaseMariaDBParserListener) ExitPartitionOptionComment(ctx *PartitionOptionCommentContext) {}

// EnterPartitionOptionDataDirectory is called when production partitionOptionDataDirectory is entered.
func (s *BaseMariaDBParserListener) EnterPartitionOptionDataDirectory(ctx *PartitionOptionDataDirectoryContext) {
}

// ExitPartitionOptionDataDirectory is called when production partitionOptionDataDirectory is exited.
func (s *BaseMariaDBParserListener) ExitPartitionOptionDataDirectory(ctx *PartitionOptionDataDirectoryContext) {
}

// EnterPartitionOptionIndexDirectory is called when production partitionOptionIndexDirectory is entered.
func (s *BaseMariaDBParserListener) EnterPartitionOptionIndexDirectory(ctx *PartitionOptionIndexDirectoryContext) {
}

// ExitPartitionOptionIndexDirectory is called when production partitionOptionIndexDirectory is exited.
func (s *BaseMariaDBParserListener) ExitPartitionOptionIndexDirectory(ctx *PartitionOptionIndexDirectoryContext) {
}

// EnterPartitionOptionMaxRows is called when production partitionOptionMaxRows is entered.
func (s *BaseMariaDBParserListener) EnterPartitionOptionMaxRows(ctx *PartitionOptionMaxRowsContext) {}

// ExitPartitionOptionMaxRows is called when production partitionOptionMaxRows is exited.
func (s *BaseMariaDBParserListener) ExitPartitionOptionMaxRows(ctx *PartitionOptionMaxRowsContext) {}

// EnterPartitionOptionMinRows is called when production partitionOptionMinRows is entered.
func (s *BaseMariaDBParserListener) EnterPartitionOptionMinRows(ctx *PartitionOptionMinRowsContext) {}

// ExitPartitionOptionMinRows is called when production partitionOptionMinRows is exited.
func (s *BaseMariaDBParserListener) ExitPartitionOptionMinRows(ctx *PartitionOptionMinRowsContext) {}

// EnterPartitionOptionTablespace is called when production partitionOptionTablespace is entered.
func (s *BaseMariaDBParserListener) EnterPartitionOptionTablespace(ctx *PartitionOptionTablespaceContext) {
}

// ExitPartitionOptionTablespace is called when production partitionOptionTablespace is exited.
func (s *BaseMariaDBParserListener) ExitPartitionOptionTablespace(ctx *PartitionOptionTablespaceContext) {
}

// EnterPartitionOptionNodeGroup is called when production partitionOptionNodeGroup is entered.
func (s *BaseMariaDBParserListener) EnterPartitionOptionNodeGroup(ctx *PartitionOptionNodeGroupContext) {
}

// ExitPartitionOptionNodeGroup is called when production partitionOptionNodeGroup is exited.
func (s *BaseMariaDBParserListener) ExitPartitionOptionNodeGroup(ctx *PartitionOptionNodeGroupContext) {
}

// EnterAlterSimpleDatabase is called when production alterSimpleDatabase is entered.
func (s *BaseMariaDBParserListener) EnterAlterSimpleDatabase(ctx *AlterSimpleDatabaseContext) {}

// ExitAlterSimpleDatabase is called when production alterSimpleDatabase is exited.
func (s *BaseMariaDBParserListener) ExitAlterSimpleDatabase(ctx *AlterSimpleDatabaseContext) {}

// EnterAlterUpgradeName is called when production alterUpgradeName is entered.
func (s *BaseMariaDBParserListener) EnterAlterUpgradeName(ctx *AlterUpgradeNameContext) {}

// ExitAlterUpgradeName is called when production alterUpgradeName is exited.
func (s *BaseMariaDBParserListener) ExitAlterUpgradeName(ctx *AlterUpgradeNameContext) {}

// EnterAlterEvent is called when production alterEvent is entered.
func (s *BaseMariaDBParserListener) EnterAlterEvent(ctx *AlterEventContext) {}

// ExitAlterEvent is called when production alterEvent is exited.
func (s *BaseMariaDBParserListener) ExitAlterEvent(ctx *AlterEventContext) {}

// EnterAlterFunction is called when production alterFunction is entered.
func (s *BaseMariaDBParserListener) EnterAlterFunction(ctx *AlterFunctionContext) {}

// ExitAlterFunction is called when production alterFunction is exited.
func (s *BaseMariaDBParserListener) ExitAlterFunction(ctx *AlterFunctionContext) {}

// EnterAlterInstance is called when production alterInstance is entered.
func (s *BaseMariaDBParserListener) EnterAlterInstance(ctx *AlterInstanceContext) {}

// ExitAlterInstance is called when production alterInstance is exited.
func (s *BaseMariaDBParserListener) ExitAlterInstance(ctx *AlterInstanceContext) {}

// EnterAlterLogfileGroup is called when production alterLogfileGroup is entered.
func (s *BaseMariaDBParserListener) EnterAlterLogfileGroup(ctx *AlterLogfileGroupContext) {}

// ExitAlterLogfileGroup is called when production alterLogfileGroup is exited.
func (s *BaseMariaDBParserListener) ExitAlterLogfileGroup(ctx *AlterLogfileGroupContext) {}

// EnterAlterProcedure is called when production alterProcedure is entered.
func (s *BaseMariaDBParserListener) EnterAlterProcedure(ctx *AlterProcedureContext) {}

// ExitAlterProcedure is called when production alterProcedure is exited.
func (s *BaseMariaDBParserListener) ExitAlterProcedure(ctx *AlterProcedureContext) {}

// EnterAlterServer is called when production alterServer is entered.
func (s *BaseMariaDBParserListener) EnterAlterServer(ctx *AlterServerContext) {}

// ExitAlterServer is called when production alterServer is exited.
func (s *BaseMariaDBParserListener) ExitAlterServer(ctx *AlterServerContext) {}

// EnterAlterTable is called when production alterTable is entered.
func (s *BaseMariaDBParserListener) EnterAlterTable(ctx *AlterTableContext) {}

// ExitAlterTable is called when production alterTable is exited.
func (s *BaseMariaDBParserListener) ExitAlterTable(ctx *AlterTableContext) {}

// EnterAlterTablespace is called when production alterTablespace is entered.
func (s *BaseMariaDBParserListener) EnterAlterTablespace(ctx *AlterTablespaceContext) {}

// ExitAlterTablespace is called when production alterTablespace is exited.
func (s *BaseMariaDBParserListener) ExitAlterTablespace(ctx *AlterTablespaceContext) {}

// EnterAlterView is called when production alterView is entered.
func (s *BaseMariaDBParserListener) EnterAlterView(ctx *AlterViewContext) {}

// ExitAlterView is called when production alterView is exited.
func (s *BaseMariaDBParserListener) ExitAlterView(ctx *AlterViewContext) {}

// EnterAlterSequence is called when production alterSequence is entered.
func (s *BaseMariaDBParserListener) EnterAlterSequence(ctx *AlterSequenceContext) {}

// ExitAlterSequence is called when production alterSequence is exited.
func (s *BaseMariaDBParserListener) ExitAlterSequence(ctx *AlterSequenceContext) {}

// EnterAlterByTableOption is called when production alterByTableOption is entered.
func (s *BaseMariaDBParserListener) EnterAlterByTableOption(ctx *AlterByTableOptionContext) {}

// ExitAlterByTableOption is called when production alterByTableOption is exited.
func (s *BaseMariaDBParserListener) ExitAlterByTableOption(ctx *AlterByTableOptionContext) {}

// EnterAlterByAddColumn is called when production alterByAddColumn is entered.
func (s *BaseMariaDBParserListener) EnterAlterByAddColumn(ctx *AlterByAddColumnContext) {}

// ExitAlterByAddColumn is called when production alterByAddColumn is exited.
func (s *BaseMariaDBParserListener) ExitAlterByAddColumn(ctx *AlterByAddColumnContext) {}

// EnterAlterByAddColumns is called when production alterByAddColumns is entered.
func (s *BaseMariaDBParserListener) EnterAlterByAddColumns(ctx *AlterByAddColumnsContext) {}

// ExitAlterByAddColumns is called when production alterByAddColumns is exited.
func (s *BaseMariaDBParserListener) ExitAlterByAddColumns(ctx *AlterByAddColumnsContext) {}

// EnterAlterByAddIndex is called when production alterByAddIndex is entered.
func (s *BaseMariaDBParserListener) EnterAlterByAddIndex(ctx *AlterByAddIndexContext) {}

// ExitAlterByAddIndex is called when production alterByAddIndex is exited.
func (s *BaseMariaDBParserListener) ExitAlterByAddIndex(ctx *AlterByAddIndexContext) {}

// EnterAlterByAddPrimaryKey is called when production alterByAddPrimaryKey is entered.
func (s *BaseMariaDBParserListener) EnterAlterByAddPrimaryKey(ctx *AlterByAddPrimaryKeyContext) {}

// ExitAlterByAddPrimaryKey is called when production alterByAddPrimaryKey is exited.
func (s *BaseMariaDBParserListener) ExitAlterByAddPrimaryKey(ctx *AlterByAddPrimaryKeyContext) {}

// EnterAlterByAddUniqueKey is called when production alterByAddUniqueKey is entered.
func (s *BaseMariaDBParserListener) EnterAlterByAddUniqueKey(ctx *AlterByAddUniqueKeyContext) {}

// ExitAlterByAddUniqueKey is called when production alterByAddUniqueKey is exited.
func (s *BaseMariaDBParserListener) ExitAlterByAddUniqueKey(ctx *AlterByAddUniqueKeyContext) {}

// EnterAlterByAddSpecialIndex is called when production alterByAddSpecialIndex is entered.
func (s *BaseMariaDBParserListener) EnterAlterByAddSpecialIndex(ctx *AlterByAddSpecialIndexContext) {}

// ExitAlterByAddSpecialIndex is called when production alterByAddSpecialIndex is exited.
func (s *BaseMariaDBParserListener) ExitAlterByAddSpecialIndex(ctx *AlterByAddSpecialIndexContext) {}

// EnterAlterByAddForeignKey is called when production alterByAddForeignKey is entered.
func (s *BaseMariaDBParserListener) EnterAlterByAddForeignKey(ctx *AlterByAddForeignKeyContext) {}

// ExitAlterByAddForeignKey is called when production alterByAddForeignKey is exited.
func (s *BaseMariaDBParserListener) ExitAlterByAddForeignKey(ctx *AlterByAddForeignKeyContext) {}

// EnterAlterByAddCheckTableConstraint is called when production alterByAddCheckTableConstraint is entered.
func (s *BaseMariaDBParserListener) EnterAlterByAddCheckTableConstraint(ctx *AlterByAddCheckTableConstraintContext) {
}

// ExitAlterByAddCheckTableConstraint is called when production alterByAddCheckTableConstraint is exited.
func (s *BaseMariaDBParserListener) ExitAlterByAddCheckTableConstraint(ctx *AlterByAddCheckTableConstraintContext) {
}

// EnterAlterBySetAlgorithm is called when production alterBySetAlgorithm is entered.
func (s *BaseMariaDBParserListener) EnterAlterBySetAlgorithm(ctx *AlterBySetAlgorithmContext) {}

// ExitAlterBySetAlgorithm is called when production alterBySetAlgorithm is exited.
func (s *BaseMariaDBParserListener) ExitAlterBySetAlgorithm(ctx *AlterBySetAlgorithmContext) {}

// EnterAlterByChangeDefault is called when production alterByChangeDefault is entered.
func (s *BaseMariaDBParserListener) EnterAlterByChangeDefault(ctx *AlterByChangeDefaultContext) {}

// ExitAlterByChangeDefault is called when production alterByChangeDefault is exited.
func (s *BaseMariaDBParserListener) ExitAlterByChangeDefault(ctx *AlterByChangeDefaultContext) {}

// EnterAlterByChangeColumn is called when production alterByChangeColumn is entered.
func (s *BaseMariaDBParserListener) EnterAlterByChangeColumn(ctx *AlterByChangeColumnContext) {}

// ExitAlterByChangeColumn is called when production alterByChangeColumn is exited.
func (s *BaseMariaDBParserListener) ExitAlterByChangeColumn(ctx *AlterByChangeColumnContext) {}

// EnterAlterByRenameColumn is called when production alterByRenameColumn is entered.
func (s *BaseMariaDBParserListener) EnterAlterByRenameColumn(ctx *AlterByRenameColumnContext) {}

// ExitAlterByRenameColumn is called when production alterByRenameColumn is exited.
func (s *BaseMariaDBParserListener) ExitAlterByRenameColumn(ctx *AlterByRenameColumnContext) {}

// EnterAlterByLock is called when production alterByLock is entered.
func (s *BaseMariaDBParserListener) EnterAlterByLock(ctx *AlterByLockContext) {}

// ExitAlterByLock is called when production alterByLock is exited.
func (s *BaseMariaDBParserListener) ExitAlterByLock(ctx *AlterByLockContext) {}

// EnterAlterByModifyColumn is called when production alterByModifyColumn is entered.
func (s *BaseMariaDBParserListener) EnterAlterByModifyColumn(ctx *AlterByModifyColumnContext) {}

// ExitAlterByModifyColumn is called when production alterByModifyColumn is exited.
func (s *BaseMariaDBParserListener) ExitAlterByModifyColumn(ctx *AlterByModifyColumnContext) {}

// EnterAlterByDropColumn is called when production alterByDropColumn is entered.
func (s *BaseMariaDBParserListener) EnterAlterByDropColumn(ctx *AlterByDropColumnContext) {}

// ExitAlterByDropColumn is called when production alterByDropColumn is exited.
func (s *BaseMariaDBParserListener) ExitAlterByDropColumn(ctx *AlterByDropColumnContext) {}

// EnterAlterByDropConstraintCheck is called when production alterByDropConstraintCheck is entered.
func (s *BaseMariaDBParserListener) EnterAlterByDropConstraintCheck(ctx *AlterByDropConstraintCheckContext) {
}

// ExitAlterByDropConstraintCheck is called when production alterByDropConstraintCheck is exited.
func (s *BaseMariaDBParserListener) ExitAlterByDropConstraintCheck(ctx *AlterByDropConstraintCheckContext) {
}

// EnterAlterByDropPrimaryKey is called when production alterByDropPrimaryKey is entered.
func (s *BaseMariaDBParserListener) EnterAlterByDropPrimaryKey(ctx *AlterByDropPrimaryKeyContext) {}

// ExitAlterByDropPrimaryKey is called when production alterByDropPrimaryKey is exited.
func (s *BaseMariaDBParserListener) ExitAlterByDropPrimaryKey(ctx *AlterByDropPrimaryKeyContext) {}

// EnterAlterByDropIndex is called when production alterByDropIndex is entered.
func (s *BaseMariaDBParserListener) EnterAlterByDropIndex(ctx *AlterByDropIndexContext) {}

// ExitAlterByDropIndex is called when production alterByDropIndex is exited.
func (s *BaseMariaDBParserListener) ExitAlterByDropIndex(ctx *AlterByDropIndexContext) {}

// EnterAlterByRenameIndex is called when production alterByRenameIndex is entered.
func (s *BaseMariaDBParserListener) EnterAlterByRenameIndex(ctx *AlterByRenameIndexContext) {}

// ExitAlterByRenameIndex is called when production alterByRenameIndex is exited.
func (s *BaseMariaDBParserListener) ExitAlterByRenameIndex(ctx *AlterByRenameIndexContext) {}

// EnterAlterByAlterIndexVisibility is called when production alterByAlterIndexVisibility is entered.
func (s *BaseMariaDBParserListener) EnterAlterByAlterIndexVisibility(ctx *AlterByAlterIndexVisibilityContext) {
}

// ExitAlterByAlterIndexVisibility is called when production alterByAlterIndexVisibility is exited.
func (s *BaseMariaDBParserListener) ExitAlterByAlterIndexVisibility(ctx *AlterByAlterIndexVisibilityContext) {
}

// EnterAlterByAlterIndexIgnore is called when production alterByAlterIndexIgnore is entered.
func (s *BaseMariaDBParserListener) EnterAlterByAlterIndexIgnore(ctx *AlterByAlterIndexIgnoreContext) {
}

// ExitAlterByAlterIndexIgnore is called when production alterByAlterIndexIgnore is exited.
func (s *BaseMariaDBParserListener) ExitAlterByAlterIndexIgnore(ctx *AlterByAlterIndexIgnoreContext) {
}

// EnterAlterByDropForeignKey is called when production alterByDropForeignKey is entered.
func (s *BaseMariaDBParserListener) EnterAlterByDropForeignKey(ctx *AlterByDropForeignKeyContext) {}

// ExitAlterByDropForeignKey is called when production alterByDropForeignKey is exited.
func (s *BaseMariaDBParserListener) ExitAlterByDropForeignKey(ctx *AlterByDropForeignKeyContext) {}

// EnterAlterByDisableKeys is called when production alterByDisableKeys is entered.
func (s *BaseMariaDBParserListener) EnterAlterByDisableKeys(ctx *AlterByDisableKeysContext) {}

// ExitAlterByDisableKeys is called when production alterByDisableKeys is exited.
func (s *BaseMariaDBParserListener) ExitAlterByDisableKeys(ctx *AlterByDisableKeysContext) {}

// EnterAlterByEnableKeys is called when production alterByEnableKeys is entered.
func (s *BaseMariaDBParserListener) EnterAlterByEnableKeys(ctx *AlterByEnableKeysContext) {}

// ExitAlterByEnableKeys is called when production alterByEnableKeys is exited.
func (s *BaseMariaDBParserListener) ExitAlterByEnableKeys(ctx *AlterByEnableKeysContext) {}

// EnterAlterByRename is called when production alterByRename is entered.
func (s *BaseMariaDBParserListener) EnterAlterByRename(ctx *AlterByRenameContext) {}

// ExitAlterByRename is called when production alterByRename is exited.
func (s *BaseMariaDBParserListener) ExitAlterByRename(ctx *AlterByRenameContext) {}

// EnterAlterByOrder is called when production alterByOrder is entered.
func (s *BaseMariaDBParserListener) EnterAlterByOrder(ctx *AlterByOrderContext) {}

// ExitAlterByOrder is called when production alterByOrder is exited.
func (s *BaseMariaDBParserListener) ExitAlterByOrder(ctx *AlterByOrderContext) {}

// EnterAlterByConvertCharset is called when production alterByConvertCharset is entered.
func (s *BaseMariaDBParserListener) EnterAlterByConvertCharset(ctx *AlterByConvertCharsetContext) {}

// ExitAlterByConvertCharset is called when production alterByConvertCharset is exited.
func (s *BaseMariaDBParserListener) ExitAlterByConvertCharset(ctx *AlterByConvertCharsetContext) {}

// EnterAlterByDefaultCharset is called when production alterByDefaultCharset is entered.
func (s *BaseMariaDBParserListener) EnterAlterByDefaultCharset(ctx *AlterByDefaultCharsetContext) {}

// ExitAlterByDefaultCharset is called when production alterByDefaultCharset is exited.
func (s *BaseMariaDBParserListener) ExitAlterByDefaultCharset(ctx *AlterByDefaultCharsetContext) {}

// EnterAlterByDiscardTablespace is called when production alterByDiscardTablespace is entered.
func (s *BaseMariaDBParserListener) EnterAlterByDiscardTablespace(ctx *AlterByDiscardTablespaceContext) {
}

// ExitAlterByDiscardTablespace is called when production alterByDiscardTablespace is exited.
func (s *BaseMariaDBParserListener) ExitAlterByDiscardTablespace(ctx *AlterByDiscardTablespaceContext) {
}

// EnterAlterByImportTablespace is called when production alterByImportTablespace is entered.
func (s *BaseMariaDBParserListener) EnterAlterByImportTablespace(ctx *AlterByImportTablespaceContext) {
}

// ExitAlterByImportTablespace is called when production alterByImportTablespace is exited.
func (s *BaseMariaDBParserListener) ExitAlterByImportTablespace(ctx *AlterByImportTablespaceContext) {
}

// EnterAlterByForce is called when production alterByForce is entered.
func (s *BaseMariaDBParserListener) EnterAlterByForce(ctx *AlterByForceContext) {}

// ExitAlterByForce is called when production alterByForce is exited.
func (s *BaseMariaDBParserListener) ExitAlterByForce(ctx *AlterByForceContext) {}

// EnterAlterByValidate is called when production alterByValidate is entered.
func (s *BaseMariaDBParserListener) EnterAlterByValidate(ctx *AlterByValidateContext) {}

// ExitAlterByValidate is called when production alterByValidate is exited.
func (s *BaseMariaDBParserListener) ExitAlterByValidate(ctx *AlterByValidateContext) {}

// EnterAlterByAddDefinitions is called when production alterByAddDefinitions is entered.
func (s *BaseMariaDBParserListener) EnterAlterByAddDefinitions(ctx *AlterByAddDefinitionsContext) {}

// ExitAlterByAddDefinitions is called when production alterByAddDefinitions is exited.
func (s *BaseMariaDBParserListener) ExitAlterByAddDefinitions(ctx *AlterByAddDefinitionsContext) {}

// EnterAlterPartition is called when production alterPartition is entered.
func (s *BaseMariaDBParserListener) EnterAlterPartition(ctx *AlterPartitionContext) {}

// ExitAlterPartition is called when production alterPartition is exited.
func (s *BaseMariaDBParserListener) ExitAlterPartition(ctx *AlterPartitionContext) {}

// EnterAlterByAddPartition is called when production alterByAddPartition is entered.
func (s *BaseMariaDBParserListener) EnterAlterByAddPartition(ctx *AlterByAddPartitionContext) {}

// ExitAlterByAddPartition is called when production alterByAddPartition is exited.
func (s *BaseMariaDBParserListener) ExitAlterByAddPartition(ctx *AlterByAddPartitionContext) {}

// EnterAlterByDropPartition is called when production alterByDropPartition is entered.
func (s *BaseMariaDBParserListener) EnterAlterByDropPartition(ctx *AlterByDropPartitionContext) {}

// ExitAlterByDropPartition is called when production alterByDropPartition is exited.
func (s *BaseMariaDBParserListener) ExitAlterByDropPartition(ctx *AlterByDropPartitionContext) {}

// EnterAlterByDiscardPartition is called when production alterByDiscardPartition is entered.
func (s *BaseMariaDBParserListener) EnterAlterByDiscardPartition(ctx *AlterByDiscardPartitionContext) {
}

// ExitAlterByDiscardPartition is called when production alterByDiscardPartition is exited.
func (s *BaseMariaDBParserListener) ExitAlterByDiscardPartition(ctx *AlterByDiscardPartitionContext) {
}

// EnterAlterByImportPartition is called when production alterByImportPartition is entered.
func (s *BaseMariaDBParserListener) EnterAlterByImportPartition(ctx *AlterByImportPartitionContext) {}

// ExitAlterByImportPartition is called when production alterByImportPartition is exited.
func (s *BaseMariaDBParserListener) ExitAlterByImportPartition(ctx *AlterByImportPartitionContext) {}

// EnterAlterByTruncatePartition is called when production alterByTruncatePartition is entered.
func (s *BaseMariaDBParserListener) EnterAlterByTruncatePartition(ctx *AlterByTruncatePartitionContext) {
}

// ExitAlterByTruncatePartition is called when production alterByTruncatePartition is exited.
func (s *BaseMariaDBParserListener) ExitAlterByTruncatePartition(ctx *AlterByTruncatePartitionContext) {
}

// EnterAlterByCoalescePartition is called when production alterByCoalescePartition is entered.
func (s *BaseMariaDBParserListener) EnterAlterByCoalescePartition(ctx *AlterByCoalescePartitionContext) {
}

// ExitAlterByCoalescePartition is called when production alterByCoalescePartition is exited.
func (s *BaseMariaDBParserListener) ExitAlterByCoalescePartition(ctx *AlterByCoalescePartitionContext) {
}

// EnterAlterByReorganizePartition is called when production alterByReorganizePartition is entered.
func (s *BaseMariaDBParserListener) EnterAlterByReorganizePartition(ctx *AlterByReorganizePartitionContext) {
}

// ExitAlterByReorganizePartition is called when production alterByReorganizePartition is exited.
func (s *BaseMariaDBParserListener) ExitAlterByReorganizePartition(ctx *AlterByReorganizePartitionContext) {
}

// EnterAlterByExchangePartition is called when production alterByExchangePartition is entered.
func (s *BaseMariaDBParserListener) EnterAlterByExchangePartition(ctx *AlterByExchangePartitionContext) {
}

// ExitAlterByExchangePartition is called when production alterByExchangePartition is exited.
func (s *BaseMariaDBParserListener) ExitAlterByExchangePartition(ctx *AlterByExchangePartitionContext) {
}

// EnterAlterByAnalyzePartition is called when production alterByAnalyzePartition is entered.
func (s *BaseMariaDBParserListener) EnterAlterByAnalyzePartition(ctx *AlterByAnalyzePartitionContext) {
}

// ExitAlterByAnalyzePartition is called when production alterByAnalyzePartition is exited.
func (s *BaseMariaDBParserListener) ExitAlterByAnalyzePartition(ctx *AlterByAnalyzePartitionContext) {
}

// EnterAlterByCheckPartition is called when production alterByCheckPartition is entered.
func (s *BaseMariaDBParserListener) EnterAlterByCheckPartition(ctx *AlterByCheckPartitionContext) {}

// ExitAlterByCheckPartition is called when production alterByCheckPartition is exited.
func (s *BaseMariaDBParserListener) ExitAlterByCheckPartition(ctx *AlterByCheckPartitionContext) {}

// EnterAlterByOptimizePartition is called when production alterByOptimizePartition is entered.
func (s *BaseMariaDBParserListener) EnterAlterByOptimizePartition(ctx *AlterByOptimizePartitionContext) {
}

// ExitAlterByOptimizePartition is called when production alterByOptimizePartition is exited.
func (s *BaseMariaDBParserListener) ExitAlterByOptimizePartition(ctx *AlterByOptimizePartitionContext) {
}

// EnterAlterByRebuildPartition is called when production alterByRebuildPartition is entered.
func (s *BaseMariaDBParserListener) EnterAlterByRebuildPartition(ctx *AlterByRebuildPartitionContext) {
}

// ExitAlterByRebuildPartition is called when production alterByRebuildPartition is exited.
func (s *BaseMariaDBParserListener) ExitAlterByRebuildPartition(ctx *AlterByRebuildPartitionContext) {
}

// EnterAlterByRepairPartition is called when production alterByRepairPartition is entered.
func (s *BaseMariaDBParserListener) EnterAlterByRepairPartition(ctx *AlterByRepairPartitionContext) {}

// ExitAlterByRepairPartition is called when production alterByRepairPartition is exited.
func (s *BaseMariaDBParserListener) ExitAlterByRepairPartition(ctx *AlterByRepairPartitionContext) {}

// EnterAlterByRemovePartitioning is called when production alterByRemovePartitioning is entered.
func (s *BaseMariaDBParserListener) EnterAlterByRemovePartitioning(ctx *AlterByRemovePartitioningContext) {
}

// ExitAlterByRemovePartitioning is called when production alterByRemovePartitioning is exited.
func (s *BaseMariaDBParserListener) ExitAlterByRemovePartitioning(ctx *AlterByRemovePartitioningContext) {
}

// EnterAlterByUpgradePartitioning is called when production alterByUpgradePartitioning is entered.
func (s *BaseMariaDBParserListener) EnterAlterByUpgradePartitioning(ctx *AlterByUpgradePartitioningContext) {
}

// ExitAlterByUpgradePartitioning is called when production alterByUpgradePartitioning is exited.
func (s *BaseMariaDBParserListener) ExitAlterByUpgradePartitioning(ctx *AlterByUpgradePartitioningContext) {
}

// EnterDropDatabase is called when production dropDatabase is entered.
func (s *BaseMariaDBParserListener) EnterDropDatabase(ctx *DropDatabaseContext) {}

// ExitDropDatabase is called when production dropDatabase is exited.
func (s *BaseMariaDBParserListener) ExitDropDatabase(ctx *DropDatabaseContext) {}

// EnterDropEvent is called when production dropEvent is entered.
func (s *BaseMariaDBParserListener) EnterDropEvent(ctx *DropEventContext) {}

// ExitDropEvent is called when production dropEvent is exited.
func (s *BaseMariaDBParserListener) ExitDropEvent(ctx *DropEventContext) {}

// EnterDropIndex is called when production dropIndex is entered.
func (s *BaseMariaDBParserListener) EnterDropIndex(ctx *DropIndexContext) {}

// ExitDropIndex is called when production dropIndex is exited.
func (s *BaseMariaDBParserListener) ExitDropIndex(ctx *DropIndexContext) {}

// EnterDropLogfileGroup is called when production dropLogfileGroup is entered.
func (s *BaseMariaDBParserListener) EnterDropLogfileGroup(ctx *DropLogfileGroupContext) {}

// ExitDropLogfileGroup is called when production dropLogfileGroup is exited.
func (s *BaseMariaDBParserListener) ExitDropLogfileGroup(ctx *DropLogfileGroupContext) {}

// EnterDropProcedure is called when production dropProcedure is entered.
func (s *BaseMariaDBParserListener) EnterDropProcedure(ctx *DropProcedureContext) {}

// ExitDropProcedure is called when production dropProcedure is exited.
func (s *BaseMariaDBParserListener) ExitDropProcedure(ctx *DropProcedureContext) {}

// EnterDropFunction is called when production dropFunction is entered.
func (s *BaseMariaDBParserListener) EnterDropFunction(ctx *DropFunctionContext) {}

// ExitDropFunction is called when production dropFunction is exited.
func (s *BaseMariaDBParserListener) ExitDropFunction(ctx *DropFunctionContext) {}

// EnterDropServer is called when production dropServer is entered.
func (s *BaseMariaDBParserListener) EnterDropServer(ctx *DropServerContext) {}

// ExitDropServer is called when production dropServer is exited.
func (s *BaseMariaDBParserListener) ExitDropServer(ctx *DropServerContext) {}

// EnterDropTable is called when production dropTable is entered.
func (s *BaseMariaDBParserListener) EnterDropTable(ctx *DropTableContext) {}

// ExitDropTable is called when production dropTable is exited.
func (s *BaseMariaDBParserListener) ExitDropTable(ctx *DropTableContext) {}

// EnterDropTablespace is called when production dropTablespace is entered.
func (s *BaseMariaDBParserListener) EnterDropTablespace(ctx *DropTablespaceContext) {}

// ExitDropTablespace is called when production dropTablespace is exited.
func (s *BaseMariaDBParserListener) ExitDropTablespace(ctx *DropTablespaceContext) {}

// EnterDropTrigger is called when production dropTrigger is entered.
func (s *BaseMariaDBParserListener) EnterDropTrigger(ctx *DropTriggerContext) {}

// ExitDropTrigger is called when production dropTrigger is exited.
func (s *BaseMariaDBParserListener) ExitDropTrigger(ctx *DropTriggerContext) {}

// EnterDropView is called when production dropView is entered.
func (s *BaseMariaDBParserListener) EnterDropView(ctx *DropViewContext) {}

// ExitDropView is called when production dropView is exited.
func (s *BaseMariaDBParserListener) ExitDropView(ctx *DropViewContext) {}

// EnterDropRole is called when production dropRole is entered.
func (s *BaseMariaDBParserListener) EnterDropRole(ctx *DropRoleContext) {}

// ExitDropRole is called when production dropRole is exited.
func (s *BaseMariaDBParserListener) ExitDropRole(ctx *DropRoleContext) {}

// EnterSetRole is called when production setRole is entered.
func (s *BaseMariaDBParserListener) EnterSetRole(ctx *SetRoleContext) {}

// ExitSetRole is called when production setRole is exited.
func (s *BaseMariaDBParserListener) ExitSetRole(ctx *SetRoleContext) {}

// EnterDropSequence is called when production dropSequence is entered.
func (s *BaseMariaDBParserListener) EnterDropSequence(ctx *DropSequenceContext) {}

// ExitDropSequence is called when production dropSequence is exited.
func (s *BaseMariaDBParserListener) ExitDropSequence(ctx *DropSequenceContext) {}

// EnterRenameTable is called when production renameTable is entered.
func (s *BaseMariaDBParserListener) EnterRenameTable(ctx *RenameTableContext) {}

// ExitRenameTable is called when production renameTable is exited.
func (s *BaseMariaDBParserListener) ExitRenameTable(ctx *RenameTableContext) {}

// EnterRenameTableClause is called when production renameTableClause is entered.
func (s *BaseMariaDBParserListener) EnterRenameTableClause(ctx *RenameTableClauseContext) {}

// ExitRenameTableClause is called when production renameTableClause is exited.
func (s *BaseMariaDBParserListener) ExitRenameTableClause(ctx *RenameTableClauseContext) {}

// EnterTruncateTable is called when production truncateTable is entered.
func (s *BaseMariaDBParserListener) EnterTruncateTable(ctx *TruncateTableContext) {}

// ExitTruncateTable is called when production truncateTable is exited.
func (s *BaseMariaDBParserListener) ExitTruncateTable(ctx *TruncateTableContext) {}

// EnterCallStatement is called when production callStatement is entered.
func (s *BaseMariaDBParserListener) EnterCallStatement(ctx *CallStatementContext) {}

// ExitCallStatement is called when production callStatement is exited.
func (s *BaseMariaDBParserListener) ExitCallStatement(ctx *CallStatementContext) {}

// EnterDeleteStatement is called when production deleteStatement is entered.
func (s *BaseMariaDBParserListener) EnterDeleteStatement(ctx *DeleteStatementContext) {}

// ExitDeleteStatement is called when production deleteStatement is exited.
func (s *BaseMariaDBParserListener) ExitDeleteStatement(ctx *DeleteStatementContext) {}

// EnterDoStatement is called when production doStatement is entered.
func (s *BaseMariaDBParserListener) EnterDoStatement(ctx *DoStatementContext) {}

// ExitDoStatement is called when production doStatement is exited.
func (s *BaseMariaDBParserListener) ExitDoStatement(ctx *DoStatementContext) {}

// EnterHandlerStatement is called when production handlerStatement is entered.
func (s *BaseMariaDBParserListener) EnterHandlerStatement(ctx *HandlerStatementContext) {}

// ExitHandlerStatement is called when production handlerStatement is exited.
func (s *BaseMariaDBParserListener) ExitHandlerStatement(ctx *HandlerStatementContext) {}

// EnterInsertStatement is called when production insertStatement is entered.
func (s *BaseMariaDBParserListener) EnterInsertStatement(ctx *InsertStatementContext) {}

// ExitInsertStatement is called when production insertStatement is exited.
func (s *BaseMariaDBParserListener) ExitInsertStatement(ctx *InsertStatementContext) {}

// EnterLoadDataStatement is called when production loadDataStatement is entered.
func (s *BaseMariaDBParserListener) EnterLoadDataStatement(ctx *LoadDataStatementContext) {}

// ExitLoadDataStatement is called when production loadDataStatement is exited.
func (s *BaseMariaDBParserListener) ExitLoadDataStatement(ctx *LoadDataStatementContext) {}

// EnterLoadXmlStatement is called when production loadXmlStatement is entered.
func (s *BaseMariaDBParserListener) EnterLoadXmlStatement(ctx *LoadXmlStatementContext) {}

// ExitLoadXmlStatement is called when production loadXmlStatement is exited.
func (s *BaseMariaDBParserListener) ExitLoadXmlStatement(ctx *LoadXmlStatementContext) {}

// EnterReplaceStatement is called when production replaceStatement is entered.
func (s *BaseMariaDBParserListener) EnterReplaceStatement(ctx *ReplaceStatementContext) {}

// ExitReplaceStatement is called when production replaceStatement is exited.
func (s *BaseMariaDBParserListener) ExitReplaceStatement(ctx *ReplaceStatementContext) {}

// EnterSimpleSelect is called when production simpleSelect is entered.
func (s *BaseMariaDBParserListener) EnterSimpleSelect(ctx *SimpleSelectContext) {}

// ExitSimpleSelect is called when production simpleSelect is exited.
func (s *BaseMariaDBParserListener) ExitSimpleSelect(ctx *SimpleSelectContext) {}

// EnterParenthesisSelect is called when production parenthesisSelect is entered.
func (s *BaseMariaDBParserListener) EnterParenthesisSelect(ctx *ParenthesisSelectContext) {}

// ExitParenthesisSelect is called when production parenthesisSelect is exited.
func (s *BaseMariaDBParserListener) ExitParenthesisSelect(ctx *ParenthesisSelectContext) {}

// EnterUnionSelect is called when production unionSelect is entered.
func (s *BaseMariaDBParserListener) EnterUnionSelect(ctx *UnionSelectContext) {}

// ExitUnionSelect is called when production unionSelect is exited.
func (s *BaseMariaDBParserListener) ExitUnionSelect(ctx *UnionSelectContext) {}

// EnterUnionParenthesisSelect is called when production unionParenthesisSelect is entered.
func (s *BaseMariaDBParserListener) EnterUnionParenthesisSelect(ctx *UnionParenthesisSelectContext) {}

// ExitUnionParenthesisSelect is called when production unionParenthesisSelect is exited.
func (s *BaseMariaDBParserListener) ExitUnionParenthesisSelect(ctx *UnionParenthesisSelectContext) {}

// EnterWithLateralStatement is called when production withLateralStatement is entered.
func (s *BaseMariaDBParserListener) EnterWithLateralStatement(ctx *WithLateralStatementContext) {}

// ExitWithLateralStatement is called when production withLateralStatement is exited.
func (s *BaseMariaDBParserListener) ExitWithLateralStatement(ctx *WithLateralStatementContext) {}

// EnterUpdateStatement is called when production updateStatement is entered.
func (s *BaseMariaDBParserListener) EnterUpdateStatement(ctx *UpdateStatementContext) {}

// ExitUpdateStatement is called when production updateStatement is exited.
func (s *BaseMariaDBParserListener) ExitUpdateStatement(ctx *UpdateStatementContext) {}

// EnterValuesStatement is called when production valuesStatement is entered.
func (s *BaseMariaDBParserListener) EnterValuesStatement(ctx *ValuesStatementContext) {}

// ExitValuesStatement is called when production valuesStatement is exited.
func (s *BaseMariaDBParserListener) ExitValuesStatement(ctx *ValuesStatementContext) {}

// EnterInsertStatementValue is called when production insertStatementValue is entered.
func (s *BaseMariaDBParserListener) EnterInsertStatementValue(ctx *InsertStatementValueContext) {}

// ExitInsertStatementValue is called when production insertStatementValue is exited.
func (s *BaseMariaDBParserListener) ExitInsertStatementValue(ctx *InsertStatementValueContext) {}

// EnterUpdatedElement is called when production updatedElement is entered.
func (s *BaseMariaDBParserListener) EnterUpdatedElement(ctx *UpdatedElementContext) {}

// ExitUpdatedElement is called when production updatedElement is exited.
func (s *BaseMariaDBParserListener) ExitUpdatedElement(ctx *UpdatedElementContext) {}

// EnterAssignmentField is called when production assignmentField is entered.
func (s *BaseMariaDBParserListener) EnterAssignmentField(ctx *AssignmentFieldContext) {}

// ExitAssignmentField is called when production assignmentField is exited.
func (s *BaseMariaDBParserListener) ExitAssignmentField(ctx *AssignmentFieldContext) {}

// EnterLockClause is called when production lockClause is entered.
func (s *BaseMariaDBParserListener) EnterLockClause(ctx *LockClauseContext) {}

// ExitLockClause is called when production lockClause is exited.
func (s *BaseMariaDBParserListener) ExitLockClause(ctx *LockClauseContext) {}

// EnterSingleDeleteStatement is called when production singleDeleteStatement is entered.
func (s *BaseMariaDBParserListener) EnterSingleDeleteStatement(ctx *SingleDeleteStatementContext) {}

// ExitSingleDeleteStatement is called when production singleDeleteStatement is exited.
func (s *BaseMariaDBParserListener) ExitSingleDeleteStatement(ctx *SingleDeleteStatementContext) {}

// EnterMultipleDeleteStatement is called when production multipleDeleteStatement is entered.
func (s *BaseMariaDBParserListener) EnterMultipleDeleteStatement(ctx *MultipleDeleteStatementContext) {
}

// ExitMultipleDeleteStatement is called when production multipleDeleteStatement is exited.
func (s *BaseMariaDBParserListener) ExitMultipleDeleteStatement(ctx *MultipleDeleteStatementContext) {
}

// EnterHandlerOpenStatement is called when production handlerOpenStatement is entered.
func (s *BaseMariaDBParserListener) EnterHandlerOpenStatement(ctx *HandlerOpenStatementContext) {}

// ExitHandlerOpenStatement is called when production handlerOpenStatement is exited.
func (s *BaseMariaDBParserListener) ExitHandlerOpenStatement(ctx *HandlerOpenStatementContext) {}

// EnterHandlerReadIndexStatement is called when production handlerReadIndexStatement is entered.
func (s *BaseMariaDBParserListener) EnterHandlerReadIndexStatement(ctx *HandlerReadIndexStatementContext) {
}

// ExitHandlerReadIndexStatement is called when production handlerReadIndexStatement is exited.
func (s *BaseMariaDBParserListener) ExitHandlerReadIndexStatement(ctx *HandlerReadIndexStatementContext) {
}

// EnterHandlerReadStatement is called when production handlerReadStatement is entered.
func (s *BaseMariaDBParserListener) EnterHandlerReadStatement(ctx *HandlerReadStatementContext) {}

// ExitHandlerReadStatement is called when production handlerReadStatement is exited.
func (s *BaseMariaDBParserListener) ExitHandlerReadStatement(ctx *HandlerReadStatementContext) {}

// EnterHandlerCloseStatement is called when production handlerCloseStatement is entered.
func (s *BaseMariaDBParserListener) EnterHandlerCloseStatement(ctx *HandlerCloseStatementContext) {}

// ExitHandlerCloseStatement is called when production handlerCloseStatement is exited.
func (s *BaseMariaDBParserListener) ExitHandlerCloseStatement(ctx *HandlerCloseStatementContext) {}

// EnterSingleUpdateStatement is called when production singleUpdateStatement is entered.
func (s *BaseMariaDBParserListener) EnterSingleUpdateStatement(ctx *SingleUpdateStatementContext) {}

// ExitSingleUpdateStatement is called when production singleUpdateStatement is exited.
func (s *BaseMariaDBParserListener) ExitSingleUpdateStatement(ctx *SingleUpdateStatementContext) {}

// EnterMultipleUpdateStatement is called when production multipleUpdateStatement is entered.
func (s *BaseMariaDBParserListener) EnterMultipleUpdateStatement(ctx *MultipleUpdateStatementContext) {
}

// ExitMultipleUpdateStatement is called when production multipleUpdateStatement is exited.
func (s *BaseMariaDBParserListener) ExitMultipleUpdateStatement(ctx *MultipleUpdateStatementContext) {
}

// EnterOrderByClause is called when production orderByClause is entered.
func (s *BaseMariaDBParserListener) EnterOrderByClause(ctx *OrderByClauseContext) {}

// ExitOrderByClause is called when production orderByClause is exited.
func (s *BaseMariaDBParserListener) ExitOrderByClause(ctx *OrderByClauseContext) {}

// EnterOrderByExpression is called when production orderByExpression is entered.
func (s *BaseMariaDBParserListener) EnterOrderByExpression(ctx *OrderByExpressionContext) {}

// ExitOrderByExpression is called when production orderByExpression is exited.
func (s *BaseMariaDBParserListener) ExitOrderByExpression(ctx *OrderByExpressionContext) {}

// EnterTableSources is called when production tableSources is entered.
func (s *BaseMariaDBParserListener) EnterTableSources(ctx *TableSourcesContext) {}

// ExitTableSources is called when production tableSources is exited.
func (s *BaseMariaDBParserListener) ExitTableSources(ctx *TableSourcesContext) {}

// EnterTableSourceBase is called when production tableSourceBase is entered.
func (s *BaseMariaDBParserListener) EnterTableSourceBase(ctx *TableSourceBaseContext) {}

// ExitTableSourceBase is called when production tableSourceBase is exited.
func (s *BaseMariaDBParserListener) ExitTableSourceBase(ctx *TableSourceBaseContext) {}

// EnterTableSourceNested is called when production tableSourceNested is entered.
func (s *BaseMariaDBParserListener) EnterTableSourceNested(ctx *TableSourceNestedContext) {}

// ExitTableSourceNested is called when production tableSourceNested is exited.
func (s *BaseMariaDBParserListener) ExitTableSourceNested(ctx *TableSourceNestedContext) {}

// EnterTableJson is called when production tableJson is entered.
func (s *BaseMariaDBParserListener) EnterTableJson(ctx *TableJsonContext) {}

// ExitTableJson is called when production tableJson is exited.
func (s *BaseMariaDBParserListener) ExitTableJson(ctx *TableJsonContext) {}

// EnterAtomTableItem is called when production atomTableItem is entered.
func (s *BaseMariaDBParserListener) EnterAtomTableItem(ctx *AtomTableItemContext) {}

// ExitAtomTableItem is called when production atomTableItem is exited.
func (s *BaseMariaDBParserListener) ExitAtomTableItem(ctx *AtomTableItemContext) {}

// EnterSubqueryTableItem is called when production subqueryTableItem is entered.
func (s *BaseMariaDBParserListener) EnterSubqueryTableItem(ctx *SubqueryTableItemContext) {}

// ExitSubqueryTableItem is called when production subqueryTableItem is exited.
func (s *BaseMariaDBParserListener) ExitSubqueryTableItem(ctx *SubqueryTableItemContext) {}

// EnterTableSourcesItem is called when production tableSourcesItem is entered.
func (s *BaseMariaDBParserListener) EnterTableSourcesItem(ctx *TableSourcesItemContext) {}

// ExitTableSourcesItem is called when production tableSourcesItem is exited.
func (s *BaseMariaDBParserListener) ExitTableSourcesItem(ctx *TableSourcesItemContext) {}

// EnterIndexHint is called when production indexHint is entered.
func (s *BaseMariaDBParserListener) EnterIndexHint(ctx *IndexHintContext) {}

// ExitIndexHint is called when production indexHint is exited.
func (s *BaseMariaDBParserListener) ExitIndexHint(ctx *IndexHintContext) {}

// EnterIndexHintType is called when production indexHintType is entered.
func (s *BaseMariaDBParserListener) EnterIndexHintType(ctx *IndexHintTypeContext) {}

// ExitIndexHintType is called when production indexHintType is exited.
func (s *BaseMariaDBParserListener) ExitIndexHintType(ctx *IndexHintTypeContext) {}

// EnterInnerJoin is called when production innerJoin is entered.
func (s *BaseMariaDBParserListener) EnterInnerJoin(ctx *InnerJoinContext) {}

// ExitInnerJoin is called when production innerJoin is exited.
func (s *BaseMariaDBParserListener) ExitInnerJoin(ctx *InnerJoinContext) {}

// EnterStraightJoin is called when production straightJoin is entered.
func (s *BaseMariaDBParserListener) EnterStraightJoin(ctx *StraightJoinContext) {}

// ExitStraightJoin is called when production straightJoin is exited.
func (s *BaseMariaDBParserListener) ExitStraightJoin(ctx *StraightJoinContext) {}

// EnterOuterJoin is called when production outerJoin is entered.
func (s *BaseMariaDBParserListener) EnterOuterJoin(ctx *OuterJoinContext) {}

// ExitOuterJoin is called when production outerJoin is exited.
func (s *BaseMariaDBParserListener) ExitOuterJoin(ctx *OuterJoinContext) {}

// EnterNaturalJoin is called when production naturalJoin is entered.
func (s *BaseMariaDBParserListener) EnterNaturalJoin(ctx *NaturalJoinContext) {}

// ExitNaturalJoin is called when production naturalJoin is exited.
func (s *BaseMariaDBParserListener) ExitNaturalJoin(ctx *NaturalJoinContext) {}

// EnterQueryExpression is called when production queryExpression is entered.
func (s *BaseMariaDBParserListener) EnterQueryExpression(ctx *QueryExpressionContext) {}

// ExitQueryExpression is called when production queryExpression is exited.
func (s *BaseMariaDBParserListener) ExitQueryExpression(ctx *QueryExpressionContext) {}

// EnterQueryExpressionNointo is called when production queryExpressionNointo is entered.
func (s *BaseMariaDBParserListener) EnterQueryExpressionNointo(ctx *QueryExpressionNointoContext) {}

// ExitQueryExpressionNointo is called when production queryExpressionNointo is exited.
func (s *BaseMariaDBParserListener) ExitQueryExpressionNointo(ctx *QueryExpressionNointoContext) {}

// EnterQuerySpecification is called when production querySpecification is entered.
func (s *BaseMariaDBParserListener) EnterQuerySpecification(ctx *QuerySpecificationContext) {}

// ExitQuerySpecification is called when production querySpecification is exited.
func (s *BaseMariaDBParserListener) ExitQuerySpecification(ctx *QuerySpecificationContext) {}

// EnterQuerySpecificationNointo is called when production querySpecificationNointo is entered.
func (s *BaseMariaDBParserListener) EnterQuerySpecificationNointo(ctx *QuerySpecificationNointoContext) {
}

// ExitQuerySpecificationNointo is called when production querySpecificationNointo is exited.
func (s *BaseMariaDBParserListener) ExitQuerySpecificationNointo(ctx *QuerySpecificationNointoContext) {
}

// EnterUnionParenthesis is called when production unionParenthesis is entered.
func (s *BaseMariaDBParserListener) EnterUnionParenthesis(ctx *UnionParenthesisContext) {}

// ExitUnionParenthesis is called when production unionParenthesis is exited.
func (s *BaseMariaDBParserListener) ExitUnionParenthesis(ctx *UnionParenthesisContext) {}

// EnterUnionStatement is called when production unionStatement is entered.
func (s *BaseMariaDBParserListener) EnterUnionStatement(ctx *UnionStatementContext) {}

// ExitUnionStatement is called when production unionStatement is exited.
func (s *BaseMariaDBParserListener) ExitUnionStatement(ctx *UnionStatementContext) {}

// EnterLateralStatement is called when production lateralStatement is entered.
func (s *BaseMariaDBParserListener) EnterLateralStatement(ctx *LateralStatementContext) {}

// ExitLateralStatement is called when production lateralStatement is exited.
func (s *BaseMariaDBParserListener) ExitLateralStatement(ctx *LateralStatementContext) {}

// EnterJsonTable is called when production jsonTable is entered.
func (s *BaseMariaDBParserListener) EnterJsonTable(ctx *JsonTableContext) {}

// ExitJsonTable is called when production jsonTable is exited.
func (s *BaseMariaDBParserListener) ExitJsonTable(ctx *JsonTableContext) {}

// EnterJsonColumnList is called when production jsonColumnList is entered.
func (s *BaseMariaDBParserListener) EnterJsonColumnList(ctx *JsonColumnListContext) {}

// ExitJsonColumnList is called when production jsonColumnList is exited.
func (s *BaseMariaDBParserListener) ExitJsonColumnList(ctx *JsonColumnListContext) {}

// EnterJsonColumn is called when production jsonColumn is entered.
func (s *BaseMariaDBParserListener) EnterJsonColumn(ctx *JsonColumnContext) {}

// ExitJsonColumn is called when production jsonColumn is exited.
func (s *BaseMariaDBParserListener) ExitJsonColumn(ctx *JsonColumnContext) {}

// EnterJsonOnEmpty is called when production jsonOnEmpty is entered.
func (s *BaseMariaDBParserListener) EnterJsonOnEmpty(ctx *JsonOnEmptyContext) {}

// ExitJsonOnEmpty is called when production jsonOnEmpty is exited.
func (s *BaseMariaDBParserListener) ExitJsonOnEmpty(ctx *JsonOnEmptyContext) {}

// EnterJsonOnError is called when production jsonOnError is entered.
func (s *BaseMariaDBParserListener) EnterJsonOnError(ctx *JsonOnErrorContext) {}

// ExitJsonOnError is called when production jsonOnError is exited.
func (s *BaseMariaDBParserListener) ExitJsonOnError(ctx *JsonOnErrorContext) {}

// EnterSelectSpec is called when production selectSpec is entered.
func (s *BaseMariaDBParserListener) EnterSelectSpec(ctx *SelectSpecContext) {}

// ExitSelectSpec is called when production selectSpec is exited.
func (s *BaseMariaDBParserListener) ExitSelectSpec(ctx *SelectSpecContext) {}

// EnterSelectElements is called when production selectElements is entered.
func (s *BaseMariaDBParserListener) EnterSelectElements(ctx *SelectElementsContext) {}

// ExitSelectElements is called when production selectElements is exited.
func (s *BaseMariaDBParserListener) ExitSelectElements(ctx *SelectElementsContext) {}

// EnterSelectStarElement is called when production selectStarElement is entered.
func (s *BaseMariaDBParserListener) EnterSelectStarElement(ctx *SelectStarElementContext) {}

// ExitSelectStarElement is called when production selectStarElement is exited.
func (s *BaseMariaDBParserListener) ExitSelectStarElement(ctx *SelectStarElementContext) {}

// EnterSelectColumnElement is called when production selectColumnElement is entered.
func (s *BaseMariaDBParserListener) EnterSelectColumnElement(ctx *SelectColumnElementContext) {}

// ExitSelectColumnElement is called when production selectColumnElement is exited.
func (s *BaseMariaDBParserListener) ExitSelectColumnElement(ctx *SelectColumnElementContext) {}

// EnterSelectFunctionElement is called when production selectFunctionElement is entered.
func (s *BaseMariaDBParserListener) EnterSelectFunctionElement(ctx *SelectFunctionElementContext) {}

// ExitSelectFunctionElement is called when production selectFunctionElement is exited.
func (s *BaseMariaDBParserListener) ExitSelectFunctionElement(ctx *SelectFunctionElementContext) {}

// EnterSelectExpressionElement is called when production selectExpressionElement is entered.
func (s *BaseMariaDBParserListener) EnterSelectExpressionElement(ctx *SelectExpressionElementContext) {
}

// ExitSelectExpressionElement is called when production selectExpressionElement is exited.
func (s *BaseMariaDBParserListener) ExitSelectExpressionElement(ctx *SelectExpressionElementContext) {
}

// EnterSelectIntoVariables is called when production selectIntoVariables is entered.
func (s *BaseMariaDBParserListener) EnterSelectIntoVariables(ctx *SelectIntoVariablesContext) {}

// ExitSelectIntoVariables is called when production selectIntoVariables is exited.
func (s *BaseMariaDBParserListener) ExitSelectIntoVariables(ctx *SelectIntoVariablesContext) {}

// EnterSelectIntoDumpFile is called when production selectIntoDumpFile is entered.
func (s *BaseMariaDBParserListener) EnterSelectIntoDumpFile(ctx *SelectIntoDumpFileContext) {}

// ExitSelectIntoDumpFile is called when production selectIntoDumpFile is exited.
func (s *BaseMariaDBParserListener) ExitSelectIntoDumpFile(ctx *SelectIntoDumpFileContext) {}

// EnterSelectIntoTextFile is called when production selectIntoTextFile is entered.
func (s *BaseMariaDBParserListener) EnterSelectIntoTextFile(ctx *SelectIntoTextFileContext) {}

// ExitSelectIntoTextFile is called when production selectIntoTextFile is exited.
func (s *BaseMariaDBParserListener) ExitSelectIntoTextFile(ctx *SelectIntoTextFileContext) {}

// EnterSelectFieldsInto is called when production selectFieldsInto is entered.
func (s *BaseMariaDBParserListener) EnterSelectFieldsInto(ctx *SelectFieldsIntoContext) {}

// ExitSelectFieldsInto is called when production selectFieldsInto is exited.
func (s *BaseMariaDBParserListener) ExitSelectFieldsInto(ctx *SelectFieldsIntoContext) {}

// EnterSelectLinesInto is called when production selectLinesInto is entered.
func (s *BaseMariaDBParserListener) EnterSelectLinesInto(ctx *SelectLinesIntoContext) {}

// ExitSelectLinesInto is called when production selectLinesInto is exited.
func (s *BaseMariaDBParserListener) ExitSelectLinesInto(ctx *SelectLinesIntoContext) {}

// EnterFromClause is called when production fromClause is entered.
func (s *BaseMariaDBParserListener) EnterFromClause(ctx *FromClauseContext) {}

// ExitFromClause is called when production fromClause is exited.
func (s *BaseMariaDBParserListener) ExitFromClause(ctx *FromClauseContext) {}

// EnterGroupByClause is called when production groupByClause is entered.
func (s *BaseMariaDBParserListener) EnterGroupByClause(ctx *GroupByClauseContext) {}

// ExitGroupByClause is called when production groupByClause is exited.
func (s *BaseMariaDBParserListener) ExitGroupByClause(ctx *GroupByClauseContext) {}

// EnterHavingClause is called when production havingClause is entered.
func (s *BaseMariaDBParserListener) EnterHavingClause(ctx *HavingClauseContext) {}

// ExitHavingClause is called when production havingClause is exited.
func (s *BaseMariaDBParserListener) ExitHavingClause(ctx *HavingClauseContext) {}

// EnterWindowClause is called when production windowClause is entered.
func (s *BaseMariaDBParserListener) EnterWindowClause(ctx *WindowClauseContext) {}

// ExitWindowClause is called when production windowClause is exited.
func (s *BaseMariaDBParserListener) ExitWindowClause(ctx *WindowClauseContext) {}

// EnterGroupByItem is called when production groupByItem is entered.
func (s *BaseMariaDBParserListener) EnterGroupByItem(ctx *GroupByItemContext) {}

// ExitGroupByItem is called when production groupByItem is exited.
func (s *BaseMariaDBParserListener) ExitGroupByItem(ctx *GroupByItemContext) {}

// EnterLimitClause is called when production limitClause is entered.
func (s *BaseMariaDBParserListener) EnterLimitClause(ctx *LimitClauseContext) {}

// ExitLimitClause is called when production limitClause is exited.
func (s *BaseMariaDBParserListener) ExitLimitClause(ctx *LimitClauseContext) {}

// EnterLimitClauseAtom is called when production limitClauseAtom is entered.
func (s *BaseMariaDBParserListener) EnterLimitClauseAtom(ctx *LimitClauseAtomContext) {}

// ExitLimitClauseAtom is called when production limitClauseAtom is exited.
func (s *BaseMariaDBParserListener) ExitLimitClauseAtom(ctx *LimitClauseAtomContext) {}

// EnterStartTransaction is called when production startTransaction is entered.
func (s *BaseMariaDBParserListener) EnterStartTransaction(ctx *StartTransactionContext) {}

// ExitStartTransaction is called when production startTransaction is exited.
func (s *BaseMariaDBParserListener) ExitStartTransaction(ctx *StartTransactionContext) {}

// EnterBeginWork is called when production beginWork is entered.
func (s *BaseMariaDBParserListener) EnterBeginWork(ctx *BeginWorkContext) {}

// ExitBeginWork is called when production beginWork is exited.
func (s *BaseMariaDBParserListener) ExitBeginWork(ctx *BeginWorkContext) {}

// EnterCommitWork is called when production commitWork is entered.
func (s *BaseMariaDBParserListener) EnterCommitWork(ctx *CommitWorkContext) {}

// ExitCommitWork is called when production commitWork is exited.
func (s *BaseMariaDBParserListener) ExitCommitWork(ctx *CommitWorkContext) {}

// EnterRollbackWork is called when production rollbackWork is entered.
func (s *BaseMariaDBParserListener) EnterRollbackWork(ctx *RollbackWorkContext) {}

// ExitRollbackWork is called when production rollbackWork is exited.
func (s *BaseMariaDBParserListener) ExitRollbackWork(ctx *RollbackWorkContext) {}

// EnterSavepointStatement is called when production savepointStatement is entered.
func (s *BaseMariaDBParserListener) EnterSavepointStatement(ctx *SavepointStatementContext) {}

// ExitSavepointStatement is called when production savepointStatement is exited.
func (s *BaseMariaDBParserListener) ExitSavepointStatement(ctx *SavepointStatementContext) {}

// EnterRollbackStatement is called when production rollbackStatement is entered.
func (s *BaseMariaDBParserListener) EnterRollbackStatement(ctx *RollbackStatementContext) {}

// ExitRollbackStatement is called when production rollbackStatement is exited.
func (s *BaseMariaDBParserListener) ExitRollbackStatement(ctx *RollbackStatementContext) {}

// EnterReleaseStatement is called when production releaseStatement is entered.
func (s *BaseMariaDBParserListener) EnterReleaseStatement(ctx *ReleaseStatementContext) {}

// ExitReleaseStatement is called when production releaseStatement is exited.
func (s *BaseMariaDBParserListener) ExitReleaseStatement(ctx *ReleaseStatementContext) {}

// EnterLockTables is called when production lockTables is entered.
func (s *BaseMariaDBParserListener) EnterLockTables(ctx *LockTablesContext) {}

// ExitLockTables is called when production lockTables is exited.
func (s *BaseMariaDBParserListener) ExitLockTables(ctx *LockTablesContext) {}

// EnterUnlockTables is called when production unlockTables is entered.
func (s *BaseMariaDBParserListener) EnterUnlockTables(ctx *UnlockTablesContext) {}

// ExitUnlockTables is called when production unlockTables is exited.
func (s *BaseMariaDBParserListener) ExitUnlockTables(ctx *UnlockTablesContext) {}

// EnterSetAutocommitStatement is called when production setAutocommitStatement is entered.
func (s *BaseMariaDBParserListener) EnterSetAutocommitStatement(ctx *SetAutocommitStatementContext) {}

// ExitSetAutocommitStatement is called when production setAutocommitStatement is exited.
func (s *BaseMariaDBParserListener) ExitSetAutocommitStatement(ctx *SetAutocommitStatementContext) {}

// EnterSetTransactionStatement is called when production setTransactionStatement is entered.
func (s *BaseMariaDBParserListener) EnterSetTransactionStatement(ctx *SetTransactionStatementContext) {
}

// ExitSetTransactionStatement is called when production setTransactionStatement is exited.
func (s *BaseMariaDBParserListener) ExitSetTransactionStatement(ctx *SetTransactionStatementContext) {
}

// EnterTransactionMode is called when production transactionMode is entered.
func (s *BaseMariaDBParserListener) EnterTransactionMode(ctx *TransactionModeContext) {}

// ExitTransactionMode is called when production transactionMode is exited.
func (s *BaseMariaDBParserListener) ExitTransactionMode(ctx *TransactionModeContext) {}

// EnterLockTableElement is called when production lockTableElement is entered.
func (s *BaseMariaDBParserListener) EnterLockTableElement(ctx *LockTableElementContext) {}

// ExitLockTableElement is called when production lockTableElement is exited.
func (s *BaseMariaDBParserListener) ExitLockTableElement(ctx *LockTableElementContext) {}

// EnterLockAction is called when production lockAction is entered.
func (s *BaseMariaDBParserListener) EnterLockAction(ctx *LockActionContext) {}

// ExitLockAction is called when production lockAction is exited.
func (s *BaseMariaDBParserListener) ExitLockAction(ctx *LockActionContext) {}

// EnterTransactionOption is called when production transactionOption is entered.
func (s *BaseMariaDBParserListener) EnterTransactionOption(ctx *TransactionOptionContext) {}

// ExitTransactionOption is called when production transactionOption is exited.
func (s *BaseMariaDBParserListener) ExitTransactionOption(ctx *TransactionOptionContext) {}

// EnterTransactionLevel is called when production transactionLevel is entered.
func (s *BaseMariaDBParserListener) EnterTransactionLevel(ctx *TransactionLevelContext) {}

// ExitTransactionLevel is called when production transactionLevel is exited.
func (s *BaseMariaDBParserListener) ExitTransactionLevel(ctx *TransactionLevelContext) {}

// EnterChangeMaster is called when production changeMaster is entered.
func (s *BaseMariaDBParserListener) EnterChangeMaster(ctx *ChangeMasterContext) {}

// ExitChangeMaster is called when production changeMaster is exited.
func (s *BaseMariaDBParserListener) ExitChangeMaster(ctx *ChangeMasterContext) {}

// EnterChangeReplicationFilter is called when production changeReplicationFilter is entered.
func (s *BaseMariaDBParserListener) EnterChangeReplicationFilter(ctx *ChangeReplicationFilterContext) {
}

// ExitChangeReplicationFilter is called when production changeReplicationFilter is exited.
func (s *BaseMariaDBParserListener) ExitChangeReplicationFilter(ctx *ChangeReplicationFilterContext) {
}

// EnterPurgeBinaryLogs is called when production purgeBinaryLogs is entered.
func (s *BaseMariaDBParserListener) EnterPurgeBinaryLogs(ctx *PurgeBinaryLogsContext) {}

// ExitPurgeBinaryLogs is called when production purgeBinaryLogs is exited.
func (s *BaseMariaDBParserListener) ExitPurgeBinaryLogs(ctx *PurgeBinaryLogsContext) {}

// EnterResetMaster is called when production resetMaster is entered.
func (s *BaseMariaDBParserListener) EnterResetMaster(ctx *ResetMasterContext) {}

// ExitResetMaster is called when production resetMaster is exited.
func (s *BaseMariaDBParserListener) ExitResetMaster(ctx *ResetMasterContext) {}

// EnterResetSlave is called when production resetSlave is entered.
func (s *BaseMariaDBParserListener) EnterResetSlave(ctx *ResetSlaveContext) {}

// ExitResetSlave is called when production resetSlave is exited.
func (s *BaseMariaDBParserListener) ExitResetSlave(ctx *ResetSlaveContext) {}

// EnterStartSlave is called when production startSlave is entered.
func (s *BaseMariaDBParserListener) EnterStartSlave(ctx *StartSlaveContext) {}

// ExitStartSlave is called when production startSlave is exited.
func (s *BaseMariaDBParserListener) ExitStartSlave(ctx *StartSlaveContext) {}

// EnterStopSlave is called when production stopSlave is entered.
func (s *BaseMariaDBParserListener) EnterStopSlave(ctx *StopSlaveContext) {}

// ExitStopSlave is called when production stopSlave is exited.
func (s *BaseMariaDBParserListener) ExitStopSlave(ctx *StopSlaveContext) {}

// EnterStartGroupReplication is called when production startGroupReplication is entered.
func (s *BaseMariaDBParserListener) EnterStartGroupReplication(ctx *StartGroupReplicationContext) {}

// ExitStartGroupReplication is called when production startGroupReplication is exited.
func (s *BaseMariaDBParserListener) ExitStartGroupReplication(ctx *StartGroupReplicationContext) {}

// EnterStopGroupReplication is called when production stopGroupReplication is entered.
func (s *BaseMariaDBParserListener) EnterStopGroupReplication(ctx *StopGroupReplicationContext) {}

// ExitStopGroupReplication is called when production stopGroupReplication is exited.
func (s *BaseMariaDBParserListener) ExitStopGroupReplication(ctx *StopGroupReplicationContext) {}

// EnterMasterStringOption is called when production masterStringOption is entered.
func (s *BaseMariaDBParserListener) EnterMasterStringOption(ctx *MasterStringOptionContext) {}

// ExitMasterStringOption is called when production masterStringOption is exited.
func (s *BaseMariaDBParserListener) ExitMasterStringOption(ctx *MasterStringOptionContext) {}

// EnterMasterDecimalOption is called when production masterDecimalOption is entered.
func (s *BaseMariaDBParserListener) EnterMasterDecimalOption(ctx *MasterDecimalOptionContext) {}

// ExitMasterDecimalOption is called when production masterDecimalOption is exited.
func (s *BaseMariaDBParserListener) ExitMasterDecimalOption(ctx *MasterDecimalOptionContext) {}

// EnterMasterBoolOption is called when production masterBoolOption is entered.
func (s *BaseMariaDBParserListener) EnterMasterBoolOption(ctx *MasterBoolOptionContext) {}

// ExitMasterBoolOption is called when production masterBoolOption is exited.
func (s *BaseMariaDBParserListener) ExitMasterBoolOption(ctx *MasterBoolOptionContext) {}

// EnterMasterRealOption is called when production masterRealOption is entered.
func (s *BaseMariaDBParserListener) EnterMasterRealOption(ctx *MasterRealOptionContext) {}

// ExitMasterRealOption is called when production masterRealOption is exited.
func (s *BaseMariaDBParserListener) ExitMasterRealOption(ctx *MasterRealOptionContext) {}

// EnterMasterUidListOption is called when production masterUidListOption is entered.
func (s *BaseMariaDBParserListener) EnterMasterUidListOption(ctx *MasterUidListOptionContext) {}

// ExitMasterUidListOption is called when production masterUidListOption is exited.
func (s *BaseMariaDBParserListener) ExitMasterUidListOption(ctx *MasterUidListOptionContext) {}

// EnterStringMasterOption is called when production stringMasterOption is entered.
func (s *BaseMariaDBParserListener) EnterStringMasterOption(ctx *StringMasterOptionContext) {}

// ExitStringMasterOption is called when production stringMasterOption is exited.
func (s *BaseMariaDBParserListener) ExitStringMasterOption(ctx *StringMasterOptionContext) {}

// EnterDecimalMasterOption is called when production decimalMasterOption is entered.
func (s *BaseMariaDBParserListener) EnterDecimalMasterOption(ctx *DecimalMasterOptionContext) {}

// ExitDecimalMasterOption is called when production decimalMasterOption is exited.
func (s *BaseMariaDBParserListener) ExitDecimalMasterOption(ctx *DecimalMasterOptionContext) {}

// EnterBoolMasterOption is called when production boolMasterOption is entered.
func (s *BaseMariaDBParserListener) EnterBoolMasterOption(ctx *BoolMasterOptionContext) {}

// ExitBoolMasterOption is called when production boolMasterOption is exited.
func (s *BaseMariaDBParserListener) ExitBoolMasterOption(ctx *BoolMasterOptionContext) {}

// EnterChannelOption is called when production channelOption is entered.
func (s *BaseMariaDBParserListener) EnterChannelOption(ctx *ChannelOptionContext) {}

// ExitChannelOption is called when production channelOption is exited.
func (s *BaseMariaDBParserListener) ExitChannelOption(ctx *ChannelOptionContext) {}

// EnterDoDbReplication is called when production doDbReplication is entered.
func (s *BaseMariaDBParserListener) EnterDoDbReplication(ctx *DoDbReplicationContext) {}

// ExitDoDbReplication is called when production doDbReplication is exited.
func (s *BaseMariaDBParserListener) ExitDoDbReplication(ctx *DoDbReplicationContext) {}

// EnterIgnoreDbReplication is called when production ignoreDbReplication is entered.
func (s *BaseMariaDBParserListener) EnterIgnoreDbReplication(ctx *IgnoreDbReplicationContext) {}

// ExitIgnoreDbReplication is called when production ignoreDbReplication is exited.
func (s *BaseMariaDBParserListener) ExitIgnoreDbReplication(ctx *IgnoreDbReplicationContext) {}

// EnterDoTableReplication is called when production doTableReplication is entered.
func (s *BaseMariaDBParserListener) EnterDoTableReplication(ctx *DoTableReplicationContext) {}

// ExitDoTableReplication is called when production doTableReplication is exited.
func (s *BaseMariaDBParserListener) ExitDoTableReplication(ctx *DoTableReplicationContext) {}

// EnterIgnoreTableReplication is called when production ignoreTableReplication is entered.
func (s *BaseMariaDBParserListener) EnterIgnoreTableReplication(ctx *IgnoreTableReplicationContext) {}

// ExitIgnoreTableReplication is called when production ignoreTableReplication is exited.
func (s *BaseMariaDBParserListener) ExitIgnoreTableReplication(ctx *IgnoreTableReplicationContext) {}

// EnterWildDoTableReplication is called when production wildDoTableReplication is entered.
func (s *BaseMariaDBParserListener) EnterWildDoTableReplication(ctx *WildDoTableReplicationContext) {}

// ExitWildDoTableReplication is called when production wildDoTableReplication is exited.
func (s *BaseMariaDBParserListener) ExitWildDoTableReplication(ctx *WildDoTableReplicationContext) {}

// EnterWildIgnoreTableReplication is called when production wildIgnoreTableReplication is entered.
func (s *BaseMariaDBParserListener) EnterWildIgnoreTableReplication(ctx *WildIgnoreTableReplicationContext) {
}

// ExitWildIgnoreTableReplication is called when production wildIgnoreTableReplication is exited.
func (s *BaseMariaDBParserListener) ExitWildIgnoreTableReplication(ctx *WildIgnoreTableReplicationContext) {
}

// EnterRewriteDbReplication is called when production rewriteDbReplication is entered.
func (s *BaseMariaDBParserListener) EnterRewriteDbReplication(ctx *RewriteDbReplicationContext) {}

// ExitRewriteDbReplication is called when production rewriteDbReplication is exited.
func (s *BaseMariaDBParserListener) ExitRewriteDbReplication(ctx *RewriteDbReplicationContext) {}

// EnterTablePair is called when production tablePair is entered.
func (s *BaseMariaDBParserListener) EnterTablePair(ctx *TablePairContext) {}

// ExitTablePair is called when production tablePair is exited.
func (s *BaseMariaDBParserListener) ExitTablePair(ctx *TablePairContext) {}

// EnterThreadType is called when production threadType is entered.
func (s *BaseMariaDBParserListener) EnterThreadType(ctx *ThreadTypeContext) {}

// ExitThreadType is called when production threadType is exited.
func (s *BaseMariaDBParserListener) ExitThreadType(ctx *ThreadTypeContext) {}

// EnterGtidsUntilOption is called when production gtidsUntilOption is entered.
func (s *BaseMariaDBParserListener) EnterGtidsUntilOption(ctx *GtidsUntilOptionContext) {}

// ExitGtidsUntilOption is called when production gtidsUntilOption is exited.
func (s *BaseMariaDBParserListener) ExitGtidsUntilOption(ctx *GtidsUntilOptionContext) {}

// EnterMasterLogUntilOption is called when production masterLogUntilOption is entered.
func (s *BaseMariaDBParserListener) EnterMasterLogUntilOption(ctx *MasterLogUntilOptionContext) {}

// ExitMasterLogUntilOption is called when production masterLogUntilOption is exited.
func (s *BaseMariaDBParserListener) ExitMasterLogUntilOption(ctx *MasterLogUntilOptionContext) {}

// EnterRelayLogUntilOption is called when production relayLogUntilOption is entered.
func (s *BaseMariaDBParserListener) EnterRelayLogUntilOption(ctx *RelayLogUntilOptionContext) {}

// ExitRelayLogUntilOption is called when production relayLogUntilOption is exited.
func (s *BaseMariaDBParserListener) ExitRelayLogUntilOption(ctx *RelayLogUntilOptionContext) {}

// EnterSqlGapsUntilOption is called when production sqlGapsUntilOption is entered.
func (s *BaseMariaDBParserListener) EnterSqlGapsUntilOption(ctx *SqlGapsUntilOptionContext) {}

// ExitSqlGapsUntilOption is called when production sqlGapsUntilOption is exited.
func (s *BaseMariaDBParserListener) ExitSqlGapsUntilOption(ctx *SqlGapsUntilOptionContext) {}

// EnterUserConnectionOption is called when production userConnectionOption is entered.
func (s *BaseMariaDBParserListener) EnterUserConnectionOption(ctx *UserConnectionOptionContext) {}

// ExitUserConnectionOption is called when production userConnectionOption is exited.
func (s *BaseMariaDBParserListener) ExitUserConnectionOption(ctx *UserConnectionOptionContext) {}

// EnterPasswordConnectionOption is called when production passwordConnectionOption is entered.
func (s *BaseMariaDBParserListener) EnterPasswordConnectionOption(ctx *PasswordConnectionOptionContext) {
}

// ExitPasswordConnectionOption is called when production passwordConnectionOption is exited.
func (s *BaseMariaDBParserListener) ExitPasswordConnectionOption(ctx *PasswordConnectionOptionContext) {
}

// EnterDefaultAuthConnectionOption is called when production defaultAuthConnectionOption is entered.
func (s *BaseMariaDBParserListener) EnterDefaultAuthConnectionOption(ctx *DefaultAuthConnectionOptionContext) {
}

// ExitDefaultAuthConnectionOption is called when production defaultAuthConnectionOption is exited.
func (s *BaseMariaDBParserListener) ExitDefaultAuthConnectionOption(ctx *DefaultAuthConnectionOptionContext) {
}

// EnterPluginDirConnectionOption is called when production pluginDirConnectionOption is entered.
func (s *BaseMariaDBParserListener) EnterPluginDirConnectionOption(ctx *PluginDirConnectionOptionContext) {
}

// ExitPluginDirConnectionOption is called when production pluginDirConnectionOption is exited.
func (s *BaseMariaDBParserListener) ExitPluginDirConnectionOption(ctx *PluginDirConnectionOptionContext) {
}

// EnterGtuidSet is called when production gtuidSet is entered.
func (s *BaseMariaDBParserListener) EnterGtuidSet(ctx *GtuidSetContext) {}

// ExitGtuidSet is called when production gtuidSet is exited.
func (s *BaseMariaDBParserListener) ExitGtuidSet(ctx *GtuidSetContext) {}

// EnterXaStartTransaction is called when production xaStartTransaction is entered.
func (s *BaseMariaDBParserListener) EnterXaStartTransaction(ctx *XaStartTransactionContext) {}

// ExitXaStartTransaction is called when production xaStartTransaction is exited.
func (s *BaseMariaDBParserListener) ExitXaStartTransaction(ctx *XaStartTransactionContext) {}

// EnterXaEndTransaction is called when production xaEndTransaction is entered.
func (s *BaseMariaDBParserListener) EnterXaEndTransaction(ctx *XaEndTransactionContext) {}

// ExitXaEndTransaction is called when production xaEndTransaction is exited.
func (s *BaseMariaDBParserListener) ExitXaEndTransaction(ctx *XaEndTransactionContext) {}

// EnterXaPrepareStatement is called when production xaPrepareStatement is entered.
func (s *BaseMariaDBParserListener) EnterXaPrepareStatement(ctx *XaPrepareStatementContext) {}

// ExitXaPrepareStatement is called when production xaPrepareStatement is exited.
func (s *BaseMariaDBParserListener) ExitXaPrepareStatement(ctx *XaPrepareStatementContext) {}

// EnterXaCommitWork is called when production xaCommitWork is entered.
func (s *BaseMariaDBParserListener) EnterXaCommitWork(ctx *XaCommitWorkContext) {}

// ExitXaCommitWork is called when production xaCommitWork is exited.
func (s *BaseMariaDBParserListener) ExitXaCommitWork(ctx *XaCommitWorkContext) {}

// EnterXaRollbackWork is called when production xaRollbackWork is entered.
func (s *BaseMariaDBParserListener) EnterXaRollbackWork(ctx *XaRollbackWorkContext) {}

// ExitXaRollbackWork is called when production xaRollbackWork is exited.
func (s *BaseMariaDBParserListener) ExitXaRollbackWork(ctx *XaRollbackWorkContext) {}

// EnterXaRecoverWork is called when production xaRecoverWork is entered.
func (s *BaseMariaDBParserListener) EnterXaRecoverWork(ctx *XaRecoverWorkContext) {}

// ExitXaRecoverWork is called when production xaRecoverWork is exited.
func (s *BaseMariaDBParserListener) ExitXaRecoverWork(ctx *XaRecoverWorkContext) {}

// EnterPrepareStatement is called when production prepareStatement is entered.
func (s *BaseMariaDBParserListener) EnterPrepareStatement(ctx *PrepareStatementContext) {}

// ExitPrepareStatement is called when production prepareStatement is exited.
func (s *BaseMariaDBParserListener) ExitPrepareStatement(ctx *PrepareStatementContext) {}

// EnterExecuteStatement is called when production executeStatement is entered.
func (s *BaseMariaDBParserListener) EnterExecuteStatement(ctx *ExecuteStatementContext) {}

// ExitExecuteStatement is called when production executeStatement is exited.
func (s *BaseMariaDBParserListener) ExitExecuteStatement(ctx *ExecuteStatementContext) {}

// EnterDeallocatePrepare is called when production deallocatePrepare is entered.
func (s *BaseMariaDBParserListener) EnterDeallocatePrepare(ctx *DeallocatePrepareContext) {}

// ExitDeallocatePrepare is called when production deallocatePrepare is exited.
func (s *BaseMariaDBParserListener) ExitDeallocatePrepare(ctx *DeallocatePrepareContext) {}

// EnterRoutineBody is called when production routineBody is entered.
func (s *BaseMariaDBParserListener) EnterRoutineBody(ctx *RoutineBodyContext) {}

// ExitRoutineBody is called when production routineBody is exited.
func (s *BaseMariaDBParserListener) ExitRoutineBody(ctx *RoutineBodyContext) {}

// EnterBlockStatement is called when production blockStatement is entered.
func (s *BaseMariaDBParserListener) EnterBlockStatement(ctx *BlockStatementContext) {}

// ExitBlockStatement is called when production blockStatement is exited.
func (s *BaseMariaDBParserListener) ExitBlockStatement(ctx *BlockStatementContext) {}

// EnterCaseStatement is called when production caseStatement is entered.
func (s *BaseMariaDBParserListener) EnterCaseStatement(ctx *CaseStatementContext) {}

// ExitCaseStatement is called when production caseStatement is exited.
func (s *BaseMariaDBParserListener) ExitCaseStatement(ctx *CaseStatementContext) {}

// EnterIfStatement is called when production ifStatement is entered.
func (s *BaseMariaDBParserListener) EnterIfStatement(ctx *IfStatementContext) {}

// ExitIfStatement is called when production ifStatement is exited.
func (s *BaseMariaDBParserListener) ExitIfStatement(ctx *IfStatementContext) {}

// EnterIterateStatement is called when production iterateStatement is entered.
func (s *BaseMariaDBParserListener) EnterIterateStatement(ctx *IterateStatementContext) {}

// ExitIterateStatement is called when production iterateStatement is exited.
func (s *BaseMariaDBParserListener) ExitIterateStatement(ctx *IterateStatementContext) {}

// EnterLeaveStatement is called when production leaveStatement is entered.
func (s *BaseMariaDBParserListener) EnterLeaveStatement(ctx *LeaveStatementContext) {}

// ExitLeaveStatement is called when production leaveStatement is exited.
func (s *BaseMariaDBParserListener) ExitLeaveStatement(ctx *LeaveStatementContext) {}

// EnterLoopStatement is called when production loopStatement is entered.
func (s *BaseMariaDBParserListener) EnterLoopStatement(ctx *LoopStatementContext) {}

// ExitLoopStatement is called when production loopStatement is exited.
func (s *BaseMariaDBParserListener) ExitLoopStatement(ctx *LoopStatementContext) {}

// EnterRepeatStatement is called when production repeatStatement is entered.
func (s *BaseMariaDBParserListener) EnterRepeatStatement(ctx *RepeatStatementContext) {}

// ExitRepeatStatement is called when production repeatStatement is exited.
func (s *BaseMariaDBParserListener) ExitRepeatStatement(ctx *RepeatStatementContext) {}

// EnterReturnStatement is called when production returnStatement is entered.
func (s *BaseMariaDBParserListener) EnterReturnStatement(ctx *ReturnStatementContext) {}

// ExitReturnStatement is called when production returnStatement is exited.
func (s *BaseMariaDBParserListener) ExitReturnStatement(ctx *ReturnStatementContext) {}

// EnterWhileStatement is called when production whileStatement is entered.
func (s *BaseMariaDBParserListener) EnterWhileStatement(ctx *WhileStatementContext) {}

// ExitWhileStatement is called when production whileStatement is exited.
func (s *BaseMariaDBParserListener) ExitWhileStatement(ctx *WhileStatementContext) {}

// EnterCloseCursor is called when production CloseCursor is entered.
func (s *BaseMariaDBParserListener) EnterCloseCursor(ctx *CloseCursorContext) {}

// ExitCloseCursor is called when production CloseCursor is exited.
func (s *BaseMariaDBParserListener) ExitCloseCursor(ctx *CloseCursorContext) {}

// EnterFetchCursor is called when production FetchCursor is entered.
func (s *BaseMariaDBParserListener) EnterFetchCursor(ctx *FetchCursorContext) {}

// ExitFetchCursor is called when production FetchCursor is exited.
func (s *BaseMariaDBParserListener) ExitFetchCursor(ctx *FetchCursorContext) {}

// EnterOpenCursor is called when production OpenCursor is entered.
func (s *BaseMariaDBParserListener) EnterOpenCursor(ctx *OpenCursorContext) {}

// ExitOpenCursor is called when production OpenCursor is exited.
func (s *BaseMariaDBParserListener) ExitOpenCursor(ctx *OpenCursorContext) {}

// EnterDeclareVariable is called when production declareVariable is entered.
func (s *BaseMariaDBParserListener) EnterDeclareVariable(ctx *DeclareVariableContext) {}

// ExitDeclareVariable is called when production declareVariable is exited.
func (s *BaseMariaDBParserListener) ExitDeclareVariable(ctx *DeclareVariableContext) {}

// EnterDeclareCondition is called when production declareCondition is entered.
func (s *BaseMariaDBParserListener) EnterDeclareCondition(ctx *DeclareConditionContext) {}

// ExitDeclareCondition is called when production declareCondition is exited.
func (s *BaseMariaDBParserListener) ExitDeclareCondition(ctx *DeclareConditionContext) {}

// EnterDeclareCursor is called when production declareCursor is entered.
func (s *BaseMariaDBParserListener) EnterDeclareCursor(ctx *DeclareCursorContext) {}

// ExitDeclareCursor is called when production declareCursor is exited.
func (s *BaseMariaDBParserListener) ExitDeclareCursor(ctx *DeclareCursorContext) {}

// EnterDeclareHandler is called when production declareHandler is entered.
func (s *BaseMariaDBParserListener) EnterDeclareHandler(ctx *DeclareHandlerContext) {}

// ExitDeclareHandler is called when production declareHandler is exited.
func (s *BaseMariaDBParserListener) ExitDeclareHandler(ctx *DeclareHandlerContext) {}

// EnterHandlerConditionCode is called when production handlerConditionCode is entered.
func (s *BaseMariaDBParserListener) EnterHandlerConditionCode(ctx *HandlerConditionCodeContext) {}

// ExitHandlerConditionCode is called when production handlerConditionCode is exited.
func (s *BaseMariaDBParserListener) ExitHandlerConditionCode(ctx *HandlerConditionCodeContext) {}

// EnterHandlerConditionState is called when production handlerConditionState is entered.
func (s *BaseMariaDBParserListener) EnterHandlerConditionState(ctx *HandlerConditionStateContext) {}

// ExitHandlerConditionState is called when production handlerConditionState is exited.
func (s *BaseMariaDBParserListener) ExitHandlerConditionState(ctx *HandlerConditionStateContext) {}

// EnterHandlerConditionName is called when production handlerConditionName is entered.
func (s *BaseMariaDBParserListener) EnterHandlerConditionName(ctx *HandlerConditionNameContext) {}

// ExitHandlerConditionName is called when production handlerConditionName is exited.
func (s *BaseMariaDBParserListener) ExitHandlerConditionName(ctx *HandlerConditionNameContext) {}

// EnterHandlerConditionWarning is called when production handlerConditionWarning is entered.
func (s *BaseMariaDBParserListener) EnterHandlerConditionWarning(ctx *HandlerConditionWarningContext) {
}

// ExitHandlerConditionWarning is called when production handlerConditionWarning is exited.
func (s *BaseMariaDBParserListener) ExitHandlerConditionWarning(ctx *HandlerConditionWarningContext) {
}

// EnterHandlerConditionNotfound is called when production handlerConditionNotfound is entered.
func (s *BaseMariaDBParserListener) EnterHandlerConditionNotfound(ctx *HandlerConditionNotfoundContext) {
}

// ExitHandlerConditionNotfound is called when production handlerConditionNotfound is exited.
func (s *BaseMariaDBParserListener) ExitHandlerConditionNotfound(ctx *HandlerConditionNotfoundContext) {
}

// EnterHandlerConditionException is called when production handlerConditionException is entered.
func (s *BaseMariaDBParserListener) EnterHandlerConditionException(ctx *HandlerConditionExceptionContext) {
}

// ExitHandlerConditionException is called when production handlerConditionException is exited.
func (s *BaseMariaDBParserListener) ExitHandlerConditionException(ctx *HandlerConditionExceptionContext) {
}

// EnterProcedureSqlStatement is called when production procedureSqlStatement is entered.
func (s *BaseMariaDBParserListener) EnterProcedureSqlStatement(ctx *ProcedureSqlStatementContext) {}

// ExitProcedureSqlStatement is called when production procedureSqlStatement is exited.
func (s *BaseMariaDBParserListener) ExitProcedureSqlStatement(ctx *ProcedureSqlStatementContext) {}

// EnterCaseAlternative is called when production caseAlternative is entered.
func (s *BaseMariaDBParserListener) EnterCaseAlternative(ctx *CaseAlternativeContext) {}

// ExitCaseAlternative is called when production caseAlternative is exited.
func (s *BaseMariaDBParserListener) ExitCaseAlternative(ctx *CaseAlternativeContext) {}

// EnterElifAlternative is called when production elifAlternative is entered.
func (s *BaseMariaDBParserListener) EnterElifAlternative(ctx *ElifAlternativeContext) {}

// ExitElifAlternative is called when production elifAlternative is exited.
func (s *BaseMariaDBParserListener) ExitElifAlternative(ctx *ElifAlternativeContext) {}

// EnterAlterUserMysqlV56 is called when production alterUserMysqlV56 is entered.
func (s *BaseMariaDBParserListener) EnterAlterUserMysqlV56(ctx *AlterUserMysqlV56Context) {}

// ExitAlterUserMysqlV56 is called when production alterUserMysqlV56 is exited.
func (s *BaseMariaDBParserListener) ExitAlterUserMysqlV56(ctx *AlterUserMysqlV56Context) {}

// EnterAlterUserMysqlV80 is called when production alterUserMysqlV80 is entered.
func (s *BaseMariaDBParserListener) EnterAlterUserMysqlV80(ctx *AlterUserMysqlV80Context) {}

// ExitAlterUserMysqlV80 is called when production alterUserMysqlV80 is exited.
func (s *BaseMariaDBParserListener) ExitAlterUserMysqlV80(ctx *AlterUserMysqlV80Context) {}

// EnterCreateUserMysqlV56 is called when production createUserMysqlV56 is entered.
func (s *BaseMariaDBParserListener) EnterCreateUserMysqlV56(ctx *CreateUserMysqlV56Context) {}

// ExitCreateUserMysqlV56 is called when production createUserMysqlV56 is exited.
func (s *BaseMariaDBParserListener) ExitCreateUserMysqlV56(ctx *CreateUserMysqlV56Context) {}

// EnterCreateUserMysqlV80 is called when production createUserMysqlV80 is entered.
func (s *BaseMariaDBParserListener) EnterCreateUserMysqlV80(ctx *CreateUserMysqlV80Context) {}

// ExitCreateUserMysqlV80 is called when production createUserMysqlV80 is exited.
func (s *BaseMariaDBParserListener) ExitCreateUserMysqlV80(ctx *CreateUserMysqlV80Context) {}

// EnterDropUser is called when production dropUser is entered.
func (s *BaseMariaDBParserListener) EnterDropUser(ctx *DropUserContext) {}

// ExitDropUser is called when production dropUser is exited.
func (s *BaseMariaDBParserListener) ExitDropUser(ctx *DropUserContext) {}

// EnterGrantStatement is called when production grantStatement is entered.
func (s *BaseMariaDBParserListener) EnterGrantStatement(ctx *GrantStatementContext) {}

// ExitGrantStatement is called when production grantStatement is exited.
func (s *BaseMariaDBParserListener) ExitGrantStatement(ctx *GrantStatementContext) {}

// EnterRoleOption is called when production roleOption is entered.
func (s *BaseMariaDBParserListener) EnterRoleOption(ctx *RoleOptionContext) {}

// ExitRoleOption is called when production roleOption is exited.
func (s *BaseMariaDBParserListener) ExitRoleOption(ctx *RoleOptionContext) {}

// EnterGrantProxy is called when production grantProxy is entered.
func (s *BaseMariaDBParserListener) EnterGrantProxy(ctx *GrantProxyContext) {}

// ExitGrantProxy is called when production grantProxy is exited.
func (s *BaseMariaDBParserListener) ExitGrantProxy(ctx *GrantProxyContext) {}

// EnterRenameUser is called when production renameUser is entered.
func (s *BaseMariaDBParserListener) EnterRenameUser(ctx *RenameUserContext) {}

// ExitRenameUser is called when production renameUser is exited.
func (s *BaseMariaDBParserListener) ExitRenameUser(ctx *RenameUserContext) {}

// EnterDetailRevoke is called when production detailRevoke is entered.
func (s *BaseMariaDBParserListener) EnterDetailRevoke(ctx *DetailRevokeContext) {}

// ExitDetailRevoke is called when production detailRevoke is exited.
func (s *BaseMariaDBParserListener) ExitDetailRevoke(ctx *DetailRevokeContext) {}

// EnterShortRevoke is called when production shortRevoke is entered.
func (s *BaseMariaDBParserListener) EnterShortRevoke(ctx *ShortRevokeContext) {}

// ExitShortRevoke is called when production shortRevoke is exited.
func (s *BaseMariaDBParserListener) ExitShortRevoke(ctx *ShortRevokeContext) {}

// EnterRoleRevoke is called when production roleRevoke is entered.
func (s *BaseMariaDBParserListener) EnterRoleRevoke(ctx *RoleRevokeContext) {}

// ExitRoleRevoke is called when production roleRevoke is exited.
func (s *BaseMariaDBParserListener) ExitRoleRevoke(ctx *RoleRevokeContext) {}

// EnterRevokeProxy is called when production revokeProxy is entered.
func (s *BaseMariaDBParserListener) EnterRevokeProxy(ctx *RevokeProxyContext) {}

// ExitRevokeProxy is called when production revokeProxy is exited.
func (s *BaseMariaDBParserListener) ExitRevokeProxy(ctx *RevokeProxyContext) {}

// EnterSetPasswordStatement is called when production setPasswordStatement is entered.
func (s *BaseMariaDBParserListener) EnterSetPasswordStatement(ctx *SetPasswordStatementContext) {}

// ExitSetPasswordStatement is called when production setPasswordStatement is exited.
func (s *BaseMariaDBParserListener) ExitSetPasswordStatement(ctx *SetPasswordStatementContext) {}

// EnterUserSpecification is called when production userSpecification is entered.
func (s *BaseMariaDBParserListener) EnterUserSpecification(ctx *UserSpecificationContext) {}

// ExitUserSpecification is called when production userSpecification is exited.
func (s *BaseMariaDBParserListener) ExitUserSpecification(ctx *UserSpecificationContext) {}

// EnterHashAuthOption is called when production hashAuthOption is entered.
func (s *BaseMariaDBParserListener) EnterHashAuthOption(ctx *HashAuthOptionContext) {}

// ExitHashAuthOption is called when production hashAuthOption is exited.
func (s *BaseMariaDBParserListener) ExitHashAuthOption(ctx *HashAuthOptionContext) {}

// EnterStringAuthOption is called when production stringAuthOption is entered.
func (s *BaseMariaDBParserListener) EnterStringAuthOption(ctx *StringAuthOptionContext) {}

// ExitStringAuthOption is called when production stringAuthOption is exited.
func (s *BaseMariaDBParserListener) ExitStringAuthOption(ctx *StringAuthOptionContext) {}

// EnterModuleAuthOption is called when production moduleAuthOption is entered.
func (s *BaseMariaDBParserListener) EnterModuleAuthOption(ctx *ModuleAuthOptionContext) {}

// ExitModuleAuthOption is called when production moduleAuthOption is exited.
func (s *BaseMariaDBParserListener) ExitModuleAuthOption(ctx *ModuleAuthOptionContext) {}

// EnterSimpleAuthOption is called when production simpleAuthOption is entered.
func (s *BaseMariaDBParserListener) EnterSimpleAuthOption(ctx *SimpleAuthOptionContext) {}

// ExitSimpleAuthOption is called when production simpleAuthOption is exited.
func (s *BaseMariaDBParserListener) ExitSimpleAuthOption(ctx *SimpleAuthOptionContext) {}

// EnterModule is called when production module is entered.
func (s *BaseMariaDBParserListener) EnterModule(ctx *ModuleContext) {}

// ExitModule is called when production module is exited.
func (s *BaseMariaDBParserListener) ExitModule(ctx *ModuleContext) {}

// EnterPasswordModuleOption is called when production passwordModuleOption is entered.
func (s *BaseMariaDBParserListener) EnterPasswordModuleOption(ctx *PasswordModuleOptionContext) {}

// ExitPasswordModuleOption is called when production passwordModuleOption is exited.
func (s *BaseMariaDBParserListener) ExitPasswordModuleOption(ctx *PasswordModuleOptionContext) {}

// EnterTlsOption is called when production tlsOption is entered.
func (s *BaseMariaDBParserListener) EnterTlsOption(ctx *TlsOptionContext) {}

// ExitTlsOption is called when production tlsOption is exited.
func (s *BaseMariaDBParserListener) ExitTlsOption(ctx *TlsOptionContext) {}

// EnterUserResourceOption is called when production userResourceOption is entered.
func (s *BaseMariaDBParserListener) EnterUserResourceOption(ctx *UserResourceOptionContext) {}

// ExitUserResourceOption is called when production userResourceOption is exited.
func (s *BaseMariaDBParserListener) ExitUserResourceOption(ctx *UserResourceOptionContext) {}

// EnterUserPasswordOption is called when production userPasswordOption is entered.
func (s *BaseMariaDBParserListener) EnterUserPasswordOption(ctx *UserPasswordOptionContext) {}

// ExitUserPasswordOption is called when production userPasswordOption is exited.
func (s *BaseMariaDBParserListener) ExitUserPasswordOption(ctx *UserPasswordOptionContext) {}

// EnterUserLockOption is called when production userLockOption is entered.
func (s *BaseMariaDBParserListener) EnterUserLockOption(ctx *UserLockOptionContext) {}

// ExitUserLockOption is called when production userLockOption is exited.
func (s *BaseMariaDBParserListener) ExitUserLockOption(ctx *UserLockOptionContext) {}

// EnterPrivelegeClause is called when production privelegeClause is entered.
func (s *BaseMariaDBParserListener) EnterPrivelegeClause(ctx *PrivelegeClauseContext) {}

// ExitPrivelegeClause is called when production privelegeClause is exited.
func (s *BaseMariaDBParserListener) ExitPrivelegeClause(ctx *PrivelegeClauseContext) {}

// EnterPrivilege is called when production privilege is entered.
func (s *BaseMariaDBParserListener) EnterPrivilege(ctx *PrivilegeContext) {}

// ExitPrivilege is called when production privilege is exited.
func (s *BaseMariaDBParserListener) ExitPrivilege(ctx *PrivilegeContext) {}

// EnterCurrentSchemaPriviLevel is called when production currentSchemaPriviLevel is entered.
func (s *BaseMariaDBParserListener) EnterCurrentSchemaPriviLevel(ctx *CurrentSchemaPriviLevelContext) {
}

// ExitCurrentSchemaPriviLevel is called when production currentSchemaPriviLevel is exited.
func (s *BaseMariaDBParserListener) ExitCurrentSchemaPriviLevel(ctx *CurrentSchemaPriviLevelContext) {
}

// EnterGlobalPrivLevel is called when production globalPrivLevel is entered.
func (s *BaseMariaDBParserListener) EnterGlobalPrivLevel(ctx *GlobalPrivLevelContext) {}

// ExitGlobalPrivLevel is called when production globalPrivLevel is exited.
func (s *BaseMariaDBParserListener) ExitGlobalPrivLevel(ctx *GlobalPrivLevelContext) {}

// EnterDefiniteSchemaPrivLevel is called when production definiteSchemaPrivLevel is entered.
func (s *BaseMariaDBParserListener) EnterDefiniteSchemaPrivLevel(ctx *DefiniteSchemaPrivLevelContext) {
}

// ExitDefiniteSchemaPrivLevel is called when production definiteSchemaPrivLevel is exited.
func (s *BaseMariaDBParserListener) ExitDefiniteSchemaPrivLevel(ctx *DefiniteSchemaPrivLevelContext) {
}

// EnterDefiniteFullTablePrivLevel is called when production definiteFullTablePrivLevel is entered.
func (s *BaseMariaDBParserListener) EnterDefiniteFullTablePrivLevel(ctx *DefiniteFullTablePrivLevelContext) {
}

// ExitDefiniteFullTablePrivLevel is called when production definiteFullTablePrivLevel is exited.
func (s *BaseMariaDBParserListener) ExitDefiniteFullTablePrivLevel(ctx *DefiniteFullTablePrivLevelContext) {
}

// EnterDefiniteFullTablePrivLevel2 is called when production definiteFullTablePrivLevel2 is entered.
func (s *BaseMariaDBParserListener) EnterDefiniteFullTablePrivLevel2(ctx *DefiniteFullTablePrivLevel2Context) {
}

// ExitDefiniteFullTablePrivLevel2 is called when production definiteFullTablePrivLevel2 is exited.
func (s *BaseMariaDBParserListener) ExitDefiniteFullTablePrivLevel2(ctx *DefiniteFullTablePrivLevel2Context) {
}

// EnterDefiniteTablePrivLevel is called when production definiteTablePrivLevel is entered.
func (s *BaseMariaDBParserListener) EnterDefiniteTablePrivLevel(ctx *DefiniteTablePrivLevelContext) {}

// ExitDefiniteTablePrivLevel is called when production definiteTablePrivLevel is exited.
func (s *BaseMariaDBParserListener) ExitDefiniteTablePrivLevel(ctx *DefiniteTablePrivLevelContext) {}

// EnterRenameUserClause is called when production renameUserClause is entered.
func (s *BaseMariaDBParserListener) EnterRenameUserClause(ctx *RenameUserClauseContext) {}

// ExitRenameUserClause is called when production renameUserClause is exited.
func (s *BaseMariaDBParserListener) ExitRenameUserClause(ctx *RenameUserClauseContext) {}

// EnterAnalyzeTable is called when production analyzeTable is entered.
func (s *BaseMariaDBParserListener) EnterAnalyzeTable(ctx *AnalyzeTableContext) {}

// ExitAnalyzeTable is called when production analyzeTable is exited.
func (s *BaseMariaDBParserListener) ExitAnalyzeTable(ctx *AnalyzeTableContext) {}

// EnterCheckTable is called when production checkTable is entered.
func (s *BaseMariaDBParserListener) EnterCheckTable(ctx *CheckTableContext) {}

// ExitCheckTable is called when production checkTable is exited.
func (s *BaseMariaDBParserListener) ExitCheckTable(ctx *CheckTableContext) {}

// EnterChecksumTable is called when production checksumTable is entered.
func (s *BaseMariaDBParserListener) EnterChecksumTable(ctx *ChecksumTableContext) {}

// ExitChecksumTable is called when production checksumTable is exited.
func (s *BaseMariaDBParserListener) ExitChecksumTable(ctx *ChecksumTableContext) {}

// EnterOptimizeTable is called when production optimizeTable is entered.
func (s *BaseMariaDBParserListener) EnterOptimizeTable(ctx *OptimizeTableContext) {}

// ExitOptimizeTable is called when production optimizeTable is exited.
func (s *BaseMariaDBParserListener) ExitOptimizeTable(ctx *OptimizeTableContext) {}

// EnterRepairTable is called when production repairTable is entered.
func (s *BaseMariaDBParserListener) EnterRepairTable(ctx *RepairTableContext) {}

// ExitRepairTable is called when production repairTable is exited.
func (s *BaseMariaDBParserListener) ExitRepairTable(ctx *RepairTableContext) {}

// EnterCheckTableOption is called when production checkTableOption is entered.
func (s *BaseMariaDBParserListener) EnterCheckTableOption(ctx *CheckTableOptionContext) {}

// ExitCheckTableOption is called when production checkTableOption is exited.
func (s *BaseMariaDBParserListener) ExitCheckTableOption(ctx *CheckTableOptionContext) {}

// EnterCreateUdfunction is called when production createUdfunction is entered.
func (s *BaseMariaDBParserListener) EnterCreateUdfunction(ctx *CreateUdfunctionContext) {}

// ExitCreateUdfunction is called when production createUdfunction is exited.
func (s *BaseMariaDBParserListener) ExitCreateUdfunction(ctx *CreateUdfunctionContext) {}

// EnterInstallPlugin is called when production installPlugin is entered.
func (s *BaseMariaDBParserListener) EnterInstallPlugin(ctx *InstallPluginContext) {}

// ExitInstallPlugin is called when production installPlugin is exited.
func (s *BaseMariaDBParserListener) ExitInstallPlugin(ctx *InstallPluginContext) {}

// EnterUninstallPlugin is called when production uninstallPlugin is entered.
func (s *BaseMariaDBParserListener) EnterUninstallPlugin(ctx *UninstallPluginContext) {}

// ExitUninstallPlugin is called when production uninstallPlugin is exited.
func (s *BaseMariaDBParserListener) ExitUninstallPlugin(ctx *UninstallPluginContext) {}

// EnterSetVariable is called when production setVariable is entered.
func (s *BaseMariaDBParserListener) EnterSetVariable(ctx *SetVariableContext) {}

// ExitSetVariable is called when production setVariable is exited.
func (s *BaseMariaDBParserListener) ExitSetVariable(ctx *SetVariableContext) {}

// EnterSetCharset is called when production setCharset is entered.
func (s *BaseMariaDBParserListener) EnterSetCharset(ctx *SetCharsetContext) {}

// ExitSetCharset is called when production setCharset is exited.
func (s *BaseMariaDBParserListener) ExitSetCharset(ctx *SetCharsetContext) {}

// EnterSetNames is called when production setNames is entered.
func (s *BaseMariaDBParserListener) EnterSetNames(ctx *SetNamesContext) {}

// ExitSetNames is called when production setNames is exited.
func (s *BaseMariaDBParserListener) ExitSetNames(ctx *SetNamesContext) {}

// EnterSetPassword is called when production setPassword is entered.
func (s *BaseMariaDBParserListener) EnterSetPassword(ctx *SetPasswordContext) {}

// ExitSetPassword is called when production setPassword is exited.
func (s *BaseMariaDBParserListener) ExitSetPassword(ctx *SetPasswordContext) {}

// EnterSetTransaction is called when production setTransaction is entered.
func (s *BaseMariaDBParserListener) EnterSetTransaction(ctx *SetTransactionContext) {}

// ExitSetTransaction is called when production setTransaction is exited.
func (s *BaseMariaDBParserListener) ExitSetTransaction(ctx *SetTransactionContext) {}

// EnterSetAutocommit is called when production setAutocommit is entered.
func (s *BaseMariaDBParserListener) EnterSetAutocommit(ctx *SetAutocommitContext) {}

// ExitSetAutocommit is called when production setAutocommit is exited.
func (s *BaseMariaDBParserListener) ExitSetAutocommit(ctx *SetAutocommitContext) {}

// EnterSetNewValueInsideTrigger is called when production setNewValueInsideTrigger is entered.
func (s *BaseMariaDBParserListener) EnterSetNewValueInsideTrigger(ctx *SetNewValueInsideTriggerContext) {
}

// ExitSetNewValueInsideTrigger is called when production setNewValueInsideTrigger is exited.
func (s *BaseMariaDBParserListener) ExitSetNewValueInsideTrigger(ctx *SetNewValueInsideTriggerContext) {
}

// EnterShowMasterLogs is called when production showMasterLogs is entered.
func (s *BaseMariaDBParserListener) EnterShowMasterLogs(ctx *ShowMasterLogsContext) {}

// ExitShowMasterLogs is called when production showMasterLogs is exited.
func (s *BaseMariaDBParserListener) ExitShowMasterLogs(ctx *ShowMasterLogsContext) {}

// EnterShowBinLogEvents is called when production showBinLogEvents is entered.
func (s *BaseMariaDBParserListener) EnterShowBinLogEvents(ctx *ShowBinLogEventsContext) {}

// ExitShowBinLogEvents is called when production showBinLogEvents is exited.
func (s *BaseMariaDBParserListener) ExitShowBinLogEvents(ctx *ShowBinLogEventsContext) {}

// EnterShowRelayLogEvents is called when production showRelayLogEvents is entered.
func (s *BaseMariaDBParserListener) EnterShowRelayLogEvents(ctx *ShowRelayLogEventsContext) {}

// ExitShowRelayLogEvents is called when production showRelayLogEvents is exited.
func (s *BaseMariaDBParserListener) ExitShowRelayLogEvents(ctx *ShowRelayLogEventsContext) {}

// EnterShowObjectFilter is called when production showObjectFilter is entered.
func (s *BaseMariaDBParserListener) EnterShowObjectFilter(ctx *ShowObjectFilterContext) {}

// ExitShowObjectFilter is called when production showObjectFilter is exited.
func (s *BaseMariaDBParserListener) ExitShowObjectFilter(ctx *ShowObjectFilterContext) {}

// EnterShowColumns is called when production showColumns is entered.
func (s *BaseMariaDBParserListener) EnterShowColumns(ctx *ShowColumnsContext) {}

// ExitShowColumns is called when production showColumns is exited.
func (s *BaseMariaDBParserListener) ExitShowColumns(ctx *ShowColumnsContext) {}

// EnterShowCreateDb is called when production showCreateDb is entered.
func (s *BaseMariaDBParserListener) EnterShowCreateDb(ctx *ShowCreateDbContext) {}

// ExitShowCreateDb is called when production showCreateDb is exited.
func (s *BaseMariaDBParserListener) ExitShowCreateDb(ctx *ShowCreateDbContext) {}

// EnterShowCreateFullIdObject is called when production showCreateFullIdObject is entered.
func (s *BaseMariaDBParserListener) EnterShowCreateFullIdObject(ctx *ShowCreateFullIdObjectContext) {}

// ExitShowCreateFullIdObject is called when production showCreateFullIdObject is exited.
func (s *BaseMariaDBParserListener) ExitShowCreateFullIdObject(ctx *ShowCreateFullIdObjectContext) {}

// EnterShowCreatePackage is called when production showCreatePackage is entered.
func (s *BaseMariaDBParserListener) EnterShowCreatePackage(ctx *ShowCreatePackageContext) {}

// ExitShowCreatePackage is called when production showCreatePackage is exited.
func (s *BaseMariaDBParserListener) ExitShowCreatePackage(ctx *ShowCreatePackageContext) {}

// EnterShowCreateUser is called when production showCreateUser is entered.
func (s *BaseMariaDBParserListener) EnterShowCreateUser(ctx *ShowCreateUserContext) {}

// ExitShowCreateUser is called when production showCreateUser is exited.
func (s *BaseMariaDBParserListener) ExitShowCreateUser(ctx *ShowCreateUserContext) {}

// EnterShowEngine is called when production showEngine is entered.
func (s *BaseMariaDBParserListener) EnterShowEngine(ctx *ShowEngineContext) {}

// ExitShowEngine is called when production showEngine is exited.
func (s *BaseMariaDBParserListener) ExitShowEngine(ctx *ShowEngineContext) {}

// EnterShowInnoDBStatus is called when production showInnoDBStatus is entered.
func (s *BaseMariaDBParserListener) EnterShowInnoDBStatus(ctx *ShowInnoDBStatusContext) {}

// ExitShowInnoDBStatus is called when production showInnoDBStatus is exited.
func (s *BaseMariaDBParserListener) ExitShowInnoDBStatus(ctx *ShowInnoDBStatusContext) {}

// EnterShowGlobalInfo is called when production showGlobalInfo is entered.
func (s *BaseMariaDBParserListener) EnterShowGlobalInfo(ctx *ShowGlobalInfoContext) {}

// ExitShowGlobalInfo is called when production showGlobalInfo is exited.
func (s *BaseMariaDBParserListener) ExitShowGlobalInfo(ctx *ShowGlobalInfoContext) {}

// EnterShowErrors is called when production showErrors is entered.
func (s *BaseMariaDBParserListener) EnterShowErrors(ctx *ShowErrorsContext) {}

// ExitShowErrors is called when production showErrors is exited.
func (s *BaseMariaDBParserListener) ExitShowErrors(ctx *ShowErrorsContext) {}

// EnterShowCountErrors is called when production showCountErrors is entered.
func (s *BaseMariaDBParserListener) EnterShowCountErrors(ctx *ShowCountErrorsContext) {}

// ExitShowCountErrors is called when production showCountErrors is exited.
func (s *BaseMariaDBParserListener) ExitShowCountErrors(ctx *ShowCountErrorsContext) {}

// EnterShowSchemaFilter is called when production showSchemaFilter is entered.
func (s *BaseMariaDBParserListener) EnterShowSchemaFilter(ctx *ShowSchemaFilterContext) {}

// ExitShowSchemaFilter is called when production showSchemaFilter is exited.
func (s *BaseMariaDBParserListener) ExitShowSchemaFilter(ctx *ShowSchemaFilterContext) {}

// EnterShowRoutine is called when production showRoutine is entered.
func (s *BaseMariaDBParserListener) EnterShowRoutine(ctx *ShowRoutineContext) {}

// ExitShowRoutine is called when production showRoutine is exited.
func (s *BaseMariaDBParserListener) ExitShowRoutine(ctx *ShowRoutineContext) {}

// EnterShowGrants is called when production showGrants is entered.
func (s *BaseMariaDBParserListener) EnterShowGrants(ctx *ShowGrantsContext) {}

// ExitShowGrants is called when production showGrants is exited.
func (s *BaseMariaDBParserListener) ExitShowGrants(ctx *ShowGrantsContext) {}

// EnterShowIndexes is called when production showIndexes is entered.
func (s *BaseMariaDBParserListener) EnterShowIndexes(ctx *ShowIndexesContext) {}

// ExitShowIndexes is called when production showIndexes is exited.
func (s *BaseMariaDBParserListener) ExitShowIndexes(ctx *ShowIndexesContext) {}

// EnterShowOpenTables is called when production showOpenTables is entered.
func (s *BaseMariaDBParserListener) EnterShowOpenTables(ctx *ShowOpenTablesContext) {}

// ExitShowOpenTables is called when production showOpenTables is exited.
func (s *BaseMariaDBParserListener) ExitShowOpenTables(ctx *ShowOpenTablesContext) {}

// EnterShowProfile is called when production showProfile is entered.
func (s *BaseMariaDBParserListener) EnterShowProfile(ctx *ShowProfileContext) {}

// ExitShowProfile is called when production showProfile is exited.
func (s *BaseMariaDBParserListener) ExitShowProfile(ctx *ShowProfileContext) {}

// EnterShowSlaveStatus is called when production showSlaveStatus is entered.
func (s *BaseMariaDBParserListener) EnterShowSlaveStatus(ctx *ShowSlaveStatusContext) {}

// ExitShowSlaveStatus is called when production showSlaveStatus is exited.
func (s *BaseMariaDBParserListener) ExitShowSlaveStatus(ctx *ShowSlaveStatusContext) {}

// EnterShowUserstatPlugin is called when production showUserstatPlugin is entered.
func (s *BaseMariaDBParserListener) EnterShowUserstatPlugin(ctx *ShowUserstatPluginContext) {}

// ExitShowUserstatPlugin is called when production showUserstatPlugin is exited.
func (s *BaseMariaDBParserListener) ExitShowUserstatPlugin(ctx *ShowUserstatPluginContext) {}

// EnterShowExplain is called when production showExplain is entered.
func (s *BaseMariaDBParserListener) EnterShowExplain(ctx *ShowExplainContext) {}

// ExitShowExplain is called when production showExplain is exited.
func (s *BaseMariaDBParserListener) ExitShowExplain(ctx *ShowExplainContext) {}

// EnterShowPackageStatus is called when production showPackageStatus is entered.
func (s *BaseMariaDBParserListener) EnterShowPackageStatus(ctx *ShowPackageStatusContext) {}

// ExitShowPackageStatus is called when production showPackageStatus is exited.
func (s *BaseMariaDBParserListener) ExitShowPackageStatus(ctx *ShowPackageStatusContext) {}

// EnterExplainForConnection is called when production explainForConnection is entered.
func (s *BaseMariaDBParserListener) EnterExplainForConnection(ctx *ExplainForConnectionContext) {}

// ExitExplainForConnection is called when production explainForConnection is exited.
func (s *BaseMariaDBParserListener) ExitExplainForConnection(ctx *ExplainForConnectionContext) {}

// EnterVariableClause is called when production variableClause is entered.
func (s *BaseMariaDBParserListener) EnterVariableClause(ctx *VariableClauseContext) {}

// ExitVariableClause is called when production variableClause is exited.
func (s *BaseMariaDBParserListener) ExitVariableClause(ctx *VariableClauseContext) {}

// EnterShowCommonEntity is called when production showCommonEntity is entered.
func (s *BaseMariaDBParserListener) EnterShowCommonEntity(ctx *ShowCommonEntityContext) {}

// ExitShowCommonEntity is called when production showCommonEntity is exited.
func (s *BaseMariaDBParserListener) ExitShowCommonEntity(ctx *ShowCommonEntityContext) {}

// EnterShowFilter is called when production showFilter is entered.
func (s *BaseMariaDBParserListener) EnterShowFilter(ctx *ShowFilterContext) {}

// ExitShowFilter is called when production showFilter is exited.
func (s *BaseMariaDBParserListener) ExitShowFilter(ctx *ShowFilterContext) {}

// EnterShowGlobalInfoClause is called when production showGlobalInfoClause is entered.
func (s *BaseMariaDBParserListener) EnterShowGlobalInfoClause(ctx *ShowGlobalInfoClauseContext) {}

// ExitShowGlobalInfoClause is called when production showGlobalInfoClause is exited.
func (s *BaseMariaDBParserListener) ExitShowGlobalInfoClause(ctx *ShowGlobalInfoClauseContext) {}

// EnterShowSchemaEntity is called when production showSchemaEntity is entered.
func (s *BaseMariaDBParserListener) EnterShowSchemaEntity(ctx *ShowSchemaEntityContext) {}

// ExitShowSchemaEntity is called when production showSchemaEntity is exited.
func (s *BaseMariaDBParserListener) ExitShowSchemaEntity(ctx *ShowSchemaEntityContext) {}

// EnterShowProfileType is called when production showProfileType is entered.
func (s *BaseMariaDBParserListener) EnterShowProfileType(ctx *ShowProfileTypeContext) {}

// ExitShowProfileType is called when production showProfileType is exited.
func (s *BaseMariaDBParserListener) ExitShowProfileType(ctx *ShowProfileTypeContext) {}

// EnterBinlogStatement is called when production binlogStatement is entered.
func (s *BaseMariaDBParserListener) EnterBinlogStatement(ctx *BinlogStatementContext) {}

// ExitBinlogStatement is called when production binlogStatement is exited.
func (s *BaseMariaDBParserListener) ExitBinlogStatement(ctx *BinlogStatementContext) {}

// EnterCacheIndexStatement is called when production cacheIndexStatement is entered.
func (s *BaseMariaDBParserListener) EnterCacheIndexStatement(ctx *CacheIndexStatementContext) {}

// ExitCacheIndexStatement is called when production cacheIndexStatement is exited.
func (s *BaseMariaDBParserListener) ExitCacheIndexStatement(ctx *CacheIndexStatementContext) {}

// EnterFlushStatement is called when production flushStatement is entered.
func (s *BaseMariaDBParserListener) EnterFlushStatement(ctx *FlushStatementContext) {}

// ExitFlushStatement is called when production flushStatement is exited.
func (s *BaseMariaDBParserListener) ExitFlushStatement(ctx *FlushStatementContext) {}

// EnterKillStatement is called when production killStatement is entered.
func (s *BaseMariaDBParserListener) EnterKillStatement(ctx *KillStatementContext) {}

// ExitKillStatement is called when production killStatement is exited.
func (s *BaseMariaDBParserListener) ExitKillStatement(ctx *KillStatementContext) {}

// EnterLoadIndexIntoCache is called when production loadIndexIntoCache is entered.
func (s *BaseMariaDBParserListener) EnterLoadIndexIntoCache(ctx *LoadIndexIntoCacheContext) {}

// ExitLoadIndexIntoCache is called when production loadIndexIntoCache is exited.
func (s *BaseMariaDBParserListener) ExitLoadIndexIntoCache(ctx *LoadIndexIntoCacheContext) {}

// EnterResetStatement is called when production resetStatement is entered.
func (s *BaseMariaDBParserListener) EnterResetStatement(ctx *ResetStatementContext) {}

// ExitResetStatement is called when production resetStatement is exited.
func (s *BaseMariaDBParserListener) ExitResetStatement(ctx *ResetStatementContext) {}

// EnterShutdownStatement is called when production shutdownStatement is entered.
func (s *BaseMariaDBParserListener) EnterShutdownStatement(ctx *ShutdownStatementContext) {}

// ExitShutdownStatement is called when production shutdownStatement is exited.
func (s *BaseMariaDBParserListener) ExitShutdownStatement(ctx *ShutdownStatementContext) {}

// EnterTableIndexes is called when production tableIndexes is entered.
func (s *BaseMariaDBParserListener) EnterTableIndexes(ctx *TableIndexesContext) {}

// ExitTableIndexes is called when production tableIndexes is exited.
func (s *BaseMariaDBParserListener) ExitTableIndexes(ctx *TableIndexesContext) {}

// EnterSimpleFlushOption is called when production simpleFlushOption is entered.
func (s *BaseMariaDBParserListener) EnterSimpleFlushOption(ctx *SimpleFlushOptionContext) {}

// ExitSimpleFlushOption is called when production simpleFlushOption is exited.
func (s *BaseMariaDBParserListener) ExitSimpleFlushOption(ctx *SimpleFlushOptionContext) {}

// EnterChannelFlushOption is called when production channelFlushOption is entered.
func (s *BaseMariaDBParserListener) EnterChannelFlushOption(ctx *ChannelFlushOptionContext) {}

// ExitChannelFlushOption is called when production channelFlushOption is exited.
func (s *BaseMariaDBParserListener) ExitChannelFlushOption(ctx *ChannelFlushOptionContext) {}

// EnterTableFlushOption is called when production tableFlushOption is entered.
func (s *BaseMariaDBParserListener) EnterTableFlushOption(ctx *TableFlushOptionContext) {}

// ExitTableFlushOption is called when production tableFlushOption is exited.
func (s *BaseMariaDBParserListener) ExitTableFlushOption(ctx *TableFlushOptionContext) {}

// EnterFlushTableOption is called when production flushTableOption is entered.
func (s *BaseMariaDBParserListener) EnterFlushTableOption(ctx *FlushTableOptionContext) {}

// ExitFlushTableOption is called when production flushTableOption is exited.
func (s *BaseMariaDBParserListener) ExitFlushTableOption(ctx *FlushTableOptionContext) {}

// EnterLoadedTableIndexes is called when production loadedTableIndexes is entered.
func (s *BaseMariaDBParserListener) EnterLoadedTableIndexes(ctx *LoadedTableIndexesContext) {}

// ExitLoadedTableIndexes is called when production loadedTableIndexes is exited.
func (s *BaseMariaDBParserListener) ExitLoadedTableIndexes(ctx *LoadedTableIndexesContext) {}

// EnterSimpleDescribeStatement is called when production simpleDescribeStatement is entered.
func (s *BaseMariaDBParserListener) EnterSimpleDescribeStatement(ctx *SimpleDescribeStatementContext) {
}

// ExitSimpleDescribeStatement is called when production simpleDescribeStatement is exited.
func (s *BaseMariaDBParserListener) ExitSimpleDescribeStatement(ctx *SimpleDescribeStatementContext) {
}

// EnterFullDescribeStatement is called when production fullDescribeStatement is entered.
func (s *BaseMariaDBParserListener) EnterFullDescribeStatement(ctx *FullDescribeStatementContext) {}

// ExitFullDescribeStatement is called when production fullDescribeStatement is exited.
func (s *BaseMariaDBParserListener) ExitFullDescribeStatement(ctx *FullDescribeStatementContext) {}

// EnterFormatJsonStatement is called when production formatJsonStatement is entered.
func (s *BaseMariaDBParserListener) EnterFormatJsonStatement(ctx *FormatJsonStatementContext) {}

// ExitFormatJsonStatement is called when production formatJsonStatement is exited.
func (s *BaseMariaDBParserListener) ExitFormatJsonStatement(ctx *FormatJsonStatementContext) {}

// EnterHelpStatement is called when production helpStatement is entered.
func (s *BaseMariaDBParserListener) EnterHelpStatement(ctx *HelpStatementContext) {}

// ExitHelpStatement is called when production helpStatement is exited.
func (s *BaseMariaDBParserListener) ExitHelpStatement(ctx *HelpStatementContext) {}

// EnterUseStatement is called when production useStatement is entered.
func (s *BaseMariaDBParserListener) EnterUseStatement(ctx *UseStatementContext) {}

// ExitUseStatement is called when production useStatement is exited.
func (s *BaseMariaDBParserListener) ExitUseStatement(ctx *UseStatementContext) {}

// EnterSignalStatement is called when production signalStatement is entered.
func (s *BaseMariaDBParserListener) EnterSignalStatement(ctx *SignalStatementContext) {}

// ExitSignalStatement is called when production signalStatement is exited.
func (s *BaseMariaDBParserListener) ExitSignalStatement(ctx *SignalStatementContext) {}

// EnterResignalStatement is called when production resignalStatement is entered.
func (s *BaseMariaDBParserListener) EnterResignalStatement(ctx *ResignalStatementContext) {}

// ExitResignalStatement is called when production resignalStatement is exited.
func (s *BaseMariaDBParserListener) ExitResignalStatement(ctx *ResignalStatementContext) {}

// EnterSignalConditionInformation is called when production signalConditionInformation is entered.
func (s *BaseMariaDBParserListener) EnterSignalConditionInformation(ctx *SignalConditionInformationContext) {
}

// ExitSignalConditionInformation is called when production signalConditionInformation is exited.
func (s *BaseMariaDBParserListener) ExitSignalConditionInformation(ctx *SignalConditionInformationContext) {
}

// EnterDiagnosticsStatement is called when production diagnosticsStatement is entered.
func (s *BaseMariaDBParserListener) EnterDiagnosticsStatement(ctx *DiagnosticsStatementContext) {}

// ExitDiagnosticsStatement is called when production diagnosticsStatement is exited.
func (s *BaseMariaDBParserListener) ExitDiagnosticsStatement(ctx *DiagnosticsStatementContext) {}

// EnterDiagnosticsConditionInformationName is called when production diagnosticsConditionInformationName is entered.
func (s *BaseMariaDBParserListener) EnterDiagnosticsConditionInformationName(ctx *DiagnosticsConditionInformationNameContext) {
}

// ExitDiagnosticsConditionInformationName is called when production diagnosticsConditionInformationName is exited.
func (s *BaseMariaDBParserListener) ExitDiagnosticsConditionInformationName(ctx *DiagnosticsConditionInformationNameContext) {
}

// EnterDescribeStatements is called when production describeStatements is entered.
func (s *BaseMariaDBParserListener) EnterDescribeStatements(ctx *DescribeStatementsContext) {}

// ExitDescribeStatements is called when production describeStatements is exited.
func (s *BaseMariaDBParserListener) ExitDescribeStatements(ctx *DescribeStatementsContext) {}

// EnterDescribeConnection is called when production describeConnection is entered.
func (s *BaseMariaDBParserListener) EnterDescribeConnection(ctx *DescribeConnectionContext) {}

// ExitDescribeConnection is called when production describeConnection is exited.
func (s *BaseMariaDBParserListener) ExitDescribeConnection(ctx *DescribeConnectionContext) {}

// EnterFullId is called when production fullId is entered.
func (s *BaseMariaDBParserListener) EnterFullId(ctx *FullIdContext) {}

// ExitFullId is called when production fullId is exited.
func (s *BaseMariaDBParserListener) ExitFullId(ctx *FullIdContext) {}

// EnterTableName is called when production tableName is entered.
func (s *BaseMariaDBParserListener) EnterTableName(ctx *TableNameContext) {}

// ExitTableName is called when production tableName is exited.
func (s *BaseMariaDBParserListener) ExitTableName(ctx *TableNameContext) {}

// EnterRoleName is called when production roleName is entered.
func (s *BaseMariaDBParserListener) EnterRoleName(ctx *RoleNameContext) {}

// ExitRoleName is called when production roleName is exited.
func (s *BaseMariaDBParserListener) ExitRoleName(ctx *RoleNameContext) {}

// EnterFullColumnName is called when production fullColumnName is entered.
func (s *BaseMariaDBParserListener) EnterFullColumnName(ctx *FullColumnNameContext) {}

// ExitFullColumnName is called when production fullColumnName is exited.
func (s *BaseMariaDBParserListener) ExitFullColumnName(ctx *FullColumnNameContext) {}

// EnterIndexColumnName is called when production indexColumnName is entered.
func (s *BaseMariaDBParserListener) EnterIndexColumnName(ctx *IndexColumnNameContext) {}

// ExitIndexColumnName is called when production indexColumnName is exited.
func (s *BaseMariaDBParserListener) ExitIndexColumnName(ctx *IndexColumnNameContext) {}

// EnterSimpleUserName is called when production simpleUserName is entered.
func (s *BaseMariaDBParserListener) EnterSimpleUserName(ctx *SimpleUserNameContext) {}

// ExitSimpleUserName is called when production simpleUserName is exited.
func (s *BaseMariaDBParserListener) ExitSimpleUserName(ctx *SimpleUserNameContext) {}

// EnterHostName is called when production hostName is entered.
func (s *BaseMariaDBParserListener) EnterHostName(ctx *HostNameContext) {}

// ExitHostName is called when production hostName is exited.
func (s *BaseMariaDBParserListener) ExitHostName(ctx *HostNameContext) {}

// EnterUserName is called when production userName is entered.
func (s *BaseMariaDBParserListener) EnterUserName(ctx *UserNameContext) {}

// ExitUserName is called when production userName is exited.
func (s *BaseMariaDBParserListener) ExitUserName(ctx *UserNameContext) {}

// EnterMysqlVariable is called when production mysqlVariable is entered.
func (s *BaseMariaDBParserListener) EnterMysqlVariable(ctx *MysqlVariableContext) {}

// ExitMysqlVariable is called when production mysqlVariable is exited.
func (s *BaseMariaDBParserListener) ExitMysqlVariable(ctx *MysqlVariableContext) {}

// EnterCharsetName is called when production charsetName is entered.
func (s *BaseMariaDBParserListener) EnterCharsetName(ctx *CharsetNameContext) {}

// ExitCharsetName is called when production charsetName is exited.
func (s *BaseMariaDBParserListener) ExitCharsetName(ctx *CharsetNameContext) {}

// EnterCollationName is called when production collationName is entered.
func (s *BaseMariaDBParserListener) EnterCollationName(ctx *CollationNameContext) {}

// ExitCollationName is called when production collationName is exited.
func (s *BaseMariaDBParserListener) ExitCollationName(ctx *CollationNameContext) {}

// EnterEngineName is called when production engineName is entered.
func (s *BaseMariaDBParserListener) EnterEngineName(ctx *EngineNameContext) {}

// ExitEngineName is called when production engineName is exited.
func (s *BaseMariaDBParserListener) ExitEngineName(ctx *EngineNameContext) {}

// EnterEngineNameBase is called when production engineNameBase is entered.
func (s *BaseMariaDBParserListener) EnterEngineNameBase(ctx *EngineNameBaseContext) {}

// ExitEngineNameBase is called when production engineNameBase is exited.
func (s *BaseMariaDBParserListener) ExitEngineNameBase(ctx *EngineNameBaseContext) {}

// EnterEncryptedLiteral is called when production encryptedLiteral is entered.
func (s *BaseMariaDBParserListener) EnterEncryptedLiteral(ctx *EncryptedLiteralContext) {}

// ExitEncryptedLiteral is called when production encryptedLiteral is exited.
func (s *BaseMariaDBParserListener) ExitEncryptedLiteral(ctx *EncryptedLiteralContext) {}

// EnterUuidSet is called when production uuidSet is entered.
func (s *BaseMariaDBParserListener) EnterUuidSet(ctx *UuidSetContext) {}

// ExitUuidSet is called when production uuidSet is exited.
func (s *BaseMariaDBParserListener) ExitUuidSet(ctx *UuidSetContext) {}

// EnterXid is called when production xid is entered.
func (s *BaseMariaDBParserListener) EnterXid(ctx *XidContext) {}

// ExitXid is called when production xid is exited.
func (s *BaseMariaDBParserListener) ExitXid(ctx *XidContext) {}

// EnterXuidStringId is called when production xuidStringId is entered.
func (s *BaseMariaDBParserListener) EnterXuidStringId(ctx *XuidStringIdContext) {}

// ExitXuidStringId is called when production xuidStringId is exited.
func (s *BaseMariaDBParserListener) ExitXuidStringId(ctx *XuidStringIdContext) {}

// EnterAuthPlugin is called when production authPlugin is entered.
func (s *BaseMariaDBParserListener) EnterAuthPlugin(ctx *AuthPluginContext) {}

// ExitAuthPlugin is called when production authPlugin is exited.
func (s *BaseMariaDBParserListener) ExitAuthPlugin(ctx *AuthPluginContext) {}

// EnterUid is called when production uid is entered.
func (s *BaseMariaDBParserListener) EnterUid(ctx *UidContext) {}

// ExitUid is called when production uid is exited.
func (s *BaseMariaDBParserListener) ExitUid(ctx *UidContext) {}

// EnterSimpleId is called when production simpleId is entered.
func (s *BaseMariaDBParserListener) EnterSimpleId(ctx *SimpleIdContext) {}

// ExitSimpleId is called when production simpleId is exited.
func (s *BaseMariaDBParserListener) ExitSimpleId(ctx *SimpleIdContext) {}

// EnterDottedId is called when production dottedId is entered.
func (s *BaseMariaDBParserListener) EnterDottedId(ctx *DottedIdContext) {}

// ExitDottedId is called when production dottedId is exited.
func (s *BaseMariaDBParserListener) ExitDottedId(ctx *DottedIdContext) {}

// EnterDecimalLiteral is called when production decimalLiteral is entered.
func (s *BaseMariaDBParserListener) EnterDecimalLiteral(ctx *DecimalLiteralContext) {}

// ExitDecimalLiteral is called when production decimalLiteral is exited.
func (s *BaseMariaDBParserListener) ExitDecimalLiteral(ctx *DecimalLiteralContext) {}

// EnterFileSizeLiteral is called when production fileSizeLiteral is entered.
func (s *BaseMariaDBParserListener) EnterFileSizeLiteral(ctx *FileSizeLiteralContext) {}

// ExitFileSizeLiteral is called when production fileSizeLiteral is exited.
func (s *BaseMariaDBParserListener) ExitFileSizeLiteral(ctx *FileSizeLiteralContext) {}

// EnterStringLiteral is called when production stringLiteral is entered.
func (s *BaseMariaDBParserListener) EnterStringLiteral(ctx *StringLiteralContext) {}

// ExitStringLiteral is called when production stringLiteral is exited.
func (s *BaseMariaDBParserListener) ExitStringLiteral(ctx *StringLiteralContext) {}

// EnterBooleanLiteral is called when production booleanLiteral is entered.
func (s *BaseMariaDBParserListener) EnterBooleanLiteral(ctx *BooleanLiteralContext) {}

// ExitBooleanLiteral is called when production booleanLiteral is exited.
func (s *BaseMariaDBParserListener) ExitBooleanLiteral(ctx *BooleanLiteralContext) {}

// EnterHexadecimalLiteral is called when production hexadecimalLiteral is entered.
func (s *BaseMariaDBParserListener) EnterHexadecimalLiteral(ctx *HexadecimalLiteralContext) {}

// ExitHexadecimalLiteral is called when production hexadecimalLiteral is exited.
func (s *BaseMariaDBParserListener) ExitHexadecimalLiteral(ctx *HexadecimalLiteralContext) {}

// EnterNullNotnull is called when production nullNotnull is entered.
func (s *BaseMariaDBParserListener) EnterNullNotnull(ctx *NullNotnullContext) {}

// ExitNullNotnull is called when production nullNotnull is exited.
func (s *BaseMariaDBParserListener) ExitNullNotnull(ctx *NullNotnullContext) {}

// EnterConstant is called when production constant is entered.
func (s *BaseMariaDBParserListener) EnterConstant(ctx *ConstantContext) {}

// ExitConstant is called when production constant is exited.
func (s *BaseMariaDBParserListener) ExitConstant(ctx *ConstantContext) {}

// EnterStringDataType is called when production stringDataType is entered.
func (s *BaseMariaDBParserListener) EnterStringDataType(ctx *StringDataTypeContext) {}

// ExitStringDataType is called when production stringDataType is exited.
func (s *BaseMariaDBParserListener) ExitStringDataType(ctx *StringDataTypeContext) {}

// EnterNationalStringDataType is called when production nationalStringDataType is entered.
func (s *BaseMariaDBParserListener) EnterNationalStringDataType(ctx *NationalStringDataTypeContext) {}

// ExitNationalStringDataType is called when production nationalStringDataType is exited.
func (s *BaseMariaDBParserListener) ExitNationalStringDataType(ctx *NationalStringDataTypeContext) {}

// EnterNationalVaryingStringDataType is called when production nationalVaryingStringDataType is entered.
func (s *BaseMariaDBParserListener) EnterNationalVaryingStringDataType(ctx *NationalVaryingStringDataTypeContext) {
}

// ExitNationalVaryingStringDataType is called when production nationalVaryingStringDataType is exited.
func (s *BaseMariaDBParserListener) ExitNationalVaryingStringDataType(ctx *NationalVaryingStringDataTypeContext) {
}

// EnterDimensionDataType is called when production dimensionDataType is entered.
func (s *BaseMariaDBParserListener) EnterDimensionDataType(ctx *DimensionDataTypeContext) {}

// ExitDimensionDataType is called when production dimensionDataType is exited.
func (s *BaseMariaDBParserListener) ExitDimensionDataType(ctx *DimensionDataTypeContext) {}

// EnterSimpleDataType is called when production simpleDataType is entered.
func (s *BaseMariaDBParserListener) EnterSimpleDataType(ctx *SimpleDataTypeContext) {}

// ExitSimpleDataType is called when production simpleDataType is exited.
func (s *BaseMariaDBParserListener) ExitSimpleDataType(ctx *SimpleDataTypeContext) {}

// EnterCollectionDataType is called when production collectionDataType is entered.
func (s *BaseMariaDBParserListener) EnterCollectionDataType(ctx *CollectionDataTypeContext) {}

// ExitCollectionDataType is called when production collectionDataType is exited.
func (s *BaseMariaDBParserListener) ExitCollectionDataType(ctx *CollectionDataTypeContext) {}

// EnterSpatialDataType is called when production spatialDataType is entered.
func (s *BaseMariaDBParserListener) EnterSpatialDataType(ctx *SpatialDataTypeContext) {}

// ExitSpatialDataType is called when production spatialDataType is exited.
func (s *BaseMariaDBParserListener) ExitSpatialDataType(ctx *SpatialDataTypeContext) {}

// EnterLongVarcharDataType is called when production longVarcharDataType is entered.
func (s *BaseMariaDBParserListener) EnterLongVarcharDataType(ctx *LongVarcharDataTypeContext) {}

// ExitLongVarcharDataType is called when production longVarcharDataType is exited.
func (s *BaseMariaDBParserListener) ExitLongVarcharDataType(ctx *LongVarcharDataTypeContext) {}

// EnterLongVarbinaryDataType is called when production longVarbinaryDataType is entered.
func (s *BaseMariaDBParserListener) EnterLongVarbinaryDataType(ctx *LongVarbinaryDataTypeContext) {}

// ExitLongVarbinaryDataType is called when production longVarbinaryDataType is exited.
func (s *BaseMariaDBParserListener) ExitLongVarbinaryDataType(ctx *LongVarbinaryDataTypeContext) {}

// EnterUuidDataType is called when production uuidDataType is entered.
func (s *BaseMariaDBParserListener) EnterUuidDataType(ctx *UuidDataTypeContext) {}

// ExitUuidDataType is called when production uuidDataType is exited.
func (s *BaseMariaDBParserListener) ExitUuidDataType(ctx *UuidDataTypeContext) {}

// EnterCollectionOptions is called when production collectionOptions is entered.
func (s *BaseMariaDBParserListener) EnterCollectionOptions(ctx *CollectionOptionsContext) {}

// ExitCollectionOptions is called when production collectionOptions is exited.
func (s *BaseMariaDBParserListener) ExitCollectionOptions(ctx *CollectionOptionsContext) {}

// EnterCollectionOption is called when production collectionOption is entered.
func (s *BaseMariaDBParserListener) EnterCollectionOption(ctx *CollectionOptionContext) {}

// ExitCollectionOption is called when production collectionOption is exited.
func (s *BaseMariaDBParserListener) ExitCollectionOption(ctx *CollectionOptionContext) {}

// EnterConvertedDataType is called when production convertedDataType is entered.
func (s *BaseMariaDBParserListener) EnterConvertedDataType(ctx *ConvertedDataTypeContext) {}

// ExitConvertedDataType is called when production convertedDataType is exited.
func (s *BaseMariaDBParserListener) ExitConvertedDataType(ctx *ConvertedDataTypeContext) {}

// EnterLengthOneDimension is called when production lengthOneDimension is entered.
func (s *BaseMariaDBParserListener) EnterLengthOneDimension(ctx *LengthOneDimensionContext) {}

// ExitLengthOneDimension is called when production lengthOneDimension is exited.
func (s *BaseMariaDBParserListener) ExitLengthOneDimension(ctx *LengthOneDimensionContext) {}

// EnterLengthTwoDimension is called when production lengthTwoDimension is entered.
func (s *BaseMariaDBParserListener) EnterLengthTwoDimension(ctx *LengthTwoDimensionContext) {}

// ExitLengthTwoDimension is called when production lengthTwoDimension is exited.
func (s *BaseMariaDBParserListener) ExitLengthTwoDimension(ctx *LengthTwoDimensionContext) {}

// EnterLengthTwoOptionalDimension is called when production lengthTwoOptionalDimension is entered.
func (s *BaseMariaDBParserListener) EnterLengthTwoOptionalDimension(ctx *LengthTwoOptionalDimensionContext) {
}

// ExitLengthTwoOptionalDimension is called when production lengthTwoOptionalDimension is exited.
func (s *BaseMariaDBParserListener) ExitLengthTwoOptionalDimension(ctx *LengthTwoOptionalDimensionContext) {
}

// EnterUidList is called when production uidList is entered.
func (s *BaseMariaDBParserListener) EnterUidList(ctx *UidListContext) {}

// ExitUidList is called when production uidList is exited.
func (s *BaseMariaDBParserListener) ExitUidList(ctx *UidListContext) {}

// EnterTables is called when production tables is entered.
func (s *BaseMariaDBParserListener) EnterTables(ctx *TablesContext) {}

// ExitTables is called when production tables is exited.
func (s *BaseMariaDBParserListener) ExitTables(ctx *TablesContext) {}

// EnterIndexColumnNames is called when production indexColumnNames is entered.
func (s *BaseMariaDBParserListener) EnterIndexColumnNames(ctx *IndexColumnNamesContext) {}

// ExitIndexColumnNames is called when production indexColumnNames is exited.
func (s *BaseMariaDBParserListener) ExitIndexColumnNames(ctx *IndexColumnNamesContext) {}

// EnterExpressions is called when production expressions is entered.
func (s *BaseMariaDBParserListener) EnterExpressions(ctx *ExpressionsContext) {}

// ExitExpressions is called when production expressions is exited.
func (s *BaseMariaDBParserListener) ExitExpressions(ctx *ExpressionsContext) {}

// EnterExpressionsWithDefaults is called when production expressionsWithDefaults is entered.
func (s *BaseMariaDBParserListener) EnterExpressionsWithDefaults(ctx *ExpressionsWithDefaultsContext) {
}

// ExitExpressionsWithDefaults is called when production expressionsWithDefaults is exited.
func (s *BaseMariaDBParserListener) ExitExpressionsWithDefaults(ctx *ExpressionsWithDefaultsContext) {
}

// EnterConstants is called when production constants is entered.
func (s *BaseMariaDBParserListener) EnterConstants(ctx *ConstantsContext) {}

// ExitConstants is called when production constants is exited.
func (s *BaseMariaDBParserListener) ExitConstants(ctx *ConstantsContext) {}

// EnterSimpleStrings is called when production simpleStrings is entered.
func (s *BaseMariaDBParserListener) EnterSimpleStrings(ctx *SimpleStringsContext) {}

// ExitSimpleStrings is called when production simpleStrings is exited.
func (s *BaseMariaDBParserListener) ExitSimpleStrings(ctx *SimpleStringsContext) {}

// EnterUserVariables is called when production userVariables is entered.
func (s *BaseMariaDBParserListener) EnterUserVariables(ctx *UserVariablesContext) {}

// ExitUserVariables is called when production userVariables is exited.
func (s *BaseMariaDBParserListener) ExitUserVariables(ctx *UserVariablesContext) {}

// EnterDefaultValue is called when production defaultValue is entered.
func (s *BaseMariaDBParserListener) EnterDefaultValue(ctx *DefaultValueContext) {}

// ExitDefaultValue is called when production defaultValue is exited.
func (s *BaseMariaDBParserListener) ExitDefaultValue(ctx *DefaultValueContext) {}

// EnterCurrentTimestamp is called when production currentTimestamp is entered.
func (s *BaseMariaDBParserListener) EnterCurrentTimestamp(ctx *CurrentTimestampContext) {}

// ExitCurrentTimestamp is called when production currentTimestamp is exited.
func (s *BaseMariaDBParserListener) ExitCurrentTimestamp(ctx *CurrentTimestampContext) {}

// EnterExpressionOrDefault is called when production expressionOrDefault is entered.
func (s *BaseMariaDBParserListener) EnterExpressionOrDefault(ctx *ExpressionOrDefaultContext) {}

// ExitExpressionOrDefault is called when production expressionOrDefault is exited.
func (s *BaseMariaDBParserListener) ExitExpressionOrDefault(ctx *ExpressionOrDefaultContext) {}

// EnterIfExists is called when production ifExists is entered.
func (s *BaseMariaDBParserListener) EnterIfExists(ctx *IfExistsContext) {}

// ExitIfExists is called when production ifExists is exited.
func (s *BaseMariaDBParserListener) ExitIfExists(ctx *IfExistsContext) {}

// EnterIfNotExists is called when production ifNotExists is entered.
func (s *BaseMariaDBParserListener) EnterIfNotExists(ctx *IfNotExistsContext) {}

// ExitIfNotExists is called when production ifNotExists is exited.
func (s *BaseMariaDBParserListener) ExitIfNotExists(ctx *IfNotExistsContext) {}

// EnterOrReplace is called when production orReplace is entered.
func (s *BaseMariaDBParserListener) EnterOrReplace(ctx *OrReplaceContext) {}

// ExitOrReplace is called when production orReplace is exited.
func (s *BaseMariaDBParserListener) ExitOrReplace(ctx *OrReplaceContext) {}

// EnterWaitNowaitClause is called when production waitNowaitClause is entered.
func (s *BaseMariaDBParserListener) EnterWaitNowaitClause(ctx *WaitNowaitClauseContext) {}

// ExitWaitNowaitClause is called when production waitNowaitClause is exited.
func (s *BaseMariaDBParserListener) ExitWaitNowaitClause(ctx *WaitNowaitClauseContext) {}

// EnterLockOption is called when production lockOption is entered.
func (s *BaseMariaDBParserListener) EnterLockOption(ctx *LockOptionContext) {}

// ExitLockOption is called when production lockOption is exited.
func (s *BaseMariaDBParserListener) ExitLockOption(ctx *LockOptionContext) {}

// EnterSpecificFunctionCall is called when production specificFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterSpecificFunctionCall(ctx *SpecificFunctionCallContext) {}

// ExitSpecificFunctionCall is called when production specificFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitSpecificFunctionCall(ctx *SpecificFunctionCallContext) {}

// EnterAggregateFunctionCall is called when production aggregateFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterAggregateFunctionCall(ctx *AggregateFunctionCallContext) {}

// ExitAggregateFunctionCall is called when production aggregateFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitAggregateFunctionCall(ctx *AggregateFunctionCallContext) {}

// EnterNonAggregateFunctionCall is called when production nonAggregateFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterNonAggregateFunctionCall(ctx *NonAggregateFunctionCallContext) {
}

// ExitNonAggregateFunctionCall is called when production nonAggregateFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitNonAggregateFunctionCall(ctx *NonAggregateFunctionCallContext) {
}

// EnterScalarFunctionCall is called when production scalarFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterScalarFunctionCall(ctx *ScalarFunctionCallContext) {}

// ExitScalarFunctionCall is called when production scalarFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitScalarFunctionCall(ctx *ScalarFunctionCallContext) {}

// EnterUdfFunctionCall is called when production udfFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterUdfFunctionCall(ctx *UdfFunctionCallContext) {}

// ExitUdfFunctionCall is called when production udfFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitUdfFunctionCall(ctx *UdfFunctionCallContext) {}

// EnterPasswordFunctionCall is called when production passwordFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterPasswordFunctionCall(ctx *PasswordFunctionCallContext) {}

// ExitPasswordFunctionCall is called when production passwordFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitPasswordFunctionCall(ctx *PasswordFunctionCallContext) {}

// EnterSimpleFunctionCall is called when production simpleFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterSimpleFunctionCall(ctx *SimpleFunctionCallContext) {}

// ExitSimpleFunctionCall is called when production simpleFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitSimpleFunctionCall(ctx *SimpleFunctionCallContext) {}

// EnterDataTypeFunctionCall is called when production dataTypeFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterDataTypeFunctionCall(ctx *DataTypeFunctionCallContext) {}

// ExitDataTypeFunctionCall is called when production dataTypeFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitDataTypeFunctionCall(ctx *DataTypeFunctionCallContext) {}

// EnterValuesFunctionCall is called when production valuesFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterValuesFunctionCall(ctx *ValuesFunctionCallContext) {}

// ExitValuesFunctionCall is called when production valuesFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitValuesFunctionCall(ctx *ValuesFunctionCallContext) {}

// EnterCaseExpressionFunctionCall is called when production caseExpressionFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterCaseExpressionFunctionCall(ctx *CaseExpressionFunctionCallContext) {
}

// ExitCaseExpressionFunctionCall is called when production caseExpressionFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitCaseExpressionFunctionCall(ctx *CaseExpressionFunctionCallContext) {
}

// EnterCaseFunctionCall is called when production caseFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterCaseFunctionCall(ctx *CaseFunctionCallContext) {}

// ExitCaseFunctionCall is called when production caseFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitCaseFunctionCall(ctx *CaseFunctionCallContext) {}

// EnterCharFunctionCall is called when production charFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterCharFunctionCall(ctx *CharFunctionCallContext) {}

// ExitCharFunctionCall is called when production charFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitCharFunctionCall(ctx *CharFunctionCallContext) {}

// EnterPositionFunctionCall is called when production positionFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterPositionFunctionCall(ctx *PositionFunctionCallContext) {}

// ExitPositionFunctionCall is called when production positionFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitPositionFunctionCall(ctx *PositionFunctionCallContext) {}

// EnterSubstrFunctionCall is called when production substrFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterSubstrFunctionCall(ctx *SubstrFunctionCallContext) {}

// ExitSubstrFunctionCall is called when production substrFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitSubstrFunctionCall(ctx *SubstrFunctionCallContext) {}

// EnterTrimFunctionCall is called when production trimFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterTrimFunctionCall(ctx *TrimFunctionCallContext) {}

// ExitTrimFunctionCall is called when production trimFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitTrimFunctionCall(ctx *TrimFunctionCallContext) {}

// EnterWeightFunctionCall is called when production weightFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterWeightFunctionCall(ctx *WeightFunctionCallContext) {}

// ExitWeightFunctionCall is called when production weightFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitWeightFunctionCall(ctx *WeightFunctionCallContext) {}

// EnterExtractFunctionCall is called when production extractFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterExtractFunctionCall(ctx *ExtractFunctionCallContext) {}

// ExitExtractFunctionCall is called when production extractFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitExtractFunctionCall(ctx *ExtractFunctionCallContext) {}

// EnterGetFormatFunctionCall is called when production getFormatFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterGetFormatFunctionCall(ctx *GetFormatFunctionCallContext) {}

// ExitGetFormatFunctionCall is called when production getFormatFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitGetFormatFunctionCall(ctx *GetFormatFunctionCallContext) {}

// EnterJsonValueFunctionCall is called when production jsonValueFunctionCall is entered.
func (s *BaseMariaDBParserListener) EnterJsonValueFunctionCall(ctx *JsonValueFunctionCallContext) {}

// ExitJsonValueFunctionCall is called when production jsonValueFunctionCall is exited.
func (s *BaseMariaDBParserListener) ExitJsonValueFunctionCall(ctx *JsonValueFunctionCallContext) {}

// EnterCaseFuncAlternative is called when production caseFuncAlternative is entered.
func (s *BaseMariaDBParserListener) EnterCaseFuncAlternative(ctx *CaseFuncAlternativeContext) {}

// ExitCaseFuncAlternative is called when production caseFuncAlternative is exited.
func (s *BaseMariaDBParserListener) ExitCaseFuncAlternative(ctx *CaseFuncAlternativeContext) {}

// EnterLevelWeightList is called when production levelWeightList is entered.
func (s *BaseMariaDBParserListener) EnterLevelWeightList(ctx *LevelWeightListContext) {}

// ExitLevelWeightList is called when production levelWeightList is exited.
func (s *BaseMariaDBParserListener) ExitLevelWeightList(ctx *LevelWeightListContext) {}

// EnterLevelWeightRange is called when production levelWeightRange is entered.
func (s *BaseMariaDBParserListener) EnterLevelWeightRange(ctx *LevelWeightRangeContext) {}

// ExitLevelWeightRange is called when production levelWeightRange is exited.
func (s *BaseMariaDBParserListener) ExitLevelWeightRange(ctx *LevelWeightRangeContext) {}

// EnterLevelInWeightListElement is called when production levelInWeightListElement is entered.
func (s *BaseMariaDBParserListener) EnterLevelInWeightListElement(ctx *LevelInWeightListElementContext) {
}

// ExitLevelInWeightListElement is called when production levelInWeightListElement is exited.
func (s *BaseMariaDBParserListener) ExitLevelInWeightListElement(ctx *LevelInWeightListElementContext) {
}

// EnterAggregateWindowedFunction is called when production aggregateWindowedFunction is entered.
func (s *BaseMariaDBParserListener) EnterAggregateWindowedFunction(ctx *AggregateWindowedFunctionContext) {
}

// ExitAggregateWindowedFunction is called when production aggregateWindowedFunction is exited.
func (s *BaseMariaDBParserListener) ExitAggregateWindowedFunction(ctx *AggregateWindowedFunctionContext) {
}

// EnterNonAggregateWindowedFunction is called when production nonAggregateWindowedFunction is entered.
func (s *BaseMariaDBParserListener) EnterNonAggregateWindowedFunction(ctx *NonAggregateWindowedFunctionContext) {
}

// ExitNonAggregateWindowedFunction is called when production nonAggregateWindowedFunction is exited.
func (s *BaseMariaDBParserListener) ExitNonAggregateWindowedFunction(ctx *NonAggregateWindowedFunctionContext) {
}

// EnterOverClause is called when production overClause is entered.
func (s *BaseMariaDBParserListener) EnterOverClause(ctx *OverClauseContext) {}

// ExitOverClause is called when production overClause is exited.
func (s *BaseMariaDBParserListener) ExitOverClause(ctx *OverClauseContext) {}

// EnterWindowSpec is called when production windowSpec is entered.
func (s *BaseMariaDBParserListener) EnterWindowSpec(ctx *WindowSpecContext) {}

// ExitWindowSpec is called when production windowSpec is exited.
func (s *BaseMariaDBParserListener) ExitWindowSpec(ctx *WindowSpecContext) {}

// EnterWindowName is called when production windowName is entered.
func (s *BaseMariaDBParserListener) EnterWindowName(ctx *WindowNameContext) {}

// ExitWindowName is called when production windowName is exited.
func (s *BaseMariaDBParserListener) ExitWindowName(ctx *WindowNameContext) {}

// EnterFrameClause is called when production frameClause is entered.
func (s *BaseMariaDBParserListener) EnterFrameClause(ctx *FrameClauseContext) {}

// ExitFrameClause is called when production frameClause is exited.
func (s *BaseMariaDBParserListener) ExitFrameClause(ctx *FrameClauseContext) {}

// EnterFrameUnits is called when production frameUnits is entered.
func (s *BaseMariaDBParserListener) EnterFrameUnits(ctx *FrameUnitsContext) {}

// ExitFrameUnits is called when production frameUnits is exited.
func (s *BaseMariaDBParserListener) ExitFrameUnits(ctx *FrameUnitsContext) {}

// EnterFrameExtent is called when production frameExtent is entered.
func (s *BaseMariaDBParserListener) EnterFrameExtent(ctx *FrameExtentContext) {}

// ExitFrameExtent is called when production frameExtent is exited.
func (s *BaseMariaDBParserListener) ExitFrameExtent(ctx *FrameExtentContext) {}

// EnterFrameBetween is called when production frameBetween is entered.
func (s *BaseMariaDBParserListener) EnterFrameBetween(ctx *FrameBetweenContext) {}

// ExitFrameBetween is called when production frameBetween is exited.
func (s *BaseMariaDBParserListener) ExitFrameBetween(ctx *FrameBetweenContext) {}

// EnterFrameRange is called when production frameRange is entered.
func (s *BaseMariaDBParserListener) EnterFrameRange(ctx *FrameRangeContext) {}

// ExitFrameRange is called when production frameRange is exited.
func (s *BaseMariaDBParserListener) ExitFrameRange(ctx *FrameRangeContext) {}

// EnterPartitionClause is called when production partitionClause is entered.
func (s *BaseMariaDBParserListener) EnterPartitionClause(ctx *PartitionClauseContext) {}

// ExitPartitionClause is called when production partitionClause is exited.
func (s *BaseMariaDBParserListener) ExitPartitionClause(ctx *PartitionClauseContext) {}

// EnterScalarFunctionName is called when production scalarFunctionName is entered.
func (s *BaseMariaDBParserListener) EnterScalarFunctionName(ctx *ScalarFunctionNameContext) {}

// ExitScalarFunctionName is called when production scalarFunctionName is exited.
func (s *BaseMariaDBParserListener) ExitScalarFunctionName(ctx *ScalarFunctionNameContext) {}

// EnterPasswordFunctionClause is called when production passwordFunctionClause is entered.
func (s *BaseMariaDBParserListener) EnterPasswordFunctionClause(ctx *PasswordFunctionClauseContext) {}

// ExitPasswordFunctionClause is called when production passwordFunctionClause is exited.
func (s *BaseMariaDBParserListener) ExitPasswordFunctionClause(ctx *PasswordFunctionClauseContext) {}

// EnterFunctionArgs is called when production functionArgs is entered.
func (s *BaseMariaDBParserListener) EnterFunctionArgs(ctx *FunctionArgsContext) {}

// ExitFunctionArgs is called when production functionArgs is exited.
func (s *BaseMariaDBParserListener) ExitFunctionArgs(ctx *FunctionArgsContext) {}

// EnterFunctionArg is called when production functionArg is entered.
func (s *BaseMariaDBParserListener) EnterFunctionArg(ctx *FunctionArgContext) {}

// ExitFunctionArg is called when production functionArg is exited.
func (s *BaseMariaDBParserListener) ExitFunctionArg(ctx *FunctionArgContext) {}

// EnterIsExpression is called when production isExpression is entered.
func (s *BaseMariaDBParserListener) EnterIsExpression(ctx *IsExpressionContext) {}

// ExitIsExpression is called when production isExpression is exited.
func (s *BaseMariaDBParserListener) ExitIsExpression(ctx *IsExpressionContext) {}

// EnterNotExpression is called when production notExpression is entered.
func (s *BaseMariaDBParserListener) EnterNotExpression(ctx *NotExpressionContext) {}

// ExitNotExpression is called when production notExpression is exited.
func (s *BaseMariaDBParserListener) ExitNotExpression(ctx *NotExpressionContext) {}

// EnterLogicalExpression is called when production logicalExpression is entered.
func (s *BaseMariaDBParserListener) EnterLogicalExpression(ctx *LogicalExpressionContext) {}

// ExitLogicalExpression is called when production logicalExpression is exited.
func (s *BaseMariaDBParserListener) ExitLogicalExpression(ctx *LogicalExpressionContext) {}

// EnterPredicateExpression is called when production predicateExpression is entered.
func (s *BaseMariaDBParserListener) EnterPredicateExpression(ctx *PredicateExpressionContext) {}

// ExitPredicateExpression is called when production predicateExpression is exited.
func (s *BaseMariaDBParserListener) ExitPredicateExpression(ctx *PredicateExpressionContext) {}

// EnterSoundsLikePredicate is called when production soundsLikePredicate is entered.
func (s *BaseMariaDBParserListener) EnterSoundsLikePredicate(ctx *SoundsLikePredicateContext) {}

// ExitSoundsLikePredicate is called when production soundsLikePredicate is exited.
func (s *BaseMariaDBParserListener) ExitSoundsLikePredicate(ctx *SoundsLikePredicateContext) {}

// EnterExpressionAtomPredicate is called when production expressionAtomPredicate is entered.
func (s *BaseMariaDBParserListener) EnterExpressionAtomPredicate(ctx *ExpressionAtomPredicateContext) {
}

// ExitExpressionAtomPredicate is called when production expressionAtomPredicate is exited.
func (s *BaseMariaDBParserListener) ExitExpressionAtomPredicate(ctx *ExpressionAtomPredicateContext) {
}

// EnterSubqueryComparisonPredicate is called when production subqueryComparisonPredicate is entered.
func (s *BaseMariaDBParserListener) EnterSubqueryComparisonPredicate(ctx *SubqueryComparisonPredicateContext) {
}

// ExitSubqueryComparisonPredicate is called when production subqueryComparisonPredicate is exited.
func (s *BaseMariaDBParserListener) ExitSubqueryComparisonPredicate(ctx *SubqueryComparisonPredicateContext) {
}

// EnterJsonMemberOfPredicate is called when production jsonMemberOfPredicate is entered.
func (s *BaseMariaDBParserListener) EnterJsonMemberOfPredicate(ctx *JsonMemberOfPredicateContext) {}

// ExitJsonMemberOfPredicate is called when production jsonMemberOfPredicate is exited.
func (s *BaseMariaDBParserListener) ExitJsonMemberOfPredicate(ctx *JsonMemberOfPredicateContext) {}

// EnterBinaryComparisonPredicate is called when production binaryComparisonPredicate is entered.
func (s *BaseMariaDBParserListener) EnterBinaryComparisonPredicate(ctx *BinaryComparisonPredicateContext) {
}

// ExitBinaryComparisonPredicate is called when production binaryComparisonPredicate is exited.
func (s *BaseMariaDBParserListener) ExitBinaryComparisonPredicate(ctx *BinaryComparisonPredicateContext) {
}

// EnterInPredicate is called when production inPredicate is entered.
func (s *BaseMariaDBParserListener) EnterInPredicate(ctx *InPredicateContext) {}

// ExitInPredicate is called when production inPredicate is exited.
func (s *BaseMariaDBParserListener) ExitInPredicate(ctx *InPredicateContext) {}

// EnterBetweenPredicate is called when production betweenPredicate is entered.
func (s *BaseMariaDBParserListener) EnterBetweenPredicate(ctx *BetweenPredicateContext) {}

// ExitBetweenPredicate is called when production betweenPredicate is exited.
func (s *BaseMariaDBParserListener) ExitBetweenPredicate(ctx *BetweenPredicateContext) {}

// EnterIsNullPredicate is called when production isNullPredicate is entered.
func (s *BaseMariaDBParserListener) EnterIsNullPredicate(ctx *IsNullPredicateContext) {}

// ExitIsNullPredicate is called when production isNullPredicate is exited.
func (s *BaseMariaDBParserListener) ExitIsNullPredicate(ctx *IsNullPredicateContext) {}

// EnterLikePredicate is called when production likePredicate is entered.
func (s *BaseMariaDBParserListener) EnterLikePredicate(ctx *LikePredicateContext) {}

// ExitLikePredicate is called when production likePredicate is exited.
func (s *BaseMariaDBParserListener) ExitLikePredicate(ctx *LikePredicateContext) {}

// EnterRegexpPredicate is called when production regexpPredicate is entered.
func (s *BaseMariaDBParserListener) EnterRegexpPredicate(ctx *RegexpPredicateContext) {}

// ExitRegexpPredicate is called when production regexpPredicate is exited.
func (s *BaseMariaDBParserListener) ExitRegexpPredicate(ctx *RegexpPredicateContext) {}

// EnterUnaryExpressionAtom is called when production unaryExpressionAtom is entered.
func (s *BaseMariaDBParserListener) EnterUnaryExpressionAtom(ctx *UnaryExpressionAtomContext) {}

// ExitUnaryExpressionAtom is called when production unaryExpressionAtom is exited.
func (s *BaseMariaDBParserListener) ExitUnaryExpressionAtom(ctx *UnaryExpressionAtomContext) {}

// EnterCollateExpressionAtom is called when production collateExpressionAtom is entered.
func (s *BaseMariaDBParserListener) EnterCollateExpressionAtom(ctx *CollateExpressionAtomContext) {}

// ExitCollateExpressionAtom is called when production collateExpressionAtom is exited.
func (s *BaseMariaDBParserListener) ExitCollateExpressionAtom(ctx *CollateExpressionAtomContext) {}

// EnterVariableAssignExpressionAtom is called when production variableAssignExpressionAtom is entered.
func (s *BaseMariaDBParserListener) EnterVariableAssignExpressionAtom(ctx *VariableAssignExpressionAtomContext) {
}

// ExitVariableAssignExpressionAtom is called when production variableAssignExpressionAtom is exited.
func (s *BaseMariaDBParserListener) ExitVariableAssignExpressionAtom(ctx *VariableAssignExpressionAtomContext) {
}

// EnterMysqlVariableExpressionAtom is called when production mysqlVariableExpressionAtom is entered.
func (s *BaseMariaDBParserListener) EnterMysqlVariableExpressionAtom(ctx *MysqlVariableExpressionAtomContext) {
}

// ExitMysqlVariableExpressionAtom is called when production mysqlVariableExpressionAtom is exited.
func (s *BaseMariaDBParserListener) ExitMysqlVariableExpressionAtom(ctx *MysqlVariableExpressionAtomContext) {
}

// EnterNestedExpressionAtom is called when production nestedExpressionAtom is entered.
func (s *BaseMariaDBParserListener) EnterNestedExpressionAtom(ctx *NestedExpressionAtomContext) {}

// ExitNestedExpressionAtom is called when production nestedExpressionAtom is exited.
func (s *BaseMariaDBParserListener) ExitNestedExpressionAtom(ctx *NestedExpressionAtomContext) {}

// EnterNestedRowExpressionAtom is called when production nestedRowExpressionAtom is entered.
func (s *BaseMariaDBParserListener) EnterNestedRowExpressionAtom(ctx *NestedRowExpressionAtomContext) {
}

// ExitNestedRowExpressionAtom is called when production nestedRowExpressionAtom is exited.
func (s *BaseMariaDBParserListener) ExitNestedRowExpressionAtom(ctx *NestedRowExpressionAtomContext) {
}

// EnterMathExpressionAtom is called when production mathExpressionAtom is entered.
func (s *BaseMariaDBParserListener) EnterMathExpressionAtom(ctx *MathExpressionAtomContext) {}

// ExitMathExpressionAtom is called when production mathExpressionAtom is exited.
func (s *BaseMariaDBParserListener) ExitMathExpressionAtom(ctx *MathExpressionAtomContext) {}

// EnterExistsExpressionAtom is called when production existsExpressionAtom is entered.
func (s *BaseMariaDBParserListener) EnterExistsExpressionAtom(ctx *ExistsExpressionAtomContext) {}

// ExitExistsExpressionAtom is called when production existsExpressionAtom is exited.
func (s *BaseMariaDBParserListener) ExitExistsExpressionAtom(ctx *ExistsExpressionAtomContext) {}

// EnterIntervalExpressionAtom is called when production intervalExpressionAtom is entered.
func (s *BaseMariaDBParserListener) EnterIntervalExpressionAtom(ctx *IntervalExpressionAtomContext) {}

// ExitIntervalExpressionAtom is called when production intervalExpressionAtom is exited.
func (s *BaseMariaDBParserListener) ExitIntervalExpressionAtom(ctx *IntervalExpressionAtomContext) {}

// EnterJsonExpressionAtom is called when production jsonExpressionAtom is entered.
func (s *BaseMariaDBParserListener) EnterJsonExpressionAtom(ctx *JsonExpressionAtomContext) {}

// ExitJsonExpressionAtom is called when production jsonExpressionAtom is exited.
func (s *BaseMariaDBParserListener) ExitJsonExpressionAtom(ctx *JsonExpressionAtomContext) {}

// EnterSubqueryExpressionAtom is called when production subqueryExpressionAtom is entered.
func (s *BaseMariaDBParserListener) EnterSubqueryExpressionAtom(ctx *SubqueryExpressionAtomContext) {}

// ExitSubqueryExpressionAtom is called when production subqueryExpressionAtom is exited.
func (s *BaseMariaDBParserListener) ExitSubqueryExpressionAtom(ctx *SubqueryExpressionAtomContext) {}

// EnterConstantExpressionAtom is called when production constantExpressionAtom is entered.
func (s *BaseMariaDBParserListener) EnterConstantExpressionAtom(ctx *ConstantExpressionAtomContext) {}

// ExitConstantExpressionAtom is called when production constantExpressionAtom is exited.
func (s *BaseMariaDBParserListener) ExitConstantExpressionAtom(ctx *ConstantExpressionAtomContext) {}

// EnterFunctionCallExpressionAtom is called when production functionCallExpressionAtom is entered.
func (s *BaseMariaDBParserListener) EnterFunctionCallExpressionAtom(ctx *FunctionCallExpressionAtomContext) {
}

// ExitFunctionCallExpressionAtom is called when production functionCallExpressionAtom is exited.
func (s *BaseMariaDBParserListener) ExitFunctionCallExpressionAtom(ctx *FunctionCallExpressionAtomContext) {
}

// EnterBinaryExpressionAtom is called when production binaryExpressionAtom is entered.
func (s *BaseMariaDBParserListener) EnterBinaryExpressionAtom(ctx *BinaryExpressionAtomContext) {}

// ExitBinaryExpressionAtom is called when production binaryExpressionAtom is exited.
func (s *BaseMariaDBParserListener) ExitBinaryExpressionAtom(ctx *BinaryExpressionAtomContext) {}

// EnterFullColumnNameExpressionAtom is called when production fullColumnNameExpressionAtom is entered.
func (s *BaseMariaDBParserListener) EnterFullColumnNameExpressionAtom(ctx *FullColumnNameExpressionAtomContext) {
}

// ExitFullColumnNameExpressionAtom is called when production fullColumnNameExpressionAtom is exited.
func (s *BaseMariaDBParserListener) ExitFullColumnNameExpressionAtom(ctx *FullColumnNameExpressionAtomContext) {
}

// EnterBitExpressionAtom is called when production bitExpressionAtom is entered.
func (s *BaseMariaDBParserListener) EnterBitExpressionAtom(ctx *BitExpressionAtomContext) {}

// ExitBitExpressionAtom is called when production bitExpressionAtom is exited.
func (s *BaseMariaDBParserListener) ExitBitExpressionAtom(ctx *BitExpressionAtomContext) {}

// EnterUnaryOperator is called when production unaryOperator is entered.
func (s *BaseMariaDBParserListener) EnterUnaryOperator(ctx *UnaryOperatorContext) {}

// ExitUnaryOperator is called when production unaryOperator is exited.
func (s *BaseMariaDBParserListener) ExitUnaryOperator(ctx *UnaryOperatorContext) {}

// EnterComparisonOperator is called when production comparisonOperator is entered.
func (s *BaseMariaDBParserListener) EnterComparisonOperator(ctx *ComparisonOperatorContext) {}

// ExitComparisonOperator is called when production comparisonOperator is exited.
func (s *BaseMariaDBParserListener) ExitComparisonOperator(ctx *ComparisonOperatorContext) {}

// EnterLogicalOperator is called when production logicalOperator is entered.
func (s *BaseMariaDBParserListener) EnterLogicalOperator(ctx *LogicalOperatorContext) {}

// ExitLogicalOperator is called when production logicalOperator is exited.
func (s *BaseMariaDBParserListener) ExitLogicalOperator(ctx *LogicalOperatorContext) {}

// EnterBitOperator is called when production bitOperator is entered.
func (s *BaseMariaDBParserListener) EnterBitOperator(ctx *BitOperatorContext) {}

// ExitBitOperator is called when production bitOperator is exited.
func (s *BaseMariaDBParserListener) ExitBitOperator(ctx *BitOperatorContext) {}

// EnterMathOperator is called when production mathOperator is entered.
func (s *BaseMariaDBParserListener) EnterMathOperator(ctx *MathOperatorContext) {}

// ExitMathOperator is called when production mathOperator is exited.
func (s *BaseMariaDBParserListener) ExitMathOperator(ctx *MathOperatorContext) {}

// EnterJsonOperator is called when production jsonOperator is entered.
func (s *BaseMariaDBParserListener) EnterJsonOperator(ctx *JsonOperatorContext) {}

// ExitJsonOperator is called when production jsonOperator is exited.
func (s *BaseMariaDBParserListener) ExitJsonOperator(ctx *JsonOperatorContext) {}

// EnterCharsetNameBase is called when production charsetNameBase is entered.
func (s *BaseMariaDBParserListener) EnterCharsetNameBase(ctx *CharsetNameBaseContext) {}

// ExitCharsetNameBase is called when production charsetNameBase is exited.
func (s *BaseMariaDBParserListener) ExitCharsetNameBase(ctx *CharsetNameBaseContext) {}

// EnterTransactionLevelBase is called when production transactionLevelBase is entered.
func (s *BaseMariaDBParserListener) EnterTransactionLevelBase(ctx *TransactionLevelBaseContext) {}

// ExitTransactionLevelBase is called when production transactionLevelBase is exited.
func (s *BaseMariaDBParserListener) ExitTransactionLevelBase(ctx *TransactionLevelBaseContext) {}

// EnterPrivilegesBase is called when production privilegesBase is entered.
func (s *BaseMariaDBParserListener) EnterPrivilegesBase(ctx *PrivilegesBaseContext) {}

// ExitPrivilegesBase is called when production privilegesBase is exited.
func (s *BaseMariaDBParserListener) ExitPrivilegesBase(ctx *PrivilegesBaseContext) {}

// EnterIntervalTypeBase is called when production intervalTypeBase is entered.
func (s *BaseMariaDBParserListener) EnterIntervalTypeBase(ctx *IntervalTypeBaseContext) {}

// ExitIntervalTypeBase is called when production intervalTypeBase is exited.
func (s *BaseMariaDBParserListener) ExitIntervalTypeBase(ctx *IntervalTypeBaseContext) {}

// EnterDataTypeBase is called when production dataTypeBase is entered.
func (s *BaseMariaDBParserListener) EnterDataTypeBase(ctx *DataTypeBaseContext) {}

// ExitDataTypeBase is called when production dataTypeBase is exited.
func (s *BaseMariaDBParserListener) ExitDataTypeBase(ctx *DataTypeBaseContext) {}

// EnterKeywordsCanBeId is called when production keywordsCanBeId is entered.
func (s *BaseMariaDBParserListener) EnterKeywordsCanBeId(ctx *KeywordsCanBeIdContext) {}

// ExitKeywordsCanBeId is called when production keywordsCanBeId is exited.
func (s *BaseMariaDBParserListener) ExitKeywordsCanBeId(ctx *KeywordsCanBeIdContext) {}

// EnterFunctionNameBase is called when production functionNameBase is entered.
func (s *BaseMariaDBParserListener) EnterFunctionNameBase(ctx *FunctionNameBaseContext) {}

// ExitFunctionNameBase is called when production functionNameBase is exited.
func (s *BaseMariaDBParserListener) ExitFunctionNameBase(ctx *FunctionNameBaseContext) {}
